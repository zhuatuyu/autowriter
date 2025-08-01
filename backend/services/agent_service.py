import asyncio
from typing import Optional
from pathlib import Path

from metagpt.environment import Environment
from metagpt.context import Context
from metagpt.team import Team
from metagpt.schema import Message
from metagpt.logs import logger
from metagpt.roles.di.team_leader import TeamLeader
from metagpt.actions.add_requirement import UserRequirement

from backend.roles.project_manager import ProjectManagerAgent
from backend.roles.writer_expert import WriterExpertAgent
from backend.roles.data_analyst import DataAnalystAgent
from backend.roles.case_expert import CaseExpertAgent
from backend.utils.project_repo import ProjectRepo

# 导入chainlit用于前端通信
import chainlit as cl


class AgentService:
    """智能体服务 - 采用与company.py相同的成功模式，并集成Chainlit前端通信"""
    
    def __init__(self):
        self.active_teams = {}
    
    async def process_message(self, project_id: str, message: str, environment: Environment) -> str:
        """处理用户消息"""
        try:
            # 获取或创建项目团队
            team = await self._get_or_create_team(project_id, environment)
            
            # 根据消息内容选择合适的角色处理
            response = await self._route_message(team, message, project_id)
            
            return response
            
        except Exception as e:
            return f"处理消息时出错: {str(e)}"
    
    async def _get_or_create_team(self, project_id: str, environment: Environment) -> Team:
        """获取或创建项目团队 - 采用与company.py相同的成功模式"""
        if project_id not in self.active_teams:
            # 创建MetaGPT Context（与company.py保持一致）
            context = Context()
            
            # 设置工作区路径
            project_repo = ProjectRepo(project_id)
            context.kwargs.set("project_path", str(project_repo.root))
            context.kwargs.set("project_name", f"project_{project_id}")
            
            # 创建Team（使用context，与company.py保持一致）
            team = Team(context=context)
            
            # 添加团队领导者（MetaGPT MGX环境需要，与company.py保持一致）
            team_leader = TeamLeader(name="王昭元")
            
            # 创建ProjectManager
            project_manager = ProjectManagerAgent()
            
            # 创建专业Agent团队，并设置project_repo（与company.py保持一致）
            case_expert = CaseExpertAgent()
            case_expert.project_repo = project_repo
            
            writer_expert = WriterExpertAgent()
            writer_expert.project_repo = project_repo
            
            data_analyst = DataAnalystAgent()
            data_analyst.project_repo = project_repo
            
            # 雇佣所有Agent（首先添加团队领导者，与company.py保持一致）
            agents = [team_leader, project_manager, case_expert, writer_expert, data_analyst]
            team.hire(agents)
            
            # 设置投资预算（与company.py保持一致）
            team.invest(investment=10.0)
            
            self.active_teams[project_id] = team
            logger.info(f"项目团队设置完成，共{len(agents)}个专家智能体（包含团队领导者）")
        
        return self.active_teams[project_id]
    
    async def _route_message(self, team: Team, message: str, project_id: str) -> str:
        """路由消息到合适的智能体 - 采用与company.py相同的成功模式，并集成Chainlit前端通信"""
        try:
            logger.info(f"🚀 开始处理用户消息: {message}")
            logger.info(f"📋 当前团队成员数量: {len(team.env.roles)}")
            
            # 向前端发送开始协作的消息
            await self._send_to_frontend("🤖 **项目经理**: 正在分析需求和制定计划...")
            
            # 发布用户需求到环境（与company.py保持一致）
            user_msg = Message(
                role="user",
                content=message,
                sent_from="user",
                send_to={"all"}
            )
            
            # 直接使用_publish_message方法，绕过团队领导者检查（与company.py保持一致）
            logger.info("📤 直接发布用户消息到环境")
            team.env._publish_message(user_msg)
            
            # 调试：检查所有角色对象的状态（与company.py保持一致）
            logger.info("🔍 检查所有角色对象状态:")
            for role_name, role in team.env.roles.items():
                logger.info(f"  角色 {role_name}: type={type(role)}, is_none={role is None}")
                if role is not None:
                    logger.info(f"    - name: {getattr(role, 'name', 'NO_NAME')}")
                    logger.info(f"    - profile: {getattr(role, 'profile', 'NO_PROFILE')}")
                else:
                    logger.error(f"    ❌ 角色 {role_name} 为 None!")
            
            # 运行团队协作（与company.py保持一致）
            logger.info(f"🔄 开始团队协作: {project_id}")
            await self._send_to_frontend("🔄 **多智能体团队**: 开始协作...")
            
            # 监听团队协作过程中的消息
            await self._run_team_with_frontend_updates(team, project_id)
            
            logger.info(f"✅ 团队协作完成: {project_id}")
            
            # 检查工作空间中的输出文件
            project_repo = ProjectRepo(project_id)
            reports_dir = project_repo.reports
            if reports_dir.exists():
                report_files = list(reports_dir.glob("*.md"))
                if report_files:
                    # 返回最新的报告文件内容
                    latest_report = max(report_files, key=lambda f: f.stat().st_mtime)
                    logger.info(f"📄 找到最新报告: {latest_report.name}")
                    
                    # 向前端发送完成消息
                    await self._send_to_frontend(f"✅ **报告生成完成**: {latest_report.name}")
                    
                    return f"✅ 多智能体协作完成！已生成报告：{latest_report.name}\n\n报告已保存到工作空间：{reports_dir}"
            
            # 如果没有找到输出文件，返回协作完成消息
            logger.info(f"🎉 项目协作完成！所有任务已完成。")
            await self._send_to_frontend("🎉 **协作完成**: 所有智能体已完成各自的任务")
            return "🎉 多智能体协作完成！所有智能体已完成各自的任务，请查看工作区中的输出结果。"
                
        except Exception as e:
            logger.error(f"❌ 消息路由失败: {e}")
            import traceback
            traceback.print_exc()
            await self._send_to_frontend(f"❌ **错误**: {str(e)}")
            return f"处理消息时出现错误: {str(e)}"
    
    async def _run_team_with_frontend_updates(self, team: Team, project_id: str):
        """运行团队协作并向前端发送更新"""
        # 创建一个任务来运行团队协作
        team_task = asyncio.create_task(team.run(n_round=10))
        
        # 创建一个任务来监听和转发消息
        monitor_task = asyncio.create_task(self._monitor_team_messages(team, project_id))
        
        # 等待团队协作完成
        await team_task
        
        # 取消监听任务
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    
    async def _monitor_team_messages(self, team: Team, project_id: str):
        """监听团队消息并转发到前端"""
        try:
            processed_messages = set()  # 记录已处理的消息，避免重复推送
            
            while True:
                # 检查环境中的新消息
                try:
                    # 尝试多种方式获取消息
                    messages_to_check = []
                    
                    # 方式1: 检查环境历史记录 (team.env.history 是一个 Memory 对象)
                    if hasattr(team.env, 'history') and team.env.history:
                        try:
                            # Memory对象有storage属性存储消息列表
                            if hasattr(team.env.history, 'storage'):
                                messages_to_check.extend(team.env.history.storage[-10:])  # 获取最近10条消息
                            # 或者使用get方法
                            elif hasattr(team.env.history, 'get'):
                                messages_to_check.extend(team.env.history.get(10))
                        except Exception as e:
                            logger.warning(f"访问team.env.history时出错: {e}")
                    
                    # 方式2: 安全地检查各个角色的输出
                    for role_name, role in team.env.roles.items():
                        try:
                            if hasattr(role, 'rc') and hasattr(role.rc, 'memory'):
                                role_memory = role.rc.memory
                                # 角色内存也是Memory对象，使用get方法获取消息
                                if hasattr(role_memory, 'get') and callable(getattr(role_memory, 'get')):
                                    role_messages = role_memory.get(3)  # 获取最近3条消息
                                    if role_messages:
                                        messages_to_check.extend(role_messages)
                                elif hasattr(role_memory, 'storage'):
                                    messages_to_check.extend(role_memory.storage[-3:])
                        except Exception:
                            pass
                    
                    # 处理收集到的消息
                    for msg in messages_to_check:
                        try:
                            if msg and hasattr(msg, 'content') and msg.content:
                                # 生成消息唯一标识符
                                content_str = str(msg.content)
                                msg_id = f"{getattr(msg, 'role', 'unknown')}_{hash(content_str[:100])}"
                                
                                if msg_id not in processed_messages:
                                    processed_messages.add(msg_id)
                                    
                                    # 根据消息来源和内容进行分类推送
                                    role = getattr(msg, 'role', '')
                                    sent_from = getattr(msg, 'sent_from', '')
                                    
                                    # 识别ProjectManager的消息
                                    if (role == "ProjectManager" or 
                                        sent_from == "ProjectManager" or 
                                        "项目经理" in content_str or 
                                        "任务分配" in content_str or
                                        "计划" in content_str or
                                        any(keyword in content_str for keyword in ['任务分配', '分配给', 'assigned to', '请完成', '负责'])):
                                        formatted_content = f"📋 **项目经理任务分配**\n\n{content_str[:300]}..."
                                        await cl.Message(
                                            content=formatted_content,
                                            author="ProjectManager"
                                        ).send()
                                        logger.info(f"推送ProjectManager消息到前端: {content_str[:100]}...")
                                    
                                    # 识别案例专家的消息
                                    elif (role == "案例专家" or 
                                          sent_from == "王磊" or 
                                          "案例" in content_str or
                                          "搜索" in content_str):
                                        await self._send_to_frontend(f"🔍 **案例专家**: {content_str[:200]}...")
                                    
                                    # 识别写作专家的消息
                                    elif (role == "writer_expert" or 
                                          sent_from == "张翰" or 
                                          "写作" in content_str or
                                          "报告" in content_str):
                                        await self._send_to_frontend(f"📝 **写作专家**: {content_str[:200]}...")
                                    
                                    # 识别数据分析师的消息
                                    elif (role == "data_analyst" or 
                                          sent_from == "赵丽娅" or 
                                          "数据" in content_str or
                                          "分析" in content_str):
                                        await self._send_to_frontend(f"📊 **数据分析师**: {content_str[:200]}...")
                                    
                                    # 其他重要消息
                                    elif any(keyword in content_str for keyword in ["完成", "开始", "任务", "协作"]):
                                        await self._send_to_frontend(f"💬 **团队消息**: {content_str[:200]}...")
                        except Exception as msg_e:
                            logger.error(f"处理单个消息时出错: {msg_e}")
                            continue
                
                except Exception as inner_e:
                    logger.error(f"处理消息时出错: {inner_e}")
                
                # 等待一段时间再检查
                await asyncio.sleep(1.5)  # 缩短检查间隔，提高实时性
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"监听团队消息时出错: {e}")
            # 不再抛出异常，避免影响主流程
    
    async def _send_to_frontend(self, message: str):
        """发送消息到Chainlit前端"""
        try:
            # 使用Chainlit的系统消息发送到前端
            await cl.Message(
                content=message,
                author="System"
            ).send()
        except Exception as e:
            logger.error(f"发送消息到前端失败: {e}")
            # 如果Chainlit不可用，只记录日志
            logger.info(f"前端消息: {message}")