"""
智能管理器 - 整合SOP模式的清晰架构
提供统一的接口，支持多种工作模式
"""
import asyncio
import threading
from typing import Dict, Optional
from queue import Queue
from datetime import datetime
import os
from pathlib import Path

from backend.services.metagpt_sop_manager import SOPReportTeam, WorkflowPhase
from backend.services.iterative_sop_manager import IterativeReportTeam, iterative_teams, ReportPhase
from backend.services.intelligent_director import IntelligentProjectDirector, intelligent_directors
from backend.models.session import WorkflowPhase as SessionPhase
from metagpt.logs import logger

class IntelligentManager:
    """智能管理器 - 统一的多Agent协作管理"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict] = {}
        self.message_queues: Dict[str, Queue] = {}
        self.message_tasks: Dict[str, asyncio.Task] = {}
        self.sop_teams: Dict[str, SOPReportTeam] = {}
        
        # 配置MetaGPT
        self._configure_metagpt()
    
    def _configure_metagpt(self):
        """配置MetaGPT"""
        try:
            from metagpt.config2 import config
            
            if hasattr(config, 'llm') and config.llm:
                logger.info(f"✅ MetaGPT配置成功: {config.llm.model}")
                logger.info(f"   API类型: {config.llm.api_type}")
                logger.info(f"   API地址: {config.llm.base_url}")
            else:
                raise Exception("MetaGPT配置未正确加载")
                
        except Exception as e:
            logger.error(f"❌ MetaGPT配置失败: {e}")
            logger.error("请检查 MetaGPT/config/config2.yaml 配置文件")
            raise

    def _get_next_project_name(self) -> str:
        """获取下一个递增的项目名称，如 project_001, project_002"""
        workspace_dir = Path("workspaces")
        workspace_dir.mkdir(exist_ok=True)
        
        existing_projects = [d for d in os.listdir(workspace_dir) if d.startswith("project_") and os.path.isdir(workspace_dir / d)]
        
        if not existing_projects:
            return "project_001"
            
        max_num = 0
        for project in existing_projects:
            try:
                num = int(project.split('_')[1])
                if num > max_num:
                    max_num = num
            except (ValueError, IndexError):
                continue
        
        return f"project_{max_num + 1:03d}"

    async def start_intelligent_workflow(self, session_id: str, websocket_manager):
        """启动智能项目总监工作流程 - 真正的人机协同模式"""
        logger.info(f"🚀 启动智能项目总监工作流程: {session_id}")
        
        if session_id in self.active_sessions:
            logger.warning(f"会话 {session_id} 已存在")
            return
            
        # 生成一个可读的项目名称
        project_name = self._get_next_project_name()
        logger.info(f"为会话 {session_id} 分配项目名称: {project_name}")
        
        # 初始化会话
        self.active_sessions[session_id] = {
            "phase": "greeting",
            "websocket_manager": websocket_manager,
            "is_running": True,
            "workflow_started": True,
            "mode": "intelligent",
            "start_time": datetime.now(),
            "project_name": project_name
        }
        
        # 创建消息队列
        self.message_queues[session_id] = Queue()
        
        # 启动消息发送任务
        self.message_tasks[session_id] = asyncio.create_task(
            self._message_sender(session_id)
        )
        
        # 创建智能项目总监，并传入项目名称
        director = IntelligentProjectDirector(
            session_id=session_id,
            project_name=project_name,
            message_queue=self.message_queues[session_id]
        )
        intelligent_directors[session_id] = director
        
        # 在后台线程运行智能工作流程
        thread = threading.Thread(
            target=self._run_intelligent_workflow_in_thread,
            args=(session_id,)
        )
        thread.daemon = True
        thread.start()
    
    def _run_intelligent_workflow_in_thread(self, session_id: str):
        """在线程中运行智能工作流程"""
        try:
            logger.info("🧠 智能项目总监工作流程启动...")
            
            # 获取智能项目总监
            director = intelligent_directors[session_id]
            
            # 运行智能工作流程（需要在新的事件循环中）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(director._act())
                logger.info(f"智能项目总监启动: {result.content[:100]}...")
                
                # 智能项目总监是持续对话系统，不应该在首次响应后停止
                # 保持会话活跃，等待用户后续输入
                logger.info("🔄 智能项目总监进入等待用户输入状态...")
                
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"智能工作流程异常: {e}")
            import traceback
            traceback.print_exc()
            
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "智能系统",
                "content": f"❌ 智能工作流程执行出错: {str(e)}",
                "status": "error"
            })
            
            # 智能项目总监出错后也要保持会话活跃，等待用户重新输入
            logger.info("🔄 智能项目总监因错误暂停，等待用户重新输入...")
        finally:
            # 智能项目总监是持续对话的，不应该在首次响应后就停止
            # if session_id in self.active_sessions:
            #     self.active_sessions[session_id]["is_running"] = False
            logger.info("🔄 智能项目总监工作流程启动完成，等待用户输入...")

    async def start_iterative_workflow(self, session_id: str, websocket_manager):
        """启动迭代式工作流程 - 新的人机协同模式"""
        logger.info(f"🚀 启动迭代式工作流程: {session_id}")
        
        if session_id in self.active_sessions:
            logger.warning(f"会话 {session_id} 已存在")
            return
        
        # 初始化会话
        self.active_sessions[session_id] = {
            "phase": "initialization",
            "websocket_manager": websocket_manager,
            "is_running": True,
            "workflow_started": True,
            "mode": "iterative",
            "start_time": datetime.now()
        }
        
        # 创建消息队列
        self.message_queues[session_id] = Queue()
        
        # 启动消息发送任务
        self.message_tasks[session_id] = asyncio.create_task(
            self._message_sender(session_id)
        )
        
        # 创建迭代式团队
        iterative_team = IterativeReportTeam(session_id, self.message_queues[session_id])
        iterative_teams[session_id] = iterative_team
        
        # 在后台线程运行迭代式工作流程
        thread = threading.Thread(
            target=self._run_iterative_workflow_in_thread,
            args=(session_id,)
        )
        thread.daemon = True
        thread.start()
    
    def _run_iterative_workflow_in_thread(self, session_id: str):
        """在线程中运行迭代式工作流程"""
        try:
            logger.info("🎯 迭代式工作流程启动...")
            
            # 获取迭代式团队
            iterative_team = iterative_teams[session_id]
            
            # 运行迭代式工作流程（需要在新的事件循环中）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(iterative_team.start_conversation())
                logger.info(f"迭代式对话启动: {result[:100]}...")
                
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"迭代式工作流程异常: {e}")
            import traceback
            traceback.print_exc()
            
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "迭代系统",
                "content": f"❌ 迭代式工作流程执行出错: {str(e)}",
                "status": "error"
            })
        finally:
            # 迭代式工作流程也是持续对话的，不应在首次响应后停止
            # if session_id in self.active_sessions:
            #     self.active_sessions[session_id]["is_running"] = False
            logger.info("🔄 迭代式工作流程启动完成，等待用户输入...")

    async def start_sop_workflow(self, session_id: str, project_info: Dict, websocket_manager):
        """启动SOP工作流程"""
        logger.info(f"🚀 启动SOP工作流程: {session_id}")
        
        if session_id in self.active_sessions:
            logger.warning(f"会话 {session_id} 已存在")
            return
        
        # 初始化会话
        self.active_sessions[session_id] = {
            "phase": SessionPhase.ANALYSIS,
            "project_info": project_info,
            "websocket_manager": websocket_manager,
            "is_running": True,
            "workflow_started": True,
            "mode": "sop",
            "start_time": datetime.now()
        }
        
        # 创建消息队列
        self.message_queues[session_id] = Queue()
        
        # 启动消息发送任务
        self.message_tasks[session_id] = asyncio.create_task(
            self._message_sender(session_id)
        )
        
        # 创建SOP团队
        sop_team = SOPReportTeam(
            session_id=session_id,
            project_info=project_info,
            message_queue=self.message_queues[session_id]
        )
        self.sop_teams[session_id] = sop_team
        
        # 在后台线程运行SOP工作流程
        thread = threading.Thread(
            target=self._run_sop_workflow_in_thread,
            args=(session_id, project_info)
        )
        thread.daemon = True
        thread.start()
    
    def _run_sop_workflow_in_thread(self, session_id: str, project_info: Dict):
        """在线程中运行SOP工作流程"""
        try:
            logger.info("🎯 SOP工作流程启动...")
            
            # 发送启动消息
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "SOP系统",
                "content": "🚀 基于SOP的智能协作系统正在启动...\n\n📋 系统特点：\n• 清晰的工作流程管理\n• 智能任务分配\n• 实时用户介入响应\n• 动态计划调整",
                "status": "running"
            })
            
            # 获取SOP团队
            sop_team = self.sop_teams[session_id]
            
            # 运行SOP工作流程（需要在新的事件循环中）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(sop_team.run_sop_workflow())
                logger.info(f"SOP工作流程完成: {result[:100]}...")
                
                # 发送最终报告
                self.message_queues[session_id].put({
                    "agent_type": "report",
                    "agent_name": "最终报告",
                    "content": result,
                    "is_report": True
                })
                
                # 保存报告
                self._save_report(session_id, result)
                
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"SOP工作流程异常: {e}")
            import traceback
            traceback.print_exc()
            
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "SOP系统",
                "content": f"❌ SOP工作流程执行出错: {str(e)}",
                "status": "error"
            })
        finally:
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["is_running"] = False
    
    async def _message_sender(self, session_id: str):
        """异步消息发送器"""
        websocket_manager = self.active_sessions[session_id]["websocket_manager"]
        queue = self.message_queues[session_id]
        
        while self.active_sessions.get(session_id, {}).get("is_running", False):
            try:
                if not queue.empty():
                    msg = queue.get_nowait()
                    
                    if msg.get("is_report"):
                        # 发送报告更新
                        await websocket_manager.broadcast_report_update(
                            session_id=session_id,
                            chapter="full_report",
                            content=msg["content"],
                            version=1
                        )
                        logger.info("📄 报告已发送")
                    else:
                        # 发送Agent消息
                        await websocket_manager.broadcast_agent_message(
                            session_id=session_id,
                            agent_type=msg["agent_type"],
                            agent_name=msg["agent_name"],
                            content=msg["content"],
                            status=msg.get("status", "completed")
                        )
                        logger.info(f"📨 消息已发送: {msg['agent_name']}")
                    
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"消息发送异常: {e}")
                await asyncio.sleep(1)
        
        # 发送完成状态
        await websocket_manager.broadcast_workflow_status(session_id, "completed", 100)
        logger.info(f"消息发送器停止: {session_id}")
    
    def _save_report(self, session_id: str, content: str):
        """保存报告"""
        try:
            from pathlib import Path
            
            workspace_path = Path(f"workspaces/{session_id}")
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            report_file = workspace_path / "sop_report.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"📄 SOP报告已保存: {report_file}")
        except Exception as e:
            logger.error(f"❌ 保存报告失败: {e}")
    
    async def handle_user_intervention(self, session_id: str, message: str):
        """处理用户介入"""
        session = self.active_sessions.get(session_id)
        if not session:
            logger.warning(f"会话 {session_id} 不存在")
            return
        
        mode = session.get("mode", "sop")
        
        if mode == "intelligent" and session_id in intelligent_directors:
            # 智能项目总监模式 - 处理用户输入
            director = intelligent_directors[session_id]
            
            # 检查是否有文件上传（这里需要后端API支持）
            uploaded_files = []  # TODO: 从请求中提取上传的文件
            
            director.handle_user_input(message, uploaded_files)
            
            # 继续工作流程
            thread = threading.Thread(
                target=self._continue_intelligent_workflow,
                args=(session_id,)
            )
            thread.daemon = True
            thread.start()
            
            logger.info(f"🗣️ 智能项目总监用户输入已处理: {message[:50]}...")
            
        elif mode == "iterative" and session_id in iterative_teams:
            # 迭代模式 - 处理用户输入
            iterative_team = iterative_teams[session_id]
            iterative_team.handle_user_input(message)
            
            # 继续工作流程
            thread = threading.Thread(
                target=self._continue_iterative_workflow,
                args=(session_id,)
            )
            thread.daemon = True
            thread.start()
            
            logger.info(f"🗣️ 迭代模式用户输入已处理: {message[:50]}...")
            
        elif mode == "sop" and session_id in self.sop_teams:
            # SOP模式 - 处理用户介入
            sop_team = self.sop_teams[session_id]
            sop_team.handle_user_intervention(message)
            
            # 发送确认消息
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "SOP系统",
                "content": f"📢 已收到您的指示：「{message}」\n\n🔄 项目总监正在根据您的要求调整工作计划...",
                "status": "info"
            })
            
            logger.info(f"🗣️ SOP模式用户介入已处理: {message[:50]}...")
    
    def _continue_intelligent_workflow(self, session_id: str):
        """继续智能项目总监工作流程"""
        try:
            director = intelligent_directors[session_id]
            
            # 运行在新的事件循环中
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(director._act())
                logger.info(f"智能项目总监工作流程继续: {result.content[:100]}...")
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"继续智能工作流程失败: {e}")
            
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "智能系统",
                "content": f"❌ 智能工作流程继续失败: {str(e)}",
                "status": "error"
            })
    
    def _continue_iterative_workflow(self, session_id: str):
        """继续迭代式工作流程"""
        try:
            iterative_team = iterative_teams[session_id]
            
            # 运行在新的事件循环中
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(iterative_team.continue_workflow())
                logger.info(f"迭代式工作流程继续: {result[:100]}...")
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"继续迭代式工作流程失败: {e}")
            
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "迭代系统",
                "content": f"❌ 工作流程继续失败: {str(e)}",
                "status": "error"
            })
    
    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """获取会话状态"""
        session = self.active_sessions.get(session_id)
        if session and session_id in self.sop_teams:
            sop_team = self.sop_teams[session_id]
            
            # 添加SOP状态信息
            session["sop_status"] = {
                "current_phase": sop_team.sop_state.current_phase.value,
                "total_tasks": len(sop_team.sop_state.tasks),
                "completed_tasks": len([
                    t for t in sop_team.sop_state.tasks.values() 
                    if t.status.value == "completed"
                ]),
                "user_interventions": len(sop_team.sop_state.user_interventions)
            }
        
        return session
    
    async def pause_workflow(self, session_id: str):
        """暂停工作流"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["is_running"] = False
            
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "SOP系统",
                "content": "⏸️ 工作流程已暂停",
                "status": "paused"
            })
    
    async def resume_workflow(self, session_id: str):
        """恢复工作流"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["is_running"] = True
            
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "SOP系统",
                "content": "▶️ 工作流程已恢复",
                "status": "running"
            })
    
    def get_workflow_summary(self, session_id: str) -> Dict:
        """获取工作流程摘要"""
        if session_id not in self.sop_teams:
            return {"error": "会话不存在"}
        
        sop_team = self.sop_teams[session_id]
        sop_state = sop_team.sop_state
        
        return {
            "session_id": session_id,
            "current_phase": sop_state.current_phase.value,
            "total_tasks": len(sop_state.tasks),
            "completed_tasks": len([
                t for t in sop_state.tasks.values() 
                if t.status.value == "completed"
            ]),
            "pending_tasks": len([
                t for t in sop_state.tasks.values() 
                if t.status.value == "pending"
            ]),
            "user_interventions": len(sop_state.user_interventions),
            "workflow_history": len(sop_state.workflow_history),
            "start_time": self.active_sessions.get(session_id, {}).get("start_time"),
            "is_running": self.active_sessions.get(session_id, {}).get("is_running", False)
        }

# 全局智能管理器实例
intelligent_manager = IntelligentManager()