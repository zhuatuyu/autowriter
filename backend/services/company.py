"""
AI公司管理器 - 基于MetaGPT架构的重构版本
参考MetaGPT的software_company.py和team.py实现
"""
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from metagpt.context import Context
from metagpt.team import Team
from metagpt.schema import Message
from metagpt.logs import logger
from metagpt.roles.di.team_leader import TeamLeader

from backend.roles.project_manager import ProjectManagerAgent
from backend.roles.case_expert import CaseExpertAgent
from backend.roles.writer_expert import WriterExpertAgent
from backend.roles.data_analyst import DataAnalystAgent
from backend.utils.project_repo import ProjectRepo
from backend.services.websocket_manager import WebSocketManager


class AICompany:
    """
    AI公司管理器 - 基于MetaGPT架构
    负责创建和管理单个项目的生命周期，对应MetaGPT的software_company.py
    """
    
    def __init__(self, session_id: str, project_info: Dict = None):
        self.session_id = session_id
        self.project_info = project_info or {}
        
        # 创建MetaGPT Context
        self.context = Context()
        
        # 创建项目仓库
        self.project_repo = ProjectRepo(session_id)
        
        # 设置工作区路径
        self.context.kwargs.set("project_path", str(self.project_repo.root))
        self.context.kwargs.set("project_name", f"project_{session_id}")
        
        # 创建Team
        self.team = Team(context=self.context)
        
        # 初始化Agent团队
        self._setup_agents()
        
        # 状态管理
        self.is_running = False
        self.current_idea = ""
        
        logger.info(f"AI公司管理器初始化完成: {session_id}")
    
    def _setup_agents(self):
        """设置Agent团队"""
        # 添加团队领导者（MetaGPT MGX环境需要）
        from metagpt.roles.di.team_leader import TeamLeader
        team_leader = TeamLeader(name="Mike")
        
        # 创建ProjectManager (类似MetaGPT的ProjectManager)
        project_manager = ProjectManagerAgent()
        
        # 创建专业Agent团队
        case_expert = CaseExpertAgent()
        case_expert.project_repo = self.project_repo
        
        writer_expert = WriterExpertAgent()
        writer_expert.project_repo = self.project_repo
        
        data_analyst = DataAnalystAgent()
        data_analyst.project_repo = self.project_repo
        
        # 雇佣所有Agent（首先添加团队领导者）
        agents = [team_leader, project_manager, case_expert, writer_expert, data_analyst]
        self.team.hire(agents)
        
        logger.info(f"Agent团队设置完成，共{len(agents)}个Agent（包含团队领导者）")
    
    async def start_project(self, user_requirement: str, websocket_manager: WebSocketManager = None) -> bool:
        """
        启动项目 - 类似MetaGPT的generate_repo函数
        
        Args:
            user_requirement: 用户需求描述
            websocket_manager: WebSocket管理器用于实时通信
        
        Returns:
            bool: 启动是否成功
        """
        try:
            if self.is_running:
                logger.warning(f"项目 {self.session_id} 已在运行中，忽略重复启动请求")
                return True  # 返回True表示项目已经在运行，不是错误
            
            self.is_running = True
            self.current_idea = user_requirement
            
            logger.info(f"🚀 启动项目: {self.session_id}")
            logger.info(f"📝 用户需求: {user_requirement[:100]}{'...' if len(user_requirement) > 100 else ''}")
            
            # 设置投资预算（类似MetaGPT）
            self.team.invest(10.0)  # 设置预算
            
            # 如果有WebSocket管理器，设置消息监听
            if websocket_manager:
                await self._setup_websocket_monitoring(websocket_manager)
                
                # 移除系统启动消息，只显示ProjectManager的工作状态
                logger.info(f"🚀 项目启动中: {user_requirement[:100]}{'...' if len(user_requirement) > 100 else ''}")
            
            # 发布用户需求到环境
            user_msg = Message(
                role="user",
                content=user_requirement,
                sent_from="user",
                send_to={"all"}
            )
            
            # 直接使用_publish_message方法，绕过团队领导者检查
            logger.info("📤 直接发布用户消息到环境")
            self.team.env._publish_message(user_msg)
            
            # 调试：检查所有角色对象的状态
            logger.info("🔍 检查所有角色对象状态:")
            for role_name, role in self.team.env.roles.items():
                logger.info(f"  角色 {role_name}: type={type(role)}, is_none={role is None}")
                if role is not None:
                    logger.info(f"    - name: {getattr(role, 'name', 'NO_NAME')}")
                    logger.info(f"    - profile: {getattr(role, 'profile', 'NO_PROFILE')}")
                    logger.info(f"    - has_websocket_manager: {hasattr(role, 'websocket_manager')}")
                else:
                    logger.error(f"    ❌ 角色 {role_name} 为 None!")
            
            # 启动异步任务运行团队协作
            asyncio.create_task(self._run_team_collaboration(websocket_manager))
            
            logger.info(f"✅ 项目 {self.session_id} 启动成功，团队开始协作")
            return True
            
        except Exception as e:
            logger.error(f"❌ 项目启动失败: {e}")
            logger.error(f"❌ 错误类型: {type(e).__name__}")
            import traceback
            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
            self.is_running = False
            if websocket_manager:
                await websocket_manager.send_message(self.session_id, {
                    "type": "system_message",
                    "sender": "system",
                    "content": f"❌ 项目启动失败: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
            return False
    
    async def _run_team_collaboration(self, websocket_manager: WebSocketManager = None):
        """运行团队协作"""
        try:
            logger.info(f"🔄 开始团队协作: {self.session_id}")
            
            # 运行团队协作（最多10轮）
            await self.team.run(n_round=10)
            
            logger.info(f"✅ 团队协作完成: {self.session_id}")
            
            # 移除系统完成消息，只显示ProjectManager的最终结果
            logger.info(f"🎉 项目协作完成！所有任务已完成。")
                
        except Exception as e:
            logger.error(f"❌ 团队协作失败: {e}")
            # 移除系统错误消息，只保留日志记录
        finally:
            self.is_running = False
    
    async def _setup_websocket_monitoring(self, websocket_manager: WebSocketManager):
        """设置WebSocket消息监听 - 只监听ProjectManager"""
        # 设置环境消息监听器
        if self.team and self.team.env:
            logger.info(f"🔍 开始设置WebSocket监听，环境中有 {len(self.team.env.roles)} 个角色")
            logger.info(f"🔍 角色字典内容: {list(self.team.env.roles.keys())}")
            
            # 只为ProjectManager设置WebSocket消息转发，忽略其他Agent
            for role_name, role in self.team.env.roles.items():
                try:
                    logger.info(f"🔍 处理角色: {role_name}, 类型: {type(role)}")
                    
                    # 检查role是否是有效的对象
                    if isinstance(role, str):
                        logger.warning(f"⚠️ 跳过字符串类型的role: {role}")
                        continue
                    
                    if not hasattr(role, 'name') or not hasattr(role, 'profile'):
                        logger.warning(f"⚠️ 跳过无效的role对象 {role_name}: {type(role)}")
                        continue
                    
                    # 只监听ProjectManager的消息，忽略其他Agent
                    profile_str = str(getattr(role, 'profile', ''))
                    if 'Project Manager' not in profile_str and 'ProjectManager' not in profile_str:
                        logger.info(f"⏭️ 跳过非ProjectManager角色: {role.name} (profile: {profile_str})")
                        continue
                    
                    # 保存WebSocket管理器引用
                    role.websocket_manager = websocket_manager
                    role.session_id = self.session_id
                    
                    # 重写Role的_act方法以支持WebSocket消息发送
                    self._create_enhanced_act_method(role)
                    
                    logger.info(f"✅ 为ProjectManager {role.name} (profile: {role.profile}) 设置WebSocket监听")
                    
                except Exception as e:
                    logger.error(f"❌ 为Agent {role_name} 设置WebSocket监听失败: {e}")
                    logger.error(f"❌ 错误详情: {type(e).__name__}: {str(e)}")
                    # 继续处理其他角色，不中断整个流程
                    continue
                
            logger.info(f"✅ WebSocket监听设置完成，只监听ProjectManager消息")
    
    def _create_enhanced_act_method(self, role):
        """为指定角色创建增强的_act方法"""
        try:
            # 添加更详细的调试信息
            logger.info(f"🔧 开始为角色 {getattr(role, 'name', 'Unknown')} 创建增强方法")
            logger.info(f"🔧 角色类型: {type(role)}")
            logger.info(f"🔧 角色profile: {getattr(role, 'profile', 'None')}")
            
            original_act = role._act
            
            # 使用默认参数来捕获当前的role值，避免闭包变量问题
            def make_enhanced_act(current_role):
                async def enhanced_act():
                    """增强的_act方法，支持WebSocket消息发送"""
                    try:
                        # 发送开始工作状态
                        if hasattr(current_role, 'websocket_manager') and current_role.websocket_manager:
                            # 安全获取profile和name
                            profile_obj = getattr(current_role, 'profile', None)
                            name_obj = getattr(current_role, 'name', None)
                            
                            profile_str = str(profile_obj) if profile_obj is not None else "unknown"
                            name_str = str(name_obj) if name_obj is not None else "Unknown"
                            
                            await current_role.websocket_manager.broadcast_agent_message(
                                session_id=current_role.session_id,
                                agent_type=profile_str.lower().replace(" ", "_"),
                                agent_name=name_str,
                                content=f"🔄 {name_str} 开始工作...",
                                status="thinking"
                            )
                        
                        # 执行原始的_act方法
                        result = await original_act()
                        
                        # 检查是否是RoleZero的ask_human命令
                        if hasattr(current_role, 'websocket_manager') and current_role.websocket_manager:
                            # 安全获取profile和name
                            profile_obj = getattr(current_role, 'profile', None)
                            name_obj = getattr(current_role, 'name', None)
                            
                            profile_str = str(profile_obj) if profile_obj is not None else "unknown"
                            name_str = str(name_obj) if name_obj is not None else "Unknown"
                            
                            # 检查是否有待执行的ask_human命令
                            if hasattr(current_role, 'rc') and hasattr(current_role.rc, 'todo_commands'):
                                for command in current_role.rc.todo_commands:
                                    if command.get('command_name') == 'RoleZero.ask_human':
                                        question = command.get('args', {}).get('question', '')
                                        if question:
                                            # 发送用户交互请求到前端
                                            await current_role.websocket_manager.send_message(
                                                current_role.session_id,
                                                {
                                                    "type": "user_interaction_request",
                                                    "agent_name": name_str,
                                                    "agent_type": profile_str.lower().replace(" ", "_"),
                                                    "question": question,
                                                    "timestamp": datetime.now().isoformat()
                                                }
                                            )
                                            logger.info(f"📤 发送用户交互请求到前端: {question[:100]}...")
                                            return result
                            
                            # 发送完成状态和结果（如果不是ask_human命令）
                            if result:
                                content = result.content if hasattr(result, 'content') else str(result)
                                await current_role.websocket_manager.broadcast_agent_message(
                                    session_id=current_role.session_id,
                                    agent_type=profile_str.lower().replace(" ", "_"),
                                    agent_name=name_str,
                                    content=content[:500] + "..." if len(content) > 500 else content,
                                    status="completed"
                                )
                        
                        return result
                        
                    except Exception as e:
                        logger.error(f"Agent {getattr(current_role, 'name', 'Unknown')} 执行失败: {e}")
                        if hasattr(current_role, 'websocket_manager') and current_role.websocket_manager:
                            # 安全获取profile和name
                            profile_obj = getattr(current_role, 'profile', None)
                            name_obj = getattr(current_role, 'name', None)
                            
                            profile_str = str(profile_obj) if profile_obj is not None else "unknown"
                            name_str = str(name_obj) if name_obj is not None else "Unknown"
                            
                            await current_role.websocket_manager.broadcast_agent_message(
                                session_id=current_role.session_id,
                                agent_type=profile_str.lower().replace(" ", "_"),
                                agent_name=name_str,
                                content=f"❌ 执行出错: {str(e)}",
                                status="error"
                            )
                        raise
                return enhanced_act
            
            # 绑定增强的方法
            role._act = make_enhanced_act(role).__get__(role, type(role))
            logger.info(f"✅ 为角色 {getattr(role, 'name', 'Unknown')} 创建增强方法成功")
            
        except Exception as e:
            logger.error(f"❌ 为角色 {getattr(role, 'name', 'Unknown')} 创建增强方法失败: {e}")
            logger.error(f"❌ 错误详情: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
            raise
    
    def get_project_status(self) -> Dict[str, Any]:
        """获取项目状态"""
        return {
            "session_id": self.session_id,
            "is_running": self.is_running,
            "current_idea": self.current_idea,
            "project_path": str(self.project_repo.root),
            "total_cost": self.team.cost_manager.total_cost if self.team else 0,
            "max_budget": self.team.cost_manager.max_budget if self.team else 0,
            "agents_count": len(self.team.env.roles) if self.team and self.team.env else 0
        }
    
    async def handle_user_message(self, message: str, websocket_manager: WebSocketManager = None) -> bool:
        """
        处理用户消息 - 简化版本
        在项目运行期间接收用户的额外指令
        """
        try:
            if not self.is_running:
                # 如果项目未运行，启动新项目
                return await self.start_project(message, websocket_manager)
            
            # 如果项目正在运行，可以发送消息到环境中
            if self.team and self.team.env:
                user_msg = Message(content=message, role="User")
                self.team.env.publish_message(user_msg)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"处理用户消息失败: {e}")
            return False
    
    def stop_project(self):
        """停止项目"""
        self.is_running = False
        logger.info(f"项目 {self.session_id} 已停止")
    
    def get_project_outputs(self) -> List[Dict]:
        """获取项目输出文件"""
        outputs = []
        if self.project_repo.outputs.exists():
            for file_path in self.project_repo.outputs.rglob("*"):
                if file_path.is_file():
                    outputs.append({
                        "name": file_path.name,
                        "path": str(file_path.relative_to(self.project_repo.root)),
                        "full_path": str(file_path),
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
        return outputs