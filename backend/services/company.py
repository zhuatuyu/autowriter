"""
公司服务 - 智能体团队管理
使用MetaGPT原生的项目管理和序列化机制
"""
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from metagpt.team import Team
from metagpt.environment import Environment
from metagpt.logs import logger
from metagpt.roles.di.team_leader import TeamLeader
from metagpt.utils.project_repo import ProjectRepo
from metagpt.schema import Message

from backend.roles.project_manager import ProjectManagerAgent
from backend.roles.architect import ArchitectAgent
from backend.roles.case_expert import CaseExpertAgent
from backend.roles.data_analyst import DataAnalystAgent
from backend.roles.writer_expert import WriterExpertAgent
import chainlit as cl
from metagpt.const import METAGPT_ROOT


class Company:
    """
    公司服务 - 智能体团队管理
    使用MetaGPT原生的项目管理和序列化机制
    """
    
    def __init__(self):
        self.teams: Dict[str, Team] = {}
        self.project_repos: Dict[str, ProjectRepo] = {}

    async def process_message(self, project_id: str, message: str, environment: Environment) -> str:
        """
        处理用户消息，创建或获取团队，并执行任务
        """
        try:
            # 获取或创建团队
            team = await self._get_or_create_team(project_id, environment)
            
            # 路由消息到团队
            result = await self._route_message(team, message, project_id)
            
            return result
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            return f"处理失败: {str(e)}"

    async def _get_or_create_team(self, project_id: str, environment: Environment) -> Team:
        """
        获取或创建智能体团队
        """
        if project_id in self.teams:
            return self.teams[project_id]
        
        # 创建项目仓库 - 使用MetaGPT原生的项目路径
        workspace_path = Path(f"workspaces/{project_id}")
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        project_repo = ProjectRepo(workspace_path)
        self.project_repos[project_id] = project_repo
        
        # 创建智能体团队
        team_leader = TeamLeader()
        project_manager = ProjectManagerAgent()
        architect = ArchitectAgent()
        case_expert = CaseExpertAgent()
        data_analyst = DataAnalystAgent()
        writer_expert = WriterExpertAgent()
        
        # 为每个智能体设置项目仓库
        for agent in [team_leader, project_manager, architect, case_expert, data_analyst, writer_expert]:
            agent.project_repo = project_repo
        
        # 创建团队并雇佣成员 - 适配MetaGPT v2
        team = Team(
            investment=10.0,
            environment=environment
        )
        team.hire([team_leader, project_manager, architect, case_expert, data_analyst, writer_expert])
        
        self.teams[project_id] = team
        logger.info(f"项目团队设置完成，共{len(team.env.roles)}个专家智能体")
        
        return team

    async def _route_message(self, team: Team, message: str, project_id: str) -> str:
        """
        路由消息到团队并执行
        """
        roles = list(team.env.roles.values())
        logger.info(f"🚀 开始处理用户消息: {message}")
        logger.info(f"📋 当前团队成员数量: {len(roles)}")
        
        try:
            # 直接发布用户消息到环境
            logger.info("📤 直接发布用户消息到环境")
            team.env.publish_message(Message(content=message, sent_from="Human"))
            
            # 检查所有角色对象状态
            logger.info("🔍 检查所有角色对象状态:")
            for member in roles:
                logger.info(f"   角色 {member.name}: type={type(member)}, is_none={member is None}")
                logger.info(f"     - name: {member.name}")
                logger.info(f"     - profile: {member.profile}")
            
            # 开始团队协作
            logger.info(f"🔄 开始团队协作: {project_id}")
            await self._run_team_with_frontend_updates(team, project_id)
            
            return "团队协作完成"
            
        except Exception as e:
            logger.error(f"❌ 消息路由失败: {e}")
            raise

    async def _run_team_with_frontend_updates(self, team: Team, project_id: str):
        """
        运行团队并向前端推送更新
        """
        try:
            # 启动团队任务
            team_task = asyncio.create_task(team.run())
            
            # 启动消息监控
            monitor_task = asyncio.create_task(self._monitor_team_messages(team))
            
            # 等待团队完成
            await team_task
            
            # 取消监控任务
            monitor_task.cancel()
            
        except Exception as e:
            logger.error(f"团队运行失败: {e}")
            raise

    async def _monitor_team_messages(self, team: 'Team'):
        """
        监控团队消息并向前端推送
        """
        last_sent_idx = -1  # 跟踪已发送消息的最新索引

        try:
            while True:
                # 检查环境中的消息
                if team.env.history and team.env.history.storage:
                    current_msg_count = len(team.env.history.storage)
                    if current_msg_count > last_sent_idx + 1:
                        # 有新消息产生
                        new_messages = team.env.history.storage[last_sent_idx + 1:]
                        for msg in new_messages:
                            # 排除用户自己的初始消息，只看智能体的回复
                            if msg.role != "User":
                                await self._send_to_frontend(message=msg.content, author=msg.sent_from)
                        last_sent_idx = current_msg_count - 1

                await asyncio.sleep(1)  # 每秒检查一次

        except asyncio.CancelledError:
            logger.info("消息监控任务已取消")
        except Exception as e:
            logger.error(f"消息监控失败: {e}")

    async def _send_to_frontend(self, message: str, author: str):
        """
        向前端发送消息
        """
        logger.info(f"📤 推送消息到前端 from {author}: {message[:100]}...")
        await cl.Message(content=message, author=author).send()