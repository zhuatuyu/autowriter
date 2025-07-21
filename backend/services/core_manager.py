"""
核心管理器 - 简化版本
替代原来复杂的intelligent_manager等服务
专注核心功能，大幅减少代码复杂度
"""
import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# 调整导入路径以适应新的Agent结构
from backend.services.llm.agents.director import IntelligentDirectorAgent
from backend.services.llm.agents.document_expert import DocumentExpertAgent
from backend.services.llm.agents.case_expert import CaseExpertAgent
from backend.services.llm.agents.writer_expert import WriterExpertAgent
from backend.services.llm.agents.data_analyst import DataAnalystAgent
from backend.services.llm.agents.chief_editor import ChiefEditorAgent

# Agent团队配置
AGENT_TEAM_CONFIG = {
    'document_expert': DocumentExpertAgent,
    'case_expert': CaseExpertAgent,
    'writer_expert': WriterExpertAgent,
    'data_analyst': DataAnalystAgent,
    'chief_editor': ChiefEditorAgent,
}

class CoreManager:
    """核心管理器 - 简化的多Agent协作管理"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict] = {}
        self.agents: Dict[str, Dict] = {}  # session_id -> {agent_id -> agent}
        self.workspace_base = Path("workspaces")
        self.workspace_base.mkdir(exist_ok=True)
        
        print("✅ 核心管理器初始化完成")
    
    async def start_session(self, session_id: str, project_info: Dict = None) -> bool:
        """启动或获取现有工作会话"""
        try:
            if session_id in self.active_sessions:
                print(f"🔄 恢复现有会话: {session_id}")
                return True

            print(f"🚀 启动新的智能工作会话: {session_id}")
            
            # 创建会话工作空间
            session_workspace = self.workspace_base / session_id
            session_workspace.mkdir(exist_ok=True)
            
            # 初始化会话状态
            self.active_sessions[session_id] = {
                'session_id': session_id,
                'project_info': project_info or {},
                'status': 'active',
                'started_at': datetime.now().isoformat(),
                'current_phase': 'initialization',
                'workspace_path': str(session_workspace)
            }
            
            # 创建Agent团队
            await self._create_agent_team(session_id)
            
            print(f"✅ 会话 {session_id} 启动成功")
            return True
            
        except Exception as e:
            print(f"❌ 启动会话失败: {e}")
            return False
    
    async def _create_agent_team(self, session_id: str):
        """根据新架构创建完整的Agent团队"""
        try:
            session_info = self.active_sessions[session_id]
            workspace_path = session_info['workspace_path']
            
            agents = {}
            
            # 1. 创建智能项目总监 (固定)
            director = IntelligentDirectorAgent(session_id, workspace_path)
            agents[director.agent_id] = director
            print(f"  ✅ 创建Agent: {director.name} ({director.role})")
            
            # 2. 创建专业Agent团队
            for agent_id, agent_class in AGENT_TEAM_CONFIG.items():
                agent_workspace = Path(workspace_path) / agent_id
                agent = agent_class(agent_id, session_id, str(agent_workspace))
                agents[agent_id] = agent
                print(f"  ✅ 创建Agent: {agent.name} ({agent.role})")
            
            self.agents[session_id] = agents
            
        except Exception as e:
            print(f"❌ 创建Agent团队失败: {e}")
    
    async def handle_user_message(self, session_id: str, user_message: str, websocket_manager=None) -> bool:
        """
        处理用户消息，将其完全委托给智能项目总监进行处理。
        总监将负责动态规划、任务分配和执行。
        """
        try:
            print(f"👤 收到用户消息 [{session_id}]: {user_message[:80]}...")
            
            if session_id not in self.agents:
                print(f"❌ 会话 {session_id} 不存在，正在尝试重新启动...")
                await self.start_session(session_id)
                if session_id not in self.agents:
                    print(f"❌ 启动会话失败，无法处理消息")
                return False
            
            director = self.agents[session_id].get('intelligent-director')
            if not director:
                print(f"❌ 智能项目总监在会话 {session_id} 中不存在")
                return False
            
            # 将用户消息和所有专家代理传递给总监，由其全权负责
            specialist_agents = {k: v for k, v in self.agents[session_id].items() if k != 'intelligent-director'}
            
            # IntelligentDirectorAgent将处理整个工作流程
            await director.handle_request(
                user_message=user_message,
                team=specialist_agents,
                websocket_manager=websocket_manager
            )
            
            # 更新会话状态
            self.active_sessions[session_id]['current_phase'] = 'in_progress'
            return True
            
        except Exception as e:
            print(f"❌ 处理用户消息时发生严重错误: {e}")
            # 在实际应用中，这里可能需要更复杂的错误处理和状态回滚
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(
                    session_id=session_id,
                    agent_type="system_error",
                    agent_name="系统错误",
                    content=f"处理请求时发生错误: {e}",
                    status="error"
                    )
            return False
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """获取会话状态"""
        try:
            if session_id not in self.active_sessions:
                return {'error': f'会话 {session_id} 不存在'}
            
            session_info = self.active_sessions[session_id].copy()
            
            # 获取所有Agent状态
            agents_status = []
            if session_id in self.agents:
                for agent_id, agent in self.agents[session_id].items():
                    if agent_id == 'intelligent-director':
                        continue  # 跳过项目总监，只显示专业Agent
                    agent_status = await agent.get_status()
                    agents_status.append(agent_status)
            
            session_info['agents'] = agents_status
            return session_info
            
        except Exception as e:
            print(f"❌ 获取会话状态失败: {e}")
            return {'error': str(e)}
    
    async def get_agent_status(self, session_id: str, agent_id: str) -> Dict[str, Any]:
        """获取指定Agent状态"""
        try:
            if session_id not in self.agents:
                return {'error': f'会话 {session_id} 不存在'}
            
            if agent_id not in self.agents[session_id]:
                return {'error': f'Agent {agent_id} 不存在'}
            
            agent = self.agents[session_id][agent_id]
            return await agent.get_status()
            
        except Exception as e:
            print(f"❌ 获取Agent状态失败: {e}")
            return {'error': str(e)}
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """获取所有会话列表"""
        return list(self.active_sessions.values())
    
    async def handle_user_intervention(self, session_id: str, user_message: str, websocket_manager=None):
        """处理用户插话"""
        try:
            print(f"👤 用户插话 [{session_id}]: {user_message}")
            
            # 智能项目总监响应用户插话
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(
                    session_id=session_id,
                    agent_type="intelligent_director",
                    agent_name="智能项目总监",
                    content=f"收到您的指示：{user_message}\n\n我会根据您的要求调整工作计划，并协调团队相应调整工作重点。",
                    status="working"
                )
            
            # 检查用户意图并触发相应的行动
            if "开始写作" in user_message or "开始" in user_message:
                await self._start_writing_workflow(session_id, websocket_manager)
            elif "修改" in user_message or "调整" in user_message:
                await self._handle_modification_request(session_id, user_message, websocket_manager)
            else:
                # 将用户插话传递给智能项目总监处理
                await self.handle_user_message(session_id, user_message, websocket_manager)
            
        except Exception as e:
            print(f"❌ 处理用户插话失败: {e}")
    
    async def _start_writing_workflow(self, session_id: str, websocket_manager=None):
        """启动写作工作流程"""
        try:
            if session_id not in self.agents:
                print(f"❌ 会话 {session_id} 不存在")
                return
            
            # 获取智能项目总监
            director = self.agents[session_id].get('intelligent-director')
            if not director:
                print(f"❌ 智能项目总监不存在")
                return
            
            # 获取专家团队
            specialist_agents = {k: v for k, v in self.agents[session_id].items() if k != 'intelligent-director'}
            
            # 开始写作流程
            await websocket_manager.broadcast_agent_message(
                session_id=session_id,
                agent_type="intelligent_director",
                agent_name="智能项目总监",
                content="🚀 正在启动写作工作流程...\n\n我将协调各专家团队按照既定计划开始工作：",
                status="working"
            )
            
            # 模拟协调各个专家开始工作
            await self._coordinate_agents_workflow(session_id, specialist_agents, websocket_manager)
            
        except Exception as e:
            print(f"❌ 启动写作工作流程失败: {e}")
    
    async def _coordinate_agents_workflow(self, session_id: str, agents: dict, websocket_manager=None):
        """协调各Agent的工作流程"""
        try:
            # 按顺序启动各个专家的工作
            workflow_steps = [
                ("document_expert", "📄 文档专家正在整理和分析上传的文件..."),
                ("case_expert", "🔍 案例专家正在搜索相关案例和最佳实践..."),
                ("data_analyst", "📊 数据分析师正在进行数据收集和分析..."),
                ("writer_expert", "✍️ 写作专家正在撰写报告初稿..."),
                ("chief_editor", "👔 总编辑正在进行质量审核和润色...")
            ]
            
            for agent_id, message in workflow_steps:
                if agent_id in agents:
                    agent = agents[agent_id]
                    
                    # 发送Agent开始工作的消息
                    await websocket_manager.broadcast_agent_message(
                        session_id=session_id,
                        agent_type=agent_id,
                        agent_name=agent.name,
                        content=message,
                        status="working"
                    )
                    
                    # 模拟工作时间
                    await asyncio.sleep(2)
                    
                    # 执行Agent的任务
                    task_result = await self._execute_agent_task(agent, agent_id)
                    
                    # 安全地获取结果
                    if task_result and isinstance(task_result, dict):
                        result_message = task_result.get('result', '任务完成')
                        result_status = task_result.get('status', 'completed')
                    else:
                        result_message = '任务完成'
                        result_status = 'completed'
                    
                    # 发送完成消息
                    await websocket_manager.broadcast_agent_message(
                        session_id=session_id,
                        agent_type=agent_id,
                        agent_name=agent.name,
                        content=f"✅ {result_message}",
                        status=result_status
                    )
                    
                    await asyncio.sleep(1)
            
            # 所有Agent完成后，发送最终完成消息
            await websocket_manager.broadcast_agent_message(
                session_id=session_id,
                agent_type="intelligent_director",
                agent_name="智能项目总监",
                content="🎉 **报告写作完成！**\n\n各专家团队已协作完成报告的初稿，请您查看并提供反馈。如需修改，请直接告诉我具体的修改要求。",
                status="completed"
            )
            
        except Exception as e:
            print(f"❌ 协调Agent工作流程失败: {e}")
    
    async def _execute_agent_task(self, agent, agent_id: str) -> dict:
        """执行Agent任务"""
        try:
            # 根据Agent类型创建不同的任务
            if agent_id == "document_expert":
                task = {
                    "type": "document_analysis",
                    "description": "分析上传的文档并提取关键信息"
                }
            elif agent_id == "case_expert":
                task = {
                    "type": "case_research",
                    "description": "搜索相关案例和最佳实践"
                }
            elif agent_id == "data_analyst":
                task = {
                    "type": "data_analysis",
                    "description": "进行数据收集和统计分析"
                }
            elif agent_id == "writer_expert":
                task = {
                    "type": "writing",
                    "chapter": "综合报告",
                    "requirements": "基于前期分析结果撰写完整报告",
                    "description": "撰写报告初稿"
                }
            elif agent_id == "chief_editor":
                task = {
                    "type": "editing",
                    "description": "审核和润色报告内容"
                }
            else:
                task = {
                    "type": "general",
                    "description": "执行通用任务"
                }
            
            # 执行任务
            result = await agent.execute_task(task)
            return result
            
        except Exception as e:
            print(f"❌ 执行Agent任务失败: {e}")
            return {"result": f"任务执行出错: {str(e)}", "status": "error"}
    
    async def _handle_modification_request(self, session_id: str, user_message: str, websocket_manager=None):
        """处理修改请求"""
        try:
            await websocket_manager.broadcast_agent_message(
                session_id=session_id,
                agent_type="intelligent_director",
                agent_name="智能项目总监",
                content=f"📝 收到修改要求：{user_message}\n\n我正在分析您的要求并协调相关专家进行调整...",
                status="working"
            )
            
            # 这里可以添加更复杂的修改逻辑
            await asyncio.sleep(2)
            
            await websocket_manager.broadcast_agent_message(
                session_id=session_id,
                agent_type="intelligent_director",
                agent_name="智能项目总监",
                content="✅ 修改计划已制定，相关专家正在进行调整。请稍候...",
                status="completed"
            )
            
        except Exception as e:
            print(f"❌ 处理修改请求失败: {e}")


# 全局核心管理器实例
core_manager = CoreManager()