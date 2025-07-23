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
from backend.services.llm.agents.chief_editor import ChiefEditorAgent
from backend.services.llm.agents.planner import PlannerAgent

# Agent团队配置 (不包含Director和Planner)
AGENT_TEAM_CONFIG = {
    'document_expert': DocumentExpertAgent,
    'case_expert': CaseExpertAgent,
    'writer_expert': WriterExpertAgent,
    'data_analyst': DataAnalystAgent,
    'chief_editor': ChiefEditorAgent,
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
            agent_dirs = ['document_expert', 'case_expert', 'writer_expert', 'data_analyst', 'chief_editor']
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
        处理用户消息，遵循 Director -> Planner -> Experts 的新流程
        """
        try:
            print(f"👤 收到用户消息 [{session_id}]: {user_message[:80]}...")
            
            if session_id not in self.sessions_context:
                await self.start_session(session_id)
            
            session_context = self.sessions_context[session_id]
            agents = session_context.get('agents', {})
            director = agents.get('director')
            planner = agents.get('planner')

            # 检查是否有待处理的计划
            pending_plan = session_context.get('current_plan')

            if pending_plan:
                # 场景2：用户对计划进行反馈
                return await self._handle_plan_feedback(session_id, user_message, pending_plan, websocket_manager)
            else:
                # 场景1：用户发起新请求
                return await self._handle_new_request(session_id, user_message, websocket_manager)

        except Exception as e:
            print(f"❌ 处理用户消息时发生严重错误: {e}")
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(session_id, "system", "系统错误", f"处理您的请求时发生错误: {e}", "error")
            return False
    
    async def _handle_new_request(self, session_id: str, user_message: str, websocket_manager=None) -> bool:
        """处理新的用户请求，生成待审核的计划"""
        session_context = self.sessions_context[session_id]
        director = session_context['agents']['director']

        if websocket_manager:
            await websocket_manager.broadcast_agent_message(session_id, "director", director.name, "正在理解您的需求，并为您草拟一份行动计划...", "working")
        
        # 步骤 1: Director接收用户需求，生成初步Plan
        plan = await director.process_request(user_message)
        
        # 步骤 2: 保存待审核的Plan
        session_context['current_plan'] = plan
        
        # 步骤 3: 将Plan格式化后发给用户征求意见
        plan_for_approval = self._format_plan_for_approval(plan)
        if websocket_manager:
            await websocket_manager.broadcast_agent_message(
                session_id=session_id,
                agent_type="director",
                agent_name=director.name,
                content=plan_for_approval,
                status="pending_approval" # 使用新状态
            )
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
            
            plan_for_approval = self._format_plan_for_approval(revised_plan)
            if websocket_manager:
                 await websocket_manager.broadcast_agent_message(
                    session_id=session_id,
                    agent_type="director",
                    agent_name=director.name,
                    content=plan_for_approval,
                    status="pending_approval"
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
            "chief_editor": "总编辑（钱敏）",
        }
        return name_map.get(agent_id, agent_id)

    async def _handle_director_response(self, session_id: str, response: Dict[str, Any], websocket_manager=None):
        """
        (已废弃) 处理增强版Director的响应
        """
        pass
    
    async def _execute_simple_task(self, session_id: str, director_response: Dict[str, Any], websocket_manager=None):
        """
        (已废弃) 执行简单任务
        """
        pass

    async def _execute_complex_workflow(self, session_id: str, director_response: Dict[str, Any], websocket_manager=None):
        """
        (已废弃) 执行复杂工作流
        """
        pass

    async def _handle_consultation_followup(self, session_id: str, director_response: Dict[str, Any], websocket_manager=None):
        """
        (已废弃) 处理咨询后续服务
        """
        pass
    
    async def _execute_agent_task(self, agent, agent_id: str) -> dict:
        """(已废弃) 执行Agent任务"""
        pass
    
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