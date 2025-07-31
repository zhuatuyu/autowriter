"""
启动管理器 - 基于MetaGPT架构
管理多个AI公司实例，类似MetaGPT的启动管理概念
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from metagpt.logs import logger

from backend.services.company import AICompany
from backend.services.websocket_manager import WebSocketManager


class StartupManager:
    """
    启动管理器 - 基于MetaGPT架构
    负责管理多个AI公司实例，每个公司独立运行
    """
    
    def __init__(self):
        # AI公司字典: session_id -> AICompany
        self.companies: Dict[str, AICompany] = {}
        
        # 工作区基础路径
        self.workspace_base = Path("workspaces")
        self.workspace_base.mkdir(exist_ok=True)
        
        logger.info("启动管理器初始化完成")
    
    async def create_company(self, session_id: str, project_info: Dict = None) -> bool:
        """
        创建新AI公司
        
        Args:
            session_id: 会话ID
            project_info: 项目信息
        
        Returns:
            bool: 创建是否成功
        """
        try:
            if session_id in self.companies:
                logger.warning(f"AI公司 {session_id} 已存在")
                return True
            
            # 创建AI公司管理器
            company = AICompany(session_id, project_info)
            self.companies[session_id] = company
            
            logger.info(f"AI公司 {session_id} 创建成功")
            return True
            
        except Exception as e:
            logger.error(f"创建AI公司失败: {e}")
            return False
    
    async def start_company(self, session_id: str, user_requirement: str, websocket_manager: WebSocketManager = None) -> bool:
        """
        启动AI公司
        
        Args:
            session_id: 会话ID
            user_requirement: 用户需求
            websocket_manager: WebSocket管理器
        
        Returns:
            bool: 启动是否成功
        """
        try:
            # 如果公司不存在，先创建
            if session_id not in self.companies:
                await self.create_company(session_id)
            
            company = self.companies[session_id]
            
            # 启动公司
            success = await company.start_project(user_requirement, websocket_manager)
            
            if success:
                logger.info(f"AI公司 {session_id} 启动成功")
            else:
                logger.error(f"AI公司 {session_id} 启动失败")
            
            return success
            
        except Exception as e:
            logger.error(f"启动AI公司失败: {e}")
            return False
    
    async def handle_user_message(self, session_id: str, user_message: str, websocket_manager: WebSocketManager = None) -> bool:
        """
        处理用户消息
        
        Args:
            session_id: 会话ID
            user_message: 用户消息
            websocket_manager: WebSocket管理器
        
        Returns:
            bool: 处理是否成功
        """
        try:
            # 如果公司不存在，创建并启动
            if session_id not in self.companies:
                return await self.start_company(session_id, user_message, websocket_manager)
            
            # 转发消息给AI公司管理器
            company = self.companies[session_id]
            return await company.handle_user_message(user_message, websocket_manager)
            
        except Exception as e:
            logger.error(f"处理用户消息失败: {e}")
            return False
    
    def get_company_status(self, session_id: str) -> Dict[str, Any]:
        """获取AI公司状态"""
        if session_id not in self.companies:
            return {"error": "AI公司不存在"}
        
        return self.companies[session_id].get_project_status()
    
    def get_all_companies(self) -> List[Dict[str, Any]]:
        """获取所有AI公司状态"""
        companies = []
        for session_id, company in self.companies.items():
            status = company.get_project_status()
            companies.append(status)
        return companies
    
    def stop_company(self, session_id: str) -> bool:
        """停止AI公司"""
        if session_id not in self.companies:
            return False
        
        self.companies[session_id].stop_project()
        return True
    
    def remove_company(self, session_id: str) -> bool:
        """移除AI公司"""
        if session_id not in self.companies:
            return False
        
        # 先停止公司
        self.stop_company(session_id)
        
        # 移除AI公司管理器
        del self.companies[session_id]
        
        logger.info(f"AI公司 {session_id} 已移除")
        return True
    
    def get_company_outputs(self, session_id: str) -> List[Dict]:
        """获取AI公司输出"""
        if session_id not in self.companies:
            return []
        
        return self.companies[session_id].get_project_outputs()
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """获取会话状态 - 兼容旧接口"""
        if session_id not in self.companies:
            return {"error": "会话不存在"}
        
        status = self.get_company_status(session_id)
        
        # 转换为旧格式以保持兼容性
        return {
            "session_id": session_id,
            "status": "running" if status.get("is_running") else "idle",
            "agents": [
                {
                    "name": "ProjectManager",
                    "status": "active" if status.get("is_running") else "idle",
                    "current_task": "项目管理"
                },
                {
                    "name": "CaseExpert", 
                    "status": "active" if status.get("is_running") else "idle",
                    "current_task": "案例分析"
                },
                {
                    "name": "WriterExpert",
                    "status": "active" if status.get("is_running") else "idle", 
                    "current_task": "内容撰写"
                },
                {
                    "name": "DataAnalyst",
                    "status": "active" if status.get("is_running") else "idle",
                    "current_task": "数据分析"
                }
            ]
        }
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """获取所有会话 - 兼容旧接口"""
        sessions = []
        for session_id, company in self.companies.items():
            status = company.get_project_status()
            sessions.append({
                "session_id": session_id,
                "status": "running" if status.get("is_running") else "idle",
                "created_at": datetime.now().isoformat(),  # 简化处理
                "project_path": status.get("project_path", ""),
                "current_idea": status.get("current_idea", "")
            })
        return sessions


# 创建全局实例
startup_manager = StartupManager()