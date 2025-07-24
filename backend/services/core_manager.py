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
from backend.services.llm.agents.director import DirectorAgent
from backend.services.llm.agents.document_expert import DocumentExpertAgent
from backend.services.llm.agents.case_expert import CaseExpertAgent
from backend.services.llm.agents.writer_expert import WriterExpertAgent
from backend.services.llm.agents.data_analyst import DataAnalystAgent
from backend.services.llm.agents.planner import PlannerAgent
from backend.services.websocket_manager import WebSocketManager

# 导入新的Prompt模块
from backend.services.llm.prompts import core_manager_prompts

# Agent团队配置 (不包含Director和Planner)
AGENT_TEAM_CONFIG = {
    'document_expert': DocumentExpertAgent,
    'case_expert': CaseExpertAgent,
    'writer_expert': WriterExpertAgent,
    'data_analyst': DataAnalystAgent,
}

class CoreManager:
    """核心管理器 - 集成增强版Director的多Agent协作管理"""
    
    def __init__(self):
        self.sessions_context: Dict[str, Dict[str, Any]] = {}
        self.workspace_base = Path("workspaces")
        self.workspace_base.mkdir(exist_ok=True)
        
        print("✅ 增强版核心管理器初始化完成")
    
    async def start_session(self, session_id: str, project_info: Dict = None) -> bool:
        """启动或获取现有工作会话"""
        try:
            if session_id in self.sessions_context:
                print(f"🔄 恢复现有会话: {session_id}")
                return True

            print(f"🚀 启动新的智能工作会话: {session_id}")
            
            # 创建会话工作空间
            session_workspace = self.workspace_base / session_id
            session_workspace.mkdir(exist_ok=True)

            # 为新会话创建唯一的记忆管理器
            from backend.services.llm.unified_memory_adapter import UnifiedMemoryManager
            memory_manager = UnifiedMemoryManager(str(session_workspace))
            
            # 初始化会话上下文
            self.sessions_context[session_id] = {
                'session_id': session_id,
                'project_info': project_info or {},
                'status': 'active',
                'started_at': datetime.now().isoformat(),
                'workspace_path': str(session_workspace),
                'agents': {},
                'memory_manager': memory_manager,
                'current_plan': None # 新增：用于存放待用户确认的计划
            }
            
            # 创建Agent团队
            await self._create_agent_team(session_id)
            
            print(f"✅ 会话 {session_id} 启动成功")
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
            memory_manager = session_context['memory_manager']
            
            agents = {}
            
            # 1. 创建总监 (Director)
            director_workspace = Path(workspace_path) / "director"
            director = DirectorAgent(
                session_id=session_id,
                workspace_path=str(director_workspace),
                memory_manager=memory_manager
            )
            agents[director.agent_id] = director
            print(f"  ✅ 创建Agent: {director.name} ({director.role})")

            # 2. 创建规划执行者 (Planner)
            planner_workspace = Path(workspace_path) / "planner"
            planner = PlannerAgent(
                session_id=session_id,
                workspace_path=str(planner_workspace),
                memory_manager=memory_manager
            )
            agents[planner.agent_id] = planner
            print(f"  ✅ 创建Agent: {planner.name} ({planner.role})")
            
            # 3. 创建专业Agent团队
            for agent_id, agent_class in AGENT_TEAM_CONFIG.items():
                agent_workspace = Path(workspace_path) / agent_id
                agent = agent_class(
                    agent_id=agent_id, 
                    session_id=session_id, 
                    workspace_path=str(agent_workspace),
                    memory_manager=memory_manager
                )
                agents[agent_id] = agent
                print(f"  ✅ 创建Agent: {agent.name} ({getattr(agent, 'profile', agent_id)})")
            
            self.sessions_context[session_id]['agents'] = agents
            
        except Exception as e:
            print(f"❌ 创建Agent团队失败: {e}")
    
    async def handle_user_message(self, session_id: str, user_message: str, websocket_manager=None) -> bool:
        """
        处理用户消息 - 智能调度版本
        """
        try:
            print(f"👤 收到用户消息 [{session_id}]: {user_message[:80]}...")
            
            if session_id not in self.sessions_context:
                await self.start_session(session_id)
            
            session_context = self.sessions_context[session_id]
            director = session_context['agents'].get('director')

            if not director:
                 print(f"❌ 核心Agent（Director）在会话 {session_id} 中不存在。")
                 return False

            # 步骤 1: 智能分类用户意图
            intent = await self._classify_user_intent(session_context, user_message)

            # 步骤 2: 根据意图进行调度
            if intent == 'plan_feedback':
                pending_plan = session_context.get('current_plan')
                if pending_plan:
                    return await self._handle_plan_feedback(session_id, user_message, pending_plan, websocket_manager)
                else:
                    # 如果没有待审批计划，却被识别为反馈，当作新请求处理
                    return await self._handle_new_request(session_id, user_message, websocket_manager)
            
            elif intent in ['trivial_chat', 'simple_qa', 'contextual_follow_up', 'status_inquiry']:
                return await self._handle_direct_answer(session_id, user_message, intent, websocket_manager)

            elif intent == 'planning_request':
                return await self._handle_new_request(session_id, user_message, websocket_manager)
                
            else: # 默认作为新请求处理
                return await self._handle_new_request(session_id, user_message, websocket_manager)

        except Exception as e:
            print(f"❌ 处理用户消息时发生严重错误: {e}")
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(session_id, "system", "系统错误", f"处理您的请求时发生错误: {e}", "error")
            return False
    
    async def _classify_user_intent(self, session_context: Dict[str, Any], user_message: str) -> str:
        """使用LLM对用户意图进行分类"""
        director = session_context['agents']['director']
        pending_plan = session_context.get('current_plan')
        
        # 准备上下文
        history = director._memory_adapter.get_conversation_history(limit=5)
        formatted_history = "\n".join([f"{msg.get('role')}: {msg.get('content')}" for msg in history])

        # 构建分类Prompt - 使用新的Prompt模块
        pending_plan_str = None
        if pending_plan:
            pending_plan_str = self._format_plan_for_approval(pending_plan)

        prompt = core_manager_prompts.get_intent_classification_prompt(
            formatted_history=formatted_history,
            user_message=user_message,
            pending_plan_str=pending_plan_str
        )
        
        # 使用Director的LLM进行分类
        # 注意：实际项目中可以考虑使用更小、更快的模型进行分类
        raw_intent = await director.llm.aask(prompt)
        
        # 增加健壮性：清理LLM可能返回的多余字符
        intent = raw_intent.strip().replace("`", "").replace("'", "").replace('"', '')
        
        # 清理并验证返回结果
        valid_intents = ['trivial_chat', 'simple_qa', 'contextual_follow_up', 'status_inquiry', 'planning_request', 'plan_feedback']
        
        if intent not in valid_intents:
            # 如果LLM返回无效内容，根据有无待审批计划做一个基本判断
            print(f"LLM返回了无效的意图分类: '{intent}'，将使用回退逻辑。")
            return 'plan_feedback' if pending_plan else 'planning_request'
            
        print(f"🧠 用户意图被分类为: {intent}")
        return intent

    async def _handle_direct_answer(self, session_id: str, user_message: str, intent: str, websocket_manager=None) -> bool:
        """处理直接问答类的请求"""
        session_context = self.sessions_context[session_id]
        director = session_context['agents']['director']

        if websocket_manager:
            await websocket_manager.broadcast_agent_message(session_id, "director", director.name, "正在思考您的问题...", "working")
        
        # 让Director直接回答
        answer = await director.direct_answer(user_message, intent)
        
        if websocket_manager:
            await websocket_manager.broadcast_agent_message(
                session_id=session_id,
                agent_type="director",
                agent_name=director.name,
                content=answer,
                status="completed"
            )
        return True

    async def _handle_new_request(self, session_id: str, user_message: str, websocket_manager=None) -> bool:
        """处理新的用户请求，生成待审核的计划"""
        session_context = self.sessions_context[session_id]
        director = session_context['agents']['director']

        if websocket_manager:
            await websocket_manager.broadcast_agent_message(session_id, "director", director.name, "正在理解您的需求，并为您草拟一份行动计划...", "working")
        
        # Director生成计划
        plan = await director.process_request(user_message)
        
        # 获取Director格式化好的、包含@姓名的计划文本
        plan_display_text = director._format_plan_for_display(plan)

        # 直接使用Director生成好的文本进行广播
        await websocket_manager.broadcast_agent_message(
            session_id, 
            "director", 
            director.name, 
            plan_display_text, 
            "pending_review" # 状态：等待用户审核
        )
        
        # 更新项目状态
        self.sessions_context[session_id]['current_plan'] = plan
        return True

    async def _handle_plan_feedback(self, session_id: str, user_message: str, plan: Any, websocket_manager=None) -> bool:
        """处理用户对计划的反馈"""
        session_context = self.sessions_context[session_id]
        director = session_context['agents']['director']
        planner = session_context['agents']['planner']

        # 简单判断用户是否同意
        if "同意" in user_message or "可以" in user_message or "ok" in user_message.lower():
            # 用户同意，开始执行计划
            session_context['current_plan'] = None # 清空待审计划
            
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(session_id, "planner", planner.name, f"收到您的确认！计划已启动，共 {len(plan.tasks)} 个步骤，开始执行...", "working")
            
            final_result = await planner.execute_plan(plan, session_context['agents'])
            final_response = self._format_final_response(final_result)
            
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(session_id, "director", director.name, final_response, "completed")
        else:
            # 用户有补充意见，让Director修订计划
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(session_id, "director", director.name, f"收到您的反馈：'{user_message[:50]}...'。正在为您修订计划...", "working")
            
            # 将用户的补充意见和原计划一起发给Director进行修订
            # (这是一个简化的实现，实际可能需要更复杂的prompt)
            revised_plan = await director.revise_plan(plan, user_message)
            session_context['current_plan'] = revised_plan # 保存修订后的计划
            
            revised_plan_display_text = director._format_plan_for_display(revised_plan)
            await websocket_manager.broadcast_agent_message(
                session_id=session_id,
                agent_type="director",
                agent_name=director.name,
                content=revised_plan_display_text,
                status="pending_review"
            )
        return True

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
        """处理用户插话"""
        try:
            print(f"👤 用户插话 [{session_id}]: {user_message}")
            
            # 直接使用handle_user_message处理插话
            await self.handle_user_message(session_id, user_message, websocket_manager)
            
        except Exception as e:
            print(f"❌ 处理用户插话失败: {e}")


# 全局核心管理器实例
core_manager = CoreManager()