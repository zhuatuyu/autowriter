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
from backend.services.environment import Environment
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
        self.session_states: Dict[str, SessionState] = {}
        self.environments: Dict[str, Environment] = {}

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
            
            # 创建 Environment 和 Agent 团队
            await self._create_environment_and_agents(session_id)
            
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
    
    async def _create_environment_and_agents(self, session_id: str):
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
                # 直接创建agent
                agent = agent_class()
                # 直接设置project_repo属性（与测试中一致）
                agent.project_repo = project_repo
                agents[agent_id] = agent
                print(f"  ✅ 创建Agent: {agent.profile} ({agent.name}) - 已注入ProjectRepo")
            
            self.sessions_context[session_id]['agents'] = agents
            # 创建并存储 Environment
            environment = Environment()
            environment.add_roles(list(agents.values()))
            self.environments[session_id] = environment
            
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
            
            # 执行计划中的任务
            try:
                execution_result = await self._execute_plan_tasks(session_id, plan_to_execute, websocket_manager)
            except Exception as e:
                print(f"❌ 任务执行过程中发生错误: {e}")
                execution_result = {"status": "error", "error": str(e)}
            
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

    async def _execute_plan_tasks(self, session_id: str, plan, websocket_manager) -> Dict[str, Any]:
        """使用MetaGPT Environment执行计划任务，包含手动触发逻辑"""
        session_context = self.sessions_context[session_id]
        
        print(f"🚀 开始执行计划，共 {len(plan.tasks)} 个任务")
        
        try:
            # 获取已创建的Environment
            environment = self.environments.get(session_id)
            if not environment:
                print("❌ 找不到Environment，重新创建")
                await self._create_environment_and_agents(session_id)
                environment = self.environments.get(session_id)
            
            # 将用户需求作为初始消息发布到环境
            from metagpt.schema import Message
            from metagpt.actions.add_requirement import UserRequirement
            
            # 构建包含完整计划的用户需求
            plan_content = plan.model_dump_json()
            
            initial_message = Message(
                content=plan_content,
                role="Director", 
                cause_by=DirectorAgent
            )
            
            # 将消息发布到环境中
            environment.publish_message(initial_message)
            print("📨 计划已发送给Director")
            
            # 获取所有智能体
            agents = session_context['agents']
            agent_roles = [agents.get('case_expert'), agents.get('data_analyst'), agents.get('writer_expert')]
            agent_roles = [role for role in agent_roles if role is not None]
            
            # 添加调试信息：检查智能体是否接收到消息
            print("\n🔍 检查智能体消息接收状态:")
            for role in agent_roles:
                print(f"  {role.profile}: 消息数={len(role.rc.memory.storage)}, 新消息数={len(role.rc.news)}")
                if role.rc.news:
                    print(f"    最新消息来源: {role.rc.news[0].cause_by}")
                    print(f"    消息内容长度: {len(role.rc.news[0].content)}")
            
            # 手动触发智能体的_think和_act方法
            for role in agent_roles:
                if role.rc.news:
                    print(f"\n🤖 手动触发 {role.profile} 的思考和行动...")
                    try:
                        # 调用_think方法
                        should_act = await role._think()
                        print(f"  {role.profile}._think() 返回: {should_act}")
                        
                        if should_act and role.rc.todo:
                            # 调用_act方法
                            print(f"  {role.profile} 开始执行 {role.rc.todo}")
                            result = await role._act()
                            print(f"  {role.profile}._act() 完成，结果: {type(result)}")
                            
                            # 检查是否需要继续执行下一个action
                            if hasattr(role, 'actions') and len(role.actions) > 1:
                                current_action_index = role.actions.index(role.rc.todo) if role.rc.todo in role.actions else 0
                                if current_action_index < len(role.actions) - 1:
                                    # 设置下一个action
                                    role.rc.todo = role.actions[current_action_index + 1]
                                    print(f"  {role.profile}: 设置下一个action为 {role.rc.todo}")
                                    
                                    # 继续执行下一个action
                                    act_result2 = await role._act()
                                    print(f"  {role.profile}._act() 第二次完成，结果: {type(act_result2)}")
                                    
                                    # 如果还有第三个action
                                    if current_action_index + 1 < len(role.actions) - 1:
                                        role.rc.todo = role.actions[current_action_index + 2]
                                        print(f"  {role.profile}: 设置第三个action为 {role.rc.todo}")
                                        act_result3 = await role._act()
                                        print(f"  {role.profile}._act() 第三次完成，结果: {type(act_result3)}")
                        else:
                            print(f"  {role.profile} 没有需要执行的任务")
                    except Exception as e:
                        print(f"  {role.profile} 执行出错: {e}")
                        import traceback
                        traceback.print_exc()
            
            # 运行Environment直到所有智能体完成工作
            max_rounds = 20  # 防止无限循环
            completed_rounds = 0
            
            for round_num in range(max_rounds):
                print(f"\n--- 执行轮次 {round_num + 1} ---")
                
                # 检查所有角色状态
                all_idle = True
                for agent_id, agent in agents.items():
                    msg_count = len(agent.rc.memory.get())
                    is_idle = agent.is_idle if hasattr(agent, 'is_idle') else True
                    print(f"  {agent_id}: 消息数={msg_count}, 空闲={is_idle}")
                    if not is_idle:
                        all_idle = False
                
                # 运行一轮
                await environment.run(k=1)
                completed_rounds += 1
                
                # 广播进度
                await websocket_manager.broadcast_agent_message(
                    session_id, "system", "Environment", 
                    f"执行轮次 {round_num + 1} 完成", "working"
                )
                
                # 如果所有角色都空闲，停止执行
                if all_idle and round_num > 0:  # 至少运行一轮
                    print("  所有角色都已空闲，执行完成")
                    break
            
            # 检查输出文件
            project_repo = session_context.get('project_repo')
            output_files = []
            
            if project_repo:
                # 检查reports目录
                reports_dir = project_repo.get_path("reports")
                if reports_dir.exists():
                    report_files = list(reports_dir.glob("*.md"))
                    output_files.extend([f.name for f in report_files])
                
                # 检查其他可能的输出目录
                for subdir in ["analysis", "research", "drafts", "outputs", "design", "cases"]:
                    subdir_path = project_repo.get_path(subdir)
                    if subdir_path.exists():
                        files = list(subdir_path.glob("*.*"))
                        output_files.extend([f"{subdir}/{f.name}" for f in files])
            
            print(f"✅ Environment执行完成，运行了 {completed_rounds} 轮")
            if output_files:
                print(f"📄 生成的文件: {output_files}")
            
            return {
                "status": "completed",
                "completed_rounds": completed_rounds,
                "total_rounds": max_rounds,
                "output_files": output_files,
                "environment_status": "success"
            }
            
        except Exception as e:
            print(f"❌ Environment执行过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "status": "error",
                "error": str(e),
                "environment_status": "failed"
            }
    
    # 移除不再需要的任务排序和单任务执行方法
    # 现在使用MetaGPT Environment的标准执行流程



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