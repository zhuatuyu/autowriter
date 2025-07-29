"""
核心管理器 - 增强版本
集成增强版Director，支持智能意图识别和动态任务分配
"""
import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# 调整导入路径以适应新的Agent结构
from backend.roles.director import DirectorAgent

from backend.roles.case_expert import CaseExpertAgent
from backend.roles.writer_expert import WriterExpertAgent
from backend.roles.data_analyst import DataAnalystAgent
from backend.services.websocket_manager import WebSocketManager
from backend.models.session import SessionState  # 引入会话状态枚举
from backend.models.plan import Plan, Task  # 引入Plan和Task模型
from metagpt.schema import Message  # 引入MetaGPT的Message类
from metagpt.logs import logger  # 引入MetaGPT的日志记录器
from backend.utils.project_repo import ProjectRepo # 引入项目仓库管理

# Agent团队配置 (不包含Director和Planner)
AGENT_TEAM_CONFIG = {
    
    'case_expert': CaseExpertAgent,
    'writer_expert': WriterExpertAgent,
    'data_analyst': DataAnalystAgent,
}

class Orchestrator:
    """核心协调器 (Orchestrator) - 基于状态机管理多智能体协作"""
    
    def __init__(self):
        self.sessions_context: Dict[str, Dict[str, Any]] = {}
        self.workspace_base = Path("workspaces")
        self.workspace_base.mkdir(exist_ok=True)
        self.session_states: Dict[str, SessionState] = {} # 新增：用于跟踪每个会话的状态

        print("✅ 增强版核心管理器(协调器模式)初始化完成")
    
    async def start_session(self, session_id: str, project_info: Dict = None) -> bool:
        """启动或获取现有工作会话"""
        try:
            if session_id in self.sessions_context:
                print(f"🔄 恢复现有会话: {session_id}")
                return True

            print(f"🚀 启动新的智能工作会话: {session_id}")
            
            # 创建会话工作空间和项目仓库
            session_workspace = self.workspace_base / session_id
            project_repo = ProjectRepo(session_id)


            # 初始化会话上下文
            self.sessions_context[session_id] = {
                'session_id': session_id,
                'project_info': project_info or {},
                'status': 'active', # 保留旧status，用于兼容
                'started_at': datetime.now().isoformat(),
                'workspace_path': str(session_workspace),
                'project_repo': project_repo, # 存储项目仓库实例
                'agents': {},
                'current_plan': None,
                'state': SessionState.IDLE  # 新增：初始化会话状态
            }
            self.session_states[session_id] = SessionState.IDLE # 同步到独立的状态跟踪器
            
            # 创建Agent团队
            await self._create_agent_team(session_id)
            
            print(f"✅ 会话 {session_id} 启动成功，当前状态: {self.session_states[session_id].value}")
            return True
            
        except Exception as e:
            print(f"❌ 启动会话失败: {e}")
            return False
    
    def _check_existing_project(self, workspace_path: Path) -> bool:
        """检查是否是现有项目"""
        try:
            # 检查是否有Agent工作区
            agent_dirs = ['document_expert', 'case_expert', 'writer_expert', 'data_analyst'] # 移除 chief_editor
            existing_agents = 0
            
            for agent_dir in agent_dirs:
                agent_path = workspace_path / agent_dir
                if agent_path.exists() and any(agent_path.iterdir()):
                    existing_agents += 1
            
            # 如果有2个或以上的Agent有工作记录，认为是现有项目
            return existing_agents >= 2
        except Exception as e:
            print(f"❌ 检查现有项目失败: {e}")
            return False
    
    async def _create_agent_team(self, session_id: str):
        """根据新架构创建完整的Agent团队"""
        try:
            session_context = self.sessions_context[session_id]
            workspace_path = session_context['workspace_path']
            project_repo = session_context['project_repo']
            
            agents = {}
            
            # 1. 创建总监 (Director)
            director = DirectorAgent()
            agents['director'] = director
            print(f"  ✅ 创建Agent: {director.profile} ({director.name})")

            # 2. 创建专业Agent团队，并注入ProjectRepo
            for agent_id, agent_class in AGENT_TEAM_CONFIG.items():
                # 创建context并注入ProjectRepo
                from metagpt.context import Context
                context = Context()
                context.kwargs.set('project_repo', project_repo)
                
                # 使用context创建agent
                agent = agent_class(context=context)
                agents[agent_id] = agent
                print(f"  ✅ 创建Agent: {agent.profile} ({agent.name}) - 已注入ProjectRepo")
            
            self.sessions_context[session_id]['agents'] = agents
            
        except Exception as e:
            print(f"❌ 创建Agent团队失败: {e}")
    
    async def handle_user_message(self, session_id: str, user_message: str, websocket_manager=None) -> bool:
        """
        处理用户消息 - 基于状态机的全新Orchestrator模式
        """
        try:
            print(f"👤 收到用户消息 [{session_id}]: {user_message[:80]}...")
            
            if session_id not in self.sessions_context:
                await self.start_session(session_id)
            
            current_state = self.get_session_state(session_id)
            print(f"🧠 当前会话状态: {current_state.value}，开始处理用户消息...")

            # 状态分发器
            state_handler_map = {
                SessionState.IDLE: self._state_idle_handler,
                SessionState.AWAITING_USER_APPROVAL: self._state_awaiting_approval_handler,
                SessionState.EXECUTING: self._state_executing_handler,
                SessionState.COMPLETED: self._state_completed_handler,
                SessionState.ERROR: self._state_error_handler,
            }

            handler = state_handler_map.get(current_state, self._state_default_handler)
            return await handler(session_id, user_message, websocket_manager)

        except Exception as e:
            print(f"❌ 处理用户消息时发生严重错误: {e}")
            self._set_session_state(session_id, SessionState.ERROR)
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(session_id, "system", "系统错误", f"处理您的请求时发生错误: {e}", "error")
            return False

    # =================================================================
    # == 状态处理方法 (State Handlers)
    # =================================================================

    async def _state_idle_handler(self, session_id: str, user_message: str, websocket_manager):
        """处理IDLE状态下的用户消息，通常意味着这是一个新请求"""
        # 对于IDLE状态，任何非平凡输入都应启动规划流程
        
        # 步骤 1: 智能分类用户意图 (可以简化，因为IDLE状态下几乎总是planning_request)
        session_context = self.sessions_context[session_id]
        intent = await self._classify_user_intent(session_context, user_message)

        if intent in ['trivial_chat', 'simple_qa']:
            return await self._handle_direct_answer(session_id, user_message, intent, websocket_manager)
        
        # 否则，视为新规划请求
        return await self._request_new_plan(session_id, user_message, websocket_manager)

    async def _state_awaiting_approval_handler(self, session_id: str, user_message: str, websocket_manager):
        """处理AWAITING_USER_APPROVAL状态下的用户消息，即处理用户对计划的反馈"""
        session_context = self.sessions_context[session_id]
        
        if "同意" in user_message or "可以" in user_message or "ok" in user_message.lower():
            plan_to_execute = session_context.get('current_plan')
            if not plan_to_execute:
                await websocket_manager.broadcast_agent_message(session_id, "system", "系统错误", "找不到待执行的计划，请重新发起请求。", "error")
                self._set_session_state(session_id, SessionState.IDLE)
                return False
            
            session_context['current_plan'] = None
            self._set_session_state(session_id, SessionState.EXECUTING)
            
            await websocket_manager.broadcast_agent_message(session_id, "system", "Orchestrator", f"收到您的确认！计划已启动，共 {len(plan_to_execute.tasks)} 个步骤，开始执行...", "working")
            
            # 调用新的执行逻辑
            execution_result = await self._execute_plan(session_id, plan_to_execute, websocket_manager)
            
            if execution_result.get("status") == "completed":
                self._set_session_state(session_id, SessionState.COMPLETED)
                await websocket_manager.broadcast_agent_message(session_id, "system", "Orchestrator", "所有任务已成功完成！", "completed")
            else:
                self._set_session_state(session_id, SessionState.ERROR)
                error_message = execution_result.get("error", "未知错误")
                await websocket_manager.broadcast_agent_message(session_id, "system", "Orchestrator", f"任务执行失败: {error_message}", "error")
            
            return True
        else:
            return await self._revise_plan(session_id, user_message, websocket_manager)

    async def _state_executing_handler(self, session_id: str, user_message: str, websocket_manager):
        """处理EXECUTING状态下的用户消息，通常是用户插话"""
        await websocket_manager.broadcast_agent_message(session_id, "system", "Orchestrator", "正在执行任务中，已收到您的消息。如需中止或修改任务，请明确指示。", "info")
        # 当前实现：仅记录用户消息，不打断执行流程
        print(f"💬 用户在执行期间插话: {user_message}")
        # 可以在这里实现更复杂的逻辑，如暂停、中止等
        return True

    async def _state_completed_handler(self, session_id: str, user_message: str, websocket_manager):
        """处理COMPLETED状态下的用户消息，通常是新一轮请求"""
        await websocket_manager.broadcast_agent_message(session_id, "system", "Orchestrator", "当前任务已完成。您的新消息将作为新一轮请求开始处理。", "info")
        self._set_session_state(session_id, SessionState.IDLE)
        return await self._state_idle_handler(session_id, user_message, websocket_manager)

    async def _state_error_handler(self, session_id: str, user_message: str, websocket_manager):
        """处理ERROR状态下的用户消息"""
        await websocket_manager.broadcast_agent_message(session_id, "system", "Orchestrator", "系统当前处于错误状态。您的新消息将作为新一轮请求开始处理。", "info")
        self._set_session_state(session_id, SessionState.IDLE)
        return await self._state_idle_handler(session_id, user_message, websocket_manager)

    async def _state_default_handler(self, session_id: str, user_message: str, websocket_manager):
        """默认处理器，用于处理未知状态"""
        await websocket_manager.broadcast_agent_message(session_id, "system", "Orchestrator", f"系统处于未知状态({self.get_session_state(session_id).value})，将重置为空闲状态。", "warning")
        self._set_session_state(session_id, SessionState.IDLE)
        return await self._state_idle_handler(session_id, user_message, websocket_manager)

    # =================================================================
    # == 原子操作方法 (Atomic Operations)
    # =================================================================

    async def _request_new_plan(self, session_id: str, user_message: str, websocket_manager=None) -> bool:
        """原子操作：请求新计划"""
        session_context = self.sessions_context[session_id]
        director = session_context['agents']['director']

        self._set_session_state(session_id, SessionState.PLANNING)
        if websocket_manager:
            await websocket_manager.broadcast_agent_message(session_id, "director", director.name, "正在理解您的需求，并为您草拟一份行动计划...", "working")
        
        plan = await director.process_request(user_message)
        
        if plan is None:
            self._set_session_state(session_id, SessionState.ERROR)
            await websocket_manager.broadcast_agent_message(session_id, "system", "系统错误", "Director未能生成计划，请检查日志。", "error")
            return False

        plan_display_text = director._format_plan_for_display(plan)
        
        await websocket_manager.broadcast_agent_message(session_id, "director", director.name, plan_display_text, "pending_review")
        
        session_context['current_plan'] = plan
        self._set_session_state(session_id, SessionState.AWAITING_USER_APPROVAL)
        return True

    async def _revise_plan(self, session_id: str, user_message: str, websocket_manager=None) -> bool:
        """原子操作：修订计划"""
        session_context = self.sessions_context[session_id]
        director = session_context['agents']['director']
        original_plan = session_context.get('current_plan')

        if not original_plan:
            await websocket_manager.broadcast_agent_message(session_id, "system", "系统错误", "找不到待修订的计划，请重新发起请求。", "error")
            self._set_session_state(session_id, SessionState.IDLE)
            return False
            
        self._set_session_state(session_id, SessionState.PLANNING)
        if websocket_manager:
            await websocket_manager.broadcast_agent_message(session_id, "director", director.name, f"收到您的反馈：'{user_message[:50]}...'。正在为您修订计划...", "working")
        
        revised_plan = await director.revise_plan(original_plan, user_message)
        
        if revised_plan is None:
            self._set_session_state(session_id, SessionState.ERROR)
            await websocket_manager.broadcast_agent_message(session_id, "system", "系统错误", "Director未能修订计划，请检查日志。", "error")
            # 保留原计划供用户再次尝试
            self._set_session_state(session_id, SessionState.AWAITING_USER_APPROVAL)
            return False

        plan_display_text = director._format_plan_for_display(revised_plan)
        
        await websocket_manager.broadcast_agent_message(session_id, "director", director.name, plan_display_text, "pending_review")
        
        session_context['current_plan'] = revised_plan
        self._set_session_state(session_id, SessionState.AWAITING_USER_APPROVAL)
        return True

    async def _handle_direct_answer(self, session_id: str, user_message: str, intent: str, websocket_manager=None) -> bool:
        """原子操作：处理直接问答类的请求"""
        session_context = self.sessions_context[session_id]
        director = session_context['agents']['director']

        if websocket_manager:
            await websocket_manager.broadcast_agent_message(session_id, "director", director.name, "正在思考您的问题...", "working")
        
        answer = await director.direct_answer(user_message, intent)
        
        if websocket_manager:
            await websocket_manager.broadcast_agent_message(
                session_id=session_id,
                agent_type="director",
                agent_name=director.name,
                content=answer,
                status="completed"
            )
        # 直接问答不改变会话状态，保持IDLE
        return True

    async def _classify_user_intent(self, session_context: Dict[str, Any], user_message: str) -> str:
        """使用LLM对用户意图进行分类"""
        director = session_context['agents']['director']
        
        # 在新模式下，我们只关心是否是闲聊
        # 如果不是，都将启动规划流程
        
        # 简化版意图分类
        prompt = f"""
        判断以下用户输入是否属于闲聊或简单问候。只需回答 "trivial_chat" 或 "planning_request"。

        用户输入: "{user_message}"
        """
        
        raw_intent = await director.llm.aask(prompt)
        intent = raw_intent.strip().replace("`", "").replace("'", "").replace('"', '')
        
        if intent not in ['trivial_chat', 'planning_request']:
            print(f"LLM返回了无效的意图分类: '{intent}'，将默认作为新请求。")
            return 'planning_request'
            
        print(f"🧠 用户意图被分类为: {intent}")
        return intent

    # _handle_direct_answer, _handle_new_request, _handle_plan_feedback 这些旧方法将被删除

    async def _execute_plan(self, session_id: str, plan: Plan, websocket_manager) -> Dict[str, Any]:
        """
        Orchestrator的核心执行逻辑：按顺序执行计划中的每个任务
        """
        print(f"🚀 {session_id} Orchestrator 开始执行计划: {plan.goal}")
        session_context = self.sessions_context[session_id]
        project_repo = session_context.get('project_repo') # 获取 project_repo
        
        # 初始上下文是用户最开始的请求
        # 使用MetaGPT标准的UserRequirement作为cause_by
        from metagpt.actions.add_requirement import UserRequirement
        last_message = Message(content=plan.goal, role="user", cause_by=UserRequirement)

        for i, task in enumerate(plan.tasks, 1):
            target_agent_id = task.agent
            agent = session_context['agents'].get(target_agent_id)

            if not agent:
                error_msg = f"任务 {i} '{task.description}' 的执行者 '{target_agent_id}' 不存在。"
                print(f"❌ {error_msg}")
                return {"status": "error", "error": error_msg}

            # ProjectRepo 已在agent创建时注入，无需重复注入
            print(f"🔧 Agent {agent.profile} 已具备 ProjectRepo 上下文。")
            
            await websocket_manager.broadcast_agent_message(session_id, agent.profile, agent.name, f"正在执行任务: {task.description}", "working")
            
            try:
                # 按照MetaGPT标准做法：直接调用 agent.run(message)
                # 让 Role 自己管理内存和 Action 流程
                print(f"🔍 调试: 准备调用 {agent.profile}.run() 方法")
                print(f"🔍 调试: 传入消息类型: {type(last_message)}, 内容: {last_message.content[:100]}...")
                print(f"🔍 调试: Agent当前内存消息数: {len(agent.rc.memory.storage) if hasattr(agent, 'rc') and hasattr(agent.rc, 'memory') else 'N/A'}")
                
                result_message = await agent.run(last_message)
                
                print(f"🔍 调试: agent.run() 返回值类型: {type(result_message)}")
                print(f"🔍 调试: agent.run() 返回值: {result_message}")
                print(f"🔍 调试: Agent执行后内存消息数: {len(agent.rc.memory.storage) if hasattr(agent, 'rc') and hasattr(agent.rc, 'memory') else 'N/A'}")

                # MetaGPT的Role.run()可能返回None（当没有新消息需要处理时）
                # 这是正常行为，我们需要从agent的内存中获取最新的消息
                if not result_message:
                    print(f"🔍 调试: agent.run() 返回None，尝试从内存获取最新消息")
                    # 从agent的内存中获取最新的消息作为结果
                    try:
                        memories = agent.rc.memory.get(k=1)
                        print(f"🔍 调试: 从内存获取到 {len(memories) if memories else 0} 条消息")
                        if memories:
                            result_message = memories[0]
                            print(f"🔍 调试: 使用内存中的消息作为结果: {type(result_message)}")
                        else:
                            logger.error(f"任务 {task.id} '{task.description}' 执行后没有返回结果消息，且内存中也没有消息。")
                            error_message = f"任务 {task.id} 执行异常，智能体未返回结果。"
                            return {"status": "error", "error": error_message}
                    except Exception as memory_error:
                        print(f"🔍 调试: 访问agent内存失败: {memory_error}")
                        logger.error(f"访问agent内存失败: {memory_error}")
                        error_message = f"任务 {task.id} 执行异常，无法访问智能体内存。"
                        return {"status": "error", "error": error_message}
                
                # 更新上下文，用于下一个任务
                last_message = result_message
                print(f"🔍 调试: 最终结果消息类型: {type(last_message)}, 内容: {last_message.content[:100] if hasattr(last_message, 'content') else 'N/A'}...")
                
                await websocket_manager.broadcast_agent_message(session_id, agent.profile, agent.name, f"任务完成: {task.description}", "completed")

            except Exception as e:
                error_msg = f"任务 {i} '{task.description}' 执行失败: {e}"
                print(f"❌ {error_msg}")
                import traceback
                traceback.print_exc()
                return {"status": "error", "error": error_msg}

        print(f"✅ {session_id} 计划执行完成")
        return {"status": "completed", "final_result": last_message.content}

    def _format_plan_for_approval(self, plan: Any) -> str:
        """将Plan对象格式化为易于用户理解的字符串"""
        response = f"**我已经为您制定了如下行动计划，请您审阅：**\n\n"
        response += f"**🎯 最终目标:** {plan.goal}\n\n"
        response += "**📝 步骤如下:**\n"
        for i, task in enumerate(plan.tasks, 1):
            response += f"{i}. {task.description}\n"
        
        response += "\n---\n"
        response += "**请问您是否同意此计划？** 您可以直接回复“同意”开始执行，或者提出您的修改意见，例如：“补充一下，第2步应该先搜索政府网站的公开数据”。"
        return response

    def _format_final_response(self, final_result: Dict[str, Any]) -> str:
        """
        格式化最终结果以便展示，现在只进行状态汇报
        """
        goal = final_result.get("goal")
        status = final_result.get("status")
        tasks = final_result.get("tasks", [])
        
        if status == "completed":
            response = f"**项目目标 “{goal}” 已成功完成！**\n\n"
            response += "所有任务均已执行完毕。您可以随时查阅各个专家的工作区以获取详细的成果文件。"
            
            # (可选) 提供一个最终产出任务的提示
            if tasks:
                final_task = tasks[-1]
                owner_agent_name = self._get_agent_name_by_id(final_task.get("owner"))
                if owner_agent_name:
                    response += f"\n\n*主要成果（例如报告初稿）通常由 **{owner_agent_name}** 完成，请重点关注其工作区。*"

        else:
            response = f"**很抱歉，项目目标 “{goal}” 未能成功完成。**\n\n"
            # 找到出错的任务
            failed_task_info = ""
            for task in tasks:
                if task.get('status') == 'error':
                    owner_agent_name = self._get_agent_name_by_id(task.get("owner"))
                    failed_task_info = f"在 **{owner_agent_name}** 执行任务 **“{task.get('description')}”** 时遇到问题。\n\n**错误详情:**\n{task.get('result')}"
                    break
            response += failed_task_info if failed_task_info else "执行过程中发生未知错误，请检查后台日志获取更多信息。"

        return response
    
    def _get_agent_name_by_id(self, agent_id: str) -> str:
        """根据agent_id获取在AGENT_TEAM_CONFIG中定义的名字"""
        # 这是一个简化的辅助函数，需要CoreManager能够访问到Agent的实例或配置
        # 暂时硬编码名字
        name_map = {
            "director": "智能项目总监",
            "planner": "规划执行者",
            "document_expert": "文档专家（李心悦）",
            "case_expert": "案例专家（王磊）",
            "writer_expert": "写作专家（张翰）",
            "data_analyst": "数据分析师（赵丽娅）",
        }
        return name_map.get(agent_id, agent_id)

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """获取会话状态"""
        try:
            if session_id not in self.sessions_context:
                return {'error': f'会话 {session_id} 不存在'}
            
            session_context = self.sessions_context[session_id]
            session_info = {k: v for k, v in session_context.items() if k not in ['agents', 'memory_manager']}
            
            # 获取所有Agent状态
            agents_status = []
            if 'agents' in session_context:
                for agent_id, agent in session_context['agents'].items():
                    if agent_id in ['director', 'planner']:
                        continue  # 跳过核心Agent，只显示专业Agent
                    
                    if hasattr(agent, 'get_status'):
                        agent_status = await agent.get_status()
                    else:
                        agent_status = {
                            'agent_id': agent_id,
                            'name': getattr(agent, 'name', agent_id),
                            'status': 'active'
                        }
                    agents_status.append(agent_status)
            
            session_info['agents'] = agents_status
            return session_info
            
        except Exception as e:
            print(f"❌ 获取会话状态失败: {e}")
            return {'error': str(e)}
    
    async def get_agent_status(self, session_id: str, agent_id: str) -> Dict[str, Any]:
        """获取指定Agent状态"""
        try:
            if session_id not in self.sessions_context:
                return {'error': f'会话 {session_id} 不存在'}

            agents = self.sessions_context[session_id].get('agents', {})
            
            if agent_id not in agents:
                return {'error': f'Agent {agent_id} 不存在'}
            
            agent = agents[agent_id]
            
            if hasattr(agent, 'get_status'):
                return await agent.get_status()
            else:
                return {
                    'agent_id': agent_id,
                    'name': getattr(agent, 'name', agent_id),
                    'status': 'active'
                }
            
        except Exception as e:
            print(f"❌ 获取Agent状态失败: {e}")
            return {'error': str(e)}
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """获取所有会话列表"""
        return [{k: v for k, v in session.items() if k not in ['agents', 'memory_manager']} for session in self.sessions_context.values()]
    
    async def handle_user_intervention(self, session_id: str, user_message: str, websocket_manager=None):
        """处理用户插话 - 现在也通过主状态机处理"""
        try:
            print(f"👤 用户插话 [{session_id}]: {user_message}")
            await self.handle_user_message(session_id, user_message, websocket_manager)
        except Exception as e:
            print(f"❌ 处理用户插话失败: {e}")

    def _set_session_state(self, session_id: str, new_state: SessionState):
        """安全地更新会话状态并记录日志"""
        if session_id not in self.session_states:
            print(f"⚠️ 尝试为不存在的会话 {session_id} 设置状态")
            return
        
        old_state = self.session_states.get(session_id, SessionState.IDLE)
        if old_state != new_state:
            self.session_states[session_id] = new_state
            # 同时更新sessions_context中的状态，以实现数据同步
            if session_id in self.sessions_context:
                self.sessions_context[session_id]['state'] = new_state
            print(f"🔄 会话 {session_id} 状态变更: {old_state.value} -> {new_state.value}")
        
    def get_session_state(self, session_id: str) -> SessionState:
        """获取当前会话状态"""
        return self.session_states.get(session_id, SessionState.IDLE)




# 全局协调器实例
orchestrator = Orchestrator()