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
from backend.services.persistence import ProjectPersistence, BreakpointRecovery


class AICompany:
    """
    AI公司管理器 - 基于MetaGPT架构
    负责创建和管理单个项目的生命周期，对应MetaGPT的software_company.py
    """
    
    def __init__(self, session_id: str, workspace_root: str = None):
        """
        初始化AI公司
        
        Args:
            session_id: 会话ID，用于标识不同的项目会话
            workspace_root: 工作区根目录
        """
        self.session_id = session_id
        self.is_running = False
        self.current_idea = ""
        self.team = None
        
        # 初始化项目仓库
        if workspace_root:
            self.project_repo = ProjectRepo(workspace_root)
        else:
            # 使用默认的工作区路径
            default_workspace = Path.cwd() / "workspaces" / f"project_{session_id}"
            self.project_repo = ProjectRepo(str(default_workspace))
        
        # 初始化持久化服务
        self.persistence = ProjectPersistence(str(self.project_repo.root.parent))
        self.recovery = BreakpointRecovery(self.persistence)
        
        logger.info(f"🏢 AI公司初始化完成，会话ID: {session_id}")
        logger.info(f"📁 工作区路径: {self.project_repo.root}")
    
    def _setup_agents(self):
        """设置Agent团队"""
        # 创建MetaGPT Context
        self.context = Context()
        
        # 设置工作区路径
        self.context.kwargs.set("project_path", str(self.project_repo.root))
        self.context.kwargs.set("project_name", f"project_{self.session_id}")
        
        # 创建Team
        self.team = Team(context=self.context)
        
        # 添加团队领导者（MetaGPT MGX环境需要）
        from metagpt.roles.di.team_leader import TeamLeader
        team_leader = TeamLeader(name="王昭元")
        
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
            
            # 检查是否有断点可以恢复
            if await self.recovery.can_recover(self.session_id):
                logger.info(f"🔄 检测到断点，尝试恢复项目: {self.session_id}")
                if await self._recover_from_breakpoint(user_requirement, websocket_manager):
                    return True
            
            self.is_running = True
            self.current_idea = user_requirement
            
            logger.info(f"🚀 启动项目: {self.session_id}")
            logger.info(f"📝 用户需求: {user_requirement[:100]}{'...' if len(user_requirement) > 100 else ''}")
            
            # 初始化Agent团队
            self._setup_agents()
            
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
            
            # 保存项目状态
            success = self.persistence.save_project_state(self.session_id, {
                "user_requirement": user_requirement,
                "status": "started",
                "timestamp": datetime.now().isoformat()
            })
            if not success:
                logger.warning("⚠️ 项目状态保存失败，但继续执行")
            
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
            
            # 发送团队协作开始消息到前端
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(
                    session_id=self.session_id,
                    agent_type="system",
                    agent_name="系统",
                    content="🔄 开始团队协作，正在协调各个智能体工作...",
                    status="working"
                )
            
            # 保存协作开始断点
            await self.save_breakpoint("collaboration_start")
            
            # 运行团队协作（最多10轮）
            await self.team.run(n_round=10)
            
            logger.info(f"✅ 团队协作完成: {self.session_id}")
            
            # 保存协作完成断点
            await self.save_breakpoint("collaboration_completed")
            
            # 发送团队协作完成消息到前端
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(
                    session_id=self.session_id,
                    agent_type="system",
                    agent_name="系统",
                    content="✅ 团队协作完成！所有智能体已完成各自的任务。",
                    status="completed"
                )
            
            logger.info(f"🎉 项目协作完成！所有任务已完成。")
            
            # 发送项目完成消息到前端
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(
                    session_id=self.session_id,
                    agent_type="system",
                    agent_name="项目管理器",
                    content="🎉 项目协作完成！所有任务已完成，请查看工作区中的输出结果。",
                    status="completed"
                )
                
        except Exception as e:
            logger.error(f"❌ 团队协作失败: {e}")
            
            # 保存错误断点
            await self.save_breakpoint("collaboration_error", {"error": str(e)})
            
            # 发送错误消息到前端
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(
                    session_id=self.session_id,
                    agent_type="system",
                    agent_name="系统",
                    content=f"❌ 团队协作失败: {str(e)}",
                    status="error"
                )
        finally:
            self.is_running = False
            # 保存项目结束状态
            success = self.persistence.save_project_state(self.session_id, {
                "status": "completed" if not hasattr(self, '_error_occurred') else "error",
                "timestamp": datetime.now().isoformat()
            })
            if not success:
                logger.warning("⚠️ 项目结束状态保存失败")
    
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
                    
                    # 不直接保存WebSocket管理器引用，避免序列化问题
                    # 使用全局引用或者通过其他方式传递
                    role.session_id = self.session_id
                    role._websocket_session_id = self.session_id  # 用于标识session
                    
                    # 重写Role的_act方法以支持WebSocket消息发送
                    self._create_enhanced_act_method(role, websocket_manager)
                    
                    logger.info(f"✅ 为ProjectManager {role.name} (profile: {role.profile}) 设置WebSocket监听")
                    
                except Exception as e:
                    logger.error(f"❌ 为Agent {role_name} 设置WebSocket监听失败: {e}")
                    logger.error(f"❌ 错误详情: {type(e).__name__}: {str(e)}")
                    # 继续处理其他角色，不中断整个流程
                    continue
                
            logger.info(f"✅ WebSocket监听设置完成，只监听ProjectManager消息")
    
    def _create_enhanced_act_method(self, role, websocket_manager):
        """为指定角色创建增强的_act方法"""
        try:
            # 添加更详细的调试信息
            logger.info(f"🔧 开始为角色 {getattr(role, 'name', 'Unknown')} 创建增强方法")
            logger.info(f"🔧 角色类型: {type(role)}")
            logger.info(f"🔧 角色profile: {getattr(role, 'profile', 'None')}")
            
            original_act = role._act
            
            # 使用默认参数来捕获当前的role值，避免闭包变量问题
            def make_enhanced_act(current_role, ws_manager):
                async def enhanced_act():
                    """增强的_act方法，支持WebSocket消息发送"""
                    try:
                        # 发送开始工作状态
                        if ws_manager:
                            # 安全获取profile和name
                            profile_obj = getattr(current_role, 'profile', None)
                            name_obj = getattr(current_role, 'name', None)
                            
                            profile_str = str(profile_obj) if profile_obj is not None else "unknown"
                            name_str = str(name_obj) if name_obj is not None else "Unknown"
                            
                            await ws_manager.broadcast_agent_message(
                                session_id=current_role.session_id,
                                agent_type=profile_str.lower().replace(" ", "_"),
                                agent_name=name_str,
                                content=f"🔄 {name_str} 开始工作...",
                                status="thinking"
                            )
                        
                        # 执行原始的_act方法
                        result = await original_act()
                        
                        # 检查是否是RoleZero的ask_human命令 - 基于MetaGPT原生实现
                        if ws_manager:
                            logger.info(f"🔍 开始检查ask_human命令，角色类型: {type(current_role).__name__}")
                            
                            # 安全获取profile和name
                            profile_obj = getattr(current_role, 'profile', None)
                            name_obj = getattr(current_role, 'name', None)
                            
                            profile_str = str(profile_obj) if profile_obj is not None else "unknown"
                            name_str = str(name_obj) if name_obj is not None else "Unknown"
                            
                            logger.info(f"🔍 角色信息: profile={profile_str}, name={name_str}")
                            
                            # 基于MetaGPT原生实现：检查RoleZero的commands属性
                            commands_to_check = []
                            
                            # 1. 检查 current_role.commands - MetaGPT原生存储位置
                            if hasattr(current_role, 'commands'):
                                logger.info(f"🔍 角色有commands属性: {current_role.commands}")
                                if current_role.commands:
                                    commands_to_check.extend(current_role.commands)
                                    logger.info(f"🔍 发现RoleZero commands: {current_role.commands}")
                            else:
                                logger.info(f"🔍 角色没有commands属性")
                            
                            # 2. 检查 command_rsp - 原始命令响应字符串
                            if hasattr(current_role, 'command_rsp'):
                                logger.info(f"🔍 角色有command_rsp属性: {getattr(current_role, 'command_rsp', None) is not None}")
                                command_rsp = current_role.command_rsp
                                if command_rsp and 'ask_human' in command_rsp:
                                    logger.info(f"🔍 在command_rsp中发现ask_human: {command_rsp[:200]}...")
                                    # 尝试解析命令
                                    try:
                                        import json
                                        import re
                                        # 查找JSON格式的命令
                                        json_matches = re.findall(r'\[.*?\]', command_rsp, re.DOTALL)
                                        for match in json_matches:
                                            try:
                                                parsed_commands = json.loads(match)
                                                if isinstance(parsed_commands, list):
                                                    commands_to_check.extend(parsed_commands)
                                                    logger.info(f"🔍 从command_rsp解析命令: {parsed_commands}")
                                            except:
                                                continue
                                    except Exception as e:
                                        logger.warning(f"解析command_rsp失败: {e}")
                            else:
                                logger.info(f"🔍 角色没有command_rsp属性")
                            
                            logger.info(f"🔍 总共找到 {len(commands_to_check)} 个命令待检查")
                            
                            # 处理所有找到的命令
                            for i, command in enumerate(commands_to_check):
                                logger.info(f"🔍 检查命令 {i+1}: {command}")
                                if isinstance(command, dict):
                                    command_name = command.get('command_name', '')
                                    logger.info(f"🔍 命令名称: {command_name}")
                                    
                                    if command_name == 'RoleZero.ask_human':
                                        question = command.get('args', {}).get('question', '')
                                        logger.info(f"🔍 找到ask_human命令，问题: {question[:100]}...")
                                        if question:
                                            # 发送用户交互请求到前端
                                            message_data = {
                                                "type": "user_interaction_request",
                                                "agent_name": name_str,
                                                "agent_type": profile_str.lower().replace(" ", "_"),
                                                "question": question,
                                                "timestamp": datetime.now().isoformat()
                                            }
                                            logger.info(f"📤 准备发送消息: {message_data}")
                                            
                                            success = await ws_manager.send_message(
                                                current_role.session_id,
                                                message_data
                                            )
                                            logger.info(f"📤 消息发送结果: {success}")
                                            logger.info(f"📤 发送用户交互请求到前端: {question[:100]}...")
                                            
                                            # 保存断点 - 等待用户回复
                                            await self.save_breakpoint("user_interaction", {
                                                "agent_name": name_str,
                                                "question": question,
                                                "waiting_for_response": True
                                            })
                                            
                                            return result
                                    
                                    elif command_name == 'RoleZero.reply_to_human':
                                        content = command.get('args', {}).get('content', '')
                                        if content:
                                            # 发送智能体回复到前端
                                            await ws_manager.broadcast_agent_message(
                                                session_id=current_role.session_id,
                                                agent_type=profile_str.lower().replace(" ", "_"),
                                                agent_name=name_str,
                                                content=content,
                                                status="completed"
                                            )
                                            logger.info(f"📤 发送智能体回复到前端: {content[:100]}...")
                                            return result
                            
                            # 发送完成状态和结果（如果不是ask_human命令）
                            if result:
                                content = result.content if hasattr(result, 'content') else str(result)
                                await ws_manager.broadcast_agent_message(
                                    session_id=current_role.session_id,
                                    agent_type=profile_str.lower().replace(" ", "_"),
                                    agent_name=name_str,
                                    content=content[:500] + "..." if len(content) > 500 else content,
                                    status="completed"
                                )
                        
                        return result
                        
                    except Exception as e:
                        logger.error(f"Agent {getattr(current_role, 'name', 'Unknown')} 执行失败: {e}")
                        if ws_manager:
                            # 安全获取profile和name
                            profile_obj = getattr(current_role, 'profile', None)
                            name_obj = getattr(current_role, 'name', None)
                            
                            profile_str = str(profile_obj) if profile_obj is not None else "unknown"
                            name_str = str(name_obj) if name_obj is not None else "Unknown"
                            
                            await ws_manager.broadcast_agent_message(
                                session_id=current_role.session_id,
                                agent_type=profile_str.lower().replace(" ", "_"),
                                agent_name=name_str,
                                content=f"❌ 执行出错: {str(e)}",
                                status="error"
                            )
                        raise
                return enhanced_act
            
            # 绑定增强的方法
            role._act = make_enhanced_act(role, websocket_manager).__get__(role, type(role))
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
    
    async def _recover_from_breakpoint(self, user_requirement: str, websocket_manager: WebSocketManager = None) -> bool:
        """从断点恢复项目"""
        try:
            logger.info(f"🔄 开始从断点恢复项目: {self.session_id}")
            
            # 恢复项目状态
            recovered_state = await self.recovery.recover_project(self.session_id)
            if not recovered_state:
                logger.warning(f"⚠️ 无法恢复项目状态: {self.session_id}")
                return False
            
            self.is_running = True
            self.current_idea = recovered_state.get("user_requirement", user_requirement)
            
            # 重新初始化Agent团队
            self._setup_agents()
            
            # 设置投资预算
            self.team.invest(10.0)
            
            if websocket_manager:
                await websocket_manager.broadcast_agent_message(
                    session_id=self.session_id,
                    agent_type="system",
                    agent_name="系统",
                    content="🔄 项目已从断点恢复，继续执行...",
                    status="recovered"
                )
            
            # 继续运行团队协作
            asyncio.create_task(self._run_team_collaboration(websocket_manager))
            
            logger.info(f"✅ 项目从断点恢复成功: {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 从断点恢复项目失败: {e}")
            return False
    
    async def save_breakpoint(self, stage: str, data: Dict = None):
        """保存断点"""
        try:
            breakpoint_data = {
                "session_id": self.session_id,
                "stage": stage,
                "timestamp": datetime.now().isoformat(),
                "user_requirement": self.current_idea,
                "is_running": self.is_running,
                "data": data or {}
            }
            
            await self.recovery.save_breakpoint(self.session_id, stage, breakpoint_data)
            logger.info(f"💾 断点已保存: {self.session_id} - {stage}")
            
        except Exception as e:
            logger.error(f"❌ 保存断点失败: {e}")
    
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