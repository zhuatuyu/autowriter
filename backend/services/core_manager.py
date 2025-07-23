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
from backend.services.llm.agents.enhanced_director import EnhancedDirectorAgent
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
                'memory_manager': memory_manager
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
            
            # 1. 创建增强版智能项目总监 (固定)
            director_workspace = Path(workspace_path) / "enhanced_director"
            director = EnhancedDirectorAgent(
                session_id=session_id,
                workspace_path=str(director_workspace),
                memory_manager=memory_manager
            )
            agents[director.agent_id] = director
            print(f"  ✅ 创建Agent: {director.name} ({director.role})")
            
            # 2. 创建专业Agent团队
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
        处理用户消息，使用增强版Director进行智能处理
        """
        try:
            print(f"👤 收到用户消息 [{session_id}]: {user_message[:80]}...")
            
            if session_id not in self.sessions_context:
                print(f"❌ 会话 {session_id} 不存在，正在尝试重新启动...")
                await self.start_session(session_id)
                if session_id not in self.sessions_context:
                    print(f"❌ 启动会话失败，无法处理消息")
                    return False
            
            session_context = self.sessions_context[session_id]
            
            # 获取增强版Director
            director = session_context['agents'].get('enhanced_director')
            if not director:
                print(f"❌ 增强版智能项目总监在会话 {session_id} 中不存在")
                return False
            
            # 构建上下文信息
            context = {
                'session_id': session_id,
                'session_info': {k: v for k, v in session_context.items() if k not in ['agents', 'memory_manager']},
                'available_agents': list(session_context['agents'].keys())
            }
            
            # 使用增强版Director的新接口处理请求
            response = await director.process_request(user_message, context)
            
            # 发送Director的响应
            if websocket_manager and response.get('success'):
                await websocket_manager.broadcast_agent_message(
                    session_id=session_id,
                    agent_type="enhanced_director",
                    agent_name=director.name,
                    content=response.get('message', '处理完成'),
                    status="completed"
                )
                
                # 根据响应类型执行后续行动
                await self._handle_director_response(session_id, response, websocket_manager)
            
            # 更新会话状态
            self.sessions_context[session_id]['status'] = 'in_progress'
            return True
            
        except Exception as e:
            print(f"❌ 处理用户消息时发生严重错误: {e}")
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(
                    session_id=session_id,
                    agent_type="system_error",
                    agent_name="系统错误",
                    content=f"处理请求时发生错误: {e}",
                    status="error"
                )
            return False
    
    async def _handle_director_response(self, session_id: str, response: Dict[str, Any], websocket_manager=None):
        """
        处理增强版Director的响应，根据响应类型执行相应的后续行动
        """
        try:
            response_type = response.get('response_type', 'communication')
            next_actions = response.get('next_actions', [])
            
            print(f"📋 Director响应类型: {response_type}, 后续行动: {next_actions}")
            
            if response_type == 'direct_answer':
                # 直接回答，无需进一步处理
                print(f"✅ Director直接回答了用户问题")
                
            elif response_type == 'simple_task' and next_actions:
                # 简单任务，委托给单个Agent
                await self._execute_simple_task(session_id, response, websocket_manager)
                
            elif response_type == 'complex_workflow' and next_actions:
                # 复杂工作流，需要多Agent协作
                await self._execute_complex_workflow(session_id, response, websocket_manager)
                
            elif response_type == 'consultation':
                # 专业咨询，可能需要后续服务
                await self._handle_consultation_followup(session_id, response, websocket_manager)
                
            else:
                # 其他类型的响应，记录日志
                print(f"📝 Director响应类型: {response_type}")
                
        except Exception as e:
            print(f"❌ 处理Director响应失败: {e}")
    
    async def _execute_simple_task(self, session_id: str, director_response: Dict[str, Any], websocket_manager=None):
        """
        执行简单任务 - 委托给单个Agent
        """
        try:
            next_actions = director_response.get('next_actions', [])
            if not next_actions:
                return
            
            target_agent_id = next_actions[0]
            
            agents = self.sessions_context[session_id]['agents']

            # 获取目标Agent
            if target_agent_id in agents:
                agent = agents[target_agent_id]
                
                # 通知开始执行任务
                if websocket_manager:
                    await websocket_manager.broadcast_agent_message(
                        session_id=session_id,
                        agent_type=target_agent_id,
                        agent_name=getattr(agent, 'name', target_agent_id),
                        content=f"🔄 正在处理您的请求...",
                        status="working"
                    )
                
                # 执行Agent任务
                task_result = await self._execute_agent_task(agent, target_agent_id)
                
                # 发送完成消息
                if websocket_manager:
                    result_message = task_result.get('result', '任务完成') if task_result else '任务完成'
                    await websocket_manager.broadcast_agent_message(
                        session_id=session_id,
                        agent_type=target_agent_id,
                        agent_name=getattr(agent, 'name', target_agent_id),
                        content=f"✅ {result_message}",
                        status="completed"
                    )
            else:
                print(f"❌ 目标Agent {target_agent_id} 不存在")
                
        except Exception as e:
            print(f"❌ 执行简单任务失败: {e}")
    
    async def _execute_complex_workflow(self, session_id: str, director_response: Dict[str, Any], websocket_manager=None):
        """
        执行复杂工作流 - 多Agent协作
        """
        try:
            task_plan = director_response.get('task_plan', {})
            steps = task_plan.get('steps', [])
            agents = self.sessions_context[session_id]['agents']

            if websocket_manager:
                await websocket_manager.broadcast_agent_message(
                    session_id=session_id,
                    agent_type="enhanced_director",
                    agent_name="智能项目总监",
                    content=f"🚀 开始执行复杂工作流，共{len(steps)}个步骤",
                    status="working"
                )
            
            # 按步骤执行
            for i, step in enumerate(steps, 1):
                agent_id = step.get('agent_id')
                action = step.get('action', 'process_user_request')
                
                if agent_id in agents:
                    agent = agents[agent_id]
                    
                    # 通知步骤开始
                    if websocket_manager:
                        await websocket_manager.broadcast_agent_message(
                            session_id=session_id,
                            agent_type=agent_id,
                            agent_name=getattr(agent, 'name', agent_id),
                            content=f"🔄 执行步骤 {i}/{len(steps)}: {step.get('expected_output', '处理中')}",
                            status="working"
                        )
                    
                    # 执行步骤
                    step_result = await self._execute_agent_task(agent, agent_id)
                    
                    # 通知步骤完成
                    if websocket_manager:
                        result_message = step_result.get('result', '步骤完成') if step_result else '步骤完成'
                        await websocket_manager.broadcast_agent_message(
                            session_id=session_id,
                            agent_type=agent_id,
                            agent_name=getattr(agent, 'name', agent_id),
                            content=f"✅ 步骤 {i} 完成: {result_message}",
                            status="completed"
                        )
                    
                    # 步骤间延迟
                    await asyncio.sleep(1)
            
            # 工作流完成
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(
                    session_id=session_id,
                    agent_type="enhanced_director",
                    agent_name="智能项目总监",
                    content="🎉 复杂工作流执行完成！所有步骤已成功完成。",
                    status="completed"
                )
                
        except Exception as e:
            print(f"❌ 执行复杂工作流失败: {e}")
    
    async def _handle_consultation_followup(self, session_id: str, director_response: Dict[str, Any], websocket_manager=None):
        """
        处理咨询后续服务
        """
        try:
            follow_up_services = director_response.get('follow_up_services', [])
            
            if follow_up_services and websocket_manager:
                services_text = "\n".join([f"• {service}" for service in follow_up_services])
                await websocket_manager.broadcast_agent_message(
                    session_id=session_id,
                    agent_type="enhanced_director",
                    agent_name="智能项目总监",
                    content=f"💡 如需进一步协助，我的团队可以提供以下服务：\n\n{services_text}",
                    status="completed"
                )
                
        except Exception as e:
            print(f"❌ 处理咨询后续服务失败: {e}")
    
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
            if hasattr(agent, 'execute_task'):
                result = await agent.execute_task(task)
            else:
                # 如果Agent没有execute_task方法，使用默认处理
                result = {"result": f"{agent_id}任务完成", "status": "completed"}
            
            return result
            
        except Exception as e:
            print(f"❌ 执行Agent任务失败: {e}")
            return {"result": f"任务执行出错: {str(e)}", "status": "error"}
    
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
                    if agent_id == 'enhanced_director':
                        continue  # 跳过项目总监，只显示专业Agent
                    
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