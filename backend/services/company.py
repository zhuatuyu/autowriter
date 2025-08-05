"""
公司服务 - 智能体团队管理
基于新的SOP和Agent架构
"""
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

from metagpt.team import Team
from metagpt.environment import Environment
from metagpt.logs import logger
from metagpt.utils.project_repo import ProjectRepo
from metagpt.schema import Message
from metagpt.actions import UserRequirement

from backend.roles.product_manager import ProductManager
from backend.roles.architect import Architect
from backend.roles.project_manager import ProjectManager as PM
from backend.roles.writer_expert import WriterExpert
from backend.actions.research_action import Documents, Document
import chainlit as cl


class Company:
    """
    公司服务 - 基于新SOP的智能体团队管理
    """
    
    def __init__(self):
        self.teams: Dict[str, Team] = {}
        self.project_repos: Dict[str, ProjectRepo] = {}

    async def process_message(self, project_id: str, message: str, environment: Environment, file_paths: Optional[List[str]] = None) -> str:
        """
        处理用户消息，创建或获取团队，并执行任务
        """
        try:
            # 获取或创建团队
            team = await self._get_or_create_team(project_id, environment)
            
            # 路由消息到团队
            result = await self._route_message(team, message, project_id, file_paths)
            
            return result
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            return f"处理失败: {str(e)}"

    async def _get_or_create_team(self, project_id: str, environment: Environment) -> Team:
        """
        获取或创建基于新SOP的智能体团队
        """
        if project_id in self.teams:
            return self.teams[project_id]
        
        # 创建工作空间
        workspace_path = Path("workspace") / project_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 创建uploads目录
        uploads_path = workspace_path / "uploads"
        uploads_path.mkdir(exist_ok=True)
        
        # 创建项目仓库
        project_repo = ProjectRepo(workspace_path).with_src_path(workspace_path)
        self.project_repos[project_id] = project_repo
        
        # 创建自定义的 TeamLeader，使用 ProductManager 的搜索配置
        from backend.roles.custom_team_leader import CustomTeamLeader
        
        # 创建新的智能体团队 (按照SOP顺序)
        team_leader = CustomTeamLeader()  # 使用自定义的团队领导者
        product_manager = ProductManager()
        architect = Architect()
        project_manager = PM()
        writer_expert = WriterExpert()

        # 为需要访问文件的智能体注入 project_repo (使用私有属性避免序列化问题)
        product_manager._project_repo = project_repo
        architect._project_repo = project_repo
        writer_expert._project_repo = project_repo
        
        # 创建团队
        team = Team(
            investment=10.0,
            environment=environment,
        )
        
        # 按照SOP顺序雇佣成员 - 必须包含TeamLeader
        team.hire([
            team_leader,      # 使用自定义的团队领导者
            product_manager,  # 需求分析与研究
            architect,        # 架构设计
            project_manager,  # 任务规划
            writer_expert     # 内容生成
        ])
        
        self.teams[project_id] = team
        logger.info(f"新SOP团队设置完成，共{len(team.env.roles)}个智能体")
        
        return team

    async def _route_message(self, team: Team, message: str, project_id: str, file_paths: Optional[List[str]] = None) -> str:
        """
        路由消息到团队并执行SOP流程
        """
        try:
            roles = list(team.env.roles.values())
            logger.info(f"🚀 开始处理用户消息: {message}")
            logger.info(f"📋 当前团队成员: {[role.name for role in roles]}")
            
            # 验证所有角色都有profile属性
            for role in roles:
                if role is None:
                    raise ValueError(f"发现空角色对象")
                if not hasattr(role, 'profile'):
                    raise ValueError(f"角色 {role.name} 缺少 profile 属性")
                if role.profile is None:
                    raise ValueError(f"角色 {role.name} 的 profile 为 None")
                logger.info(f"✅ 角色验证通过: {role.name} - {role.profile}")
            
            if file_paths:
                logger.info(f"📁 上传的文件: {file_paths}")
            
            # 发布用户需求消息
            logger.info("📤 发布用户需求消息")
            user_msg = Message(content=message, cause_by=UserRequirement)
            
            # 如果有文件路径，处理文件并移动到正确位置
            if file_paths:
                # 获取正确的uploads目录
                workspace_path = Path("workspace") / project_id
                correct_uploads_path = workspace_path / "uploads"
                correct_uploads_path.mkdir(parents=True, exist_ok=True)
                
                docs = []
                corrected_file_paths = []
                
                for file_path in file_paths:
                    try:
                        source_path = Path(file_path)
                        if source_path.exists() and source_path.is_file():
                            # 移动文件到正确的uploads目录
                            target_path = correct_uploads_path / source_path.name
                            
                            # 如果文件不在正确位置，则移动它
                            if source_path.parent != correct_uploads_path:
                                import shutil
                                shutil.move(str(source_path), str(target_path))
                                logger.info(f"文件已移动: {source_path} -> {target_path}")
                            else:
                                target_path = source_path
                            
                            # 读取文件内容
                            content = target_path.read_text(encoding='utf-8')
                            docs.append(Document(filename=target_path.name, content=content))
                            corrected_file_paths.append(str(target_path))
                            logger.info(f"成功处理文件: {target_path.name}")
                            
                    except Exception as e:
                        logger.error(f"处理文件失败 {file_path}: {e}")
                    
                # 创建Documents对象并正确序列化
                if docs:
                    documents = Documents(docs=docs)
                    # 直接将Documents对象赋值给instruct_content
                    # 之前的Message.create_instruct_value(documents)调用是错误的
                    user_msg.instruct_content = documents

            # 发布用户需求消息
            logger.info("📤 发布用户需求消息")
            team.env.publish_message(user_msg)

            # 启动SOP流程
            logger.info(f"🔄 开始SOP流程: {project_id}")
            await self._run_team_with_frontend_updates(team, project_id)
            
            return "SOP流程执行完成，报告已生成"
            
        except Exception as e:
            logger.error(f"❌ SOP流程执行失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise

    async def _run_team_with_frontend_updates(self, team: Team, project_id: str):
        """
        运行团队SOP流程并向前端推送更新
        """
        try:
            # 验证团队状态
            if not team or not team.env:
                raise ValueError("团队或环境未正确初始化")
            
            # 验证所有角色都有profile属性
            for role_name, role in team.env.roles.items():
                if role is None:
                    raise ValueError(f"角色 {role_name} 为 None")
                if not hasattr(role, 'profile') or role.profile is None:
                    raise ValueError(f"角色 {role_name} 缺少 profile 属性")
                logger.info(f"✅ 角色验证通过: {role_name} - {role.profile}")
            
            # 启动消息监控
            monitor_task = asyncio.create_task(self._monitor_team_messages(team))
            
            # 启动团队任务 (增加轮次确保所有智能体都能参与，特别是Architect处理时间增长后)
            logger.info("🔄 启动团队SOP流程...")
            team_task = asyncio.create_task(team.run(n_round=10))
            
            # 等待团队完成
            await team_task
            logger.info("✅ 团队SOP流程执行完成")
            
            # 取消监控任务
            monitor_task.cancel()
            
        except Exception as e:
            logger.error(f"团队SOP流程失败: {e}")
            logger.error(f"错误类型: {type(e)}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            
            # 确保监控任务被取消
            if 'monitor_task' in locals():
                monitor_task.cancel()
            raise

    async def _monitor_team_messages(self, team: Team):
        """
        监控团队消息并向前端推送
        """
        last_sent_idx = -1

        try:
            while True:
                if team.env.history and team.env.history.storage:
                    current_msg_count = len(team.env.history.storage)
                    if current_msg_count > last_sent_idx + 1:
                        new_messages = team.env.history.storage[last_sent_idx + 1:]
                        for msg in new_messages:
                            # 添加详细的空值检查
                            if msg is None:
                                logger.warning("发现空消息，跳过")
                                continue
                            
                            # 检查消息属性
                            if not hasattr(msg, 'role'):
                                logger.warning(f"消息缺少role属性: {type(msg)}")
                                continue
                                
                            if msg.role is None:
                                logger.warning("消息的role为None")
                                continue
                                
                            if msg.role == "User":
                                continue
                            
                            # 安全获取author信息
                            try:
                                author = getattr(msg, 'sent_from', None) or getattr(msg, 'role', 'Unknown')
                                if author and hasattr(msg, 'content'):
                                    await self._send_to_frontend(
                                        message=msg.content or "", 
                                        author=str(author)
                                    )
                            except Exception as msg_error:
                                logger.error(f"处理消息时出错: {msg_error}, 消息类型: {type(msg)}")
                                
                        last_sent_idx = current_msg_count - 1

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("消息监控任务已取消")
        except Exception as e:
            logger.error(f"消息监控失败: {e}")
            import traceback
            logger.error(f"监控错误堆栈: {traceback.format_exc()}")

    async def _send_to_frontend(self, message: str, author: str):
        """
        向前端发送消息
        """
        logger.info(f"📤 推送消息到前端 from {author}: {message[:100]}...")
        await cl.Message(content=message, author=author).send()