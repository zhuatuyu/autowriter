"""
项目持久化和断点恢复服务
基于MetaGPT的序列化机制实现断点恢复功能
"""
import json
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ProjectPersistence:
    """项目持久化管理器"""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.storage_dir = self.workspace_root / "storage"
        self.storage_dir.mkdir(exist_ok=True)
        
    def save_project_state(self, session_id: str, project_state: Dict[str, Any]) -> bool:
        """
        保存项目状态到磁盘
        
        Args:
            session_id: 会话ID
            project_state: 项目状态数据
            
        Returns:
            bool: 保存是否成功
        """
        try:
            session_dir = self.storage_dir / session_id
            session_dir.mkdir(exist_ok=True)
            
            # 保存基本状态信息
            state_file = session_dir / "project_state.json"
            
            # 过滤掉不可序列化的对象
            serializable_state = self._make_serializable(project_state)
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 项目状态已保存: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存项目状态失败 {session_id}: {e}")
            return False
    
    def load_project_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        从磁盘加载项目状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Dict[str, Any]]: 项目状态数据，如果不存在则返回None
        """
        try:
            session_dir = self.storage_dir / session_id
            state_file = session_dir / "project_state.json"
            
            if not state_file.exists():
                logger.info(f"📂 项目状态文件不存在: {session_id}")
                return None
            
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            logger.info(f"✅ 项目状态已加载: {session_id}")
            return state
            
        except Exception as e:
            logger.error(f"❌ 加载项目状态失败 {session_id}: {e}")
            return None
    
    def list_recoverable_projects(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有可恢复的项目
        
        Returns:
            Dict[str, Dict[str, Any]]: 项目列表，key为session_id
        """
        projects = {}
        
        try:
            for session_dir in self.storage_dir.iterdir():
                if session_dir.is_dir():
                    state_file = session_dir / "project_state.json"
                    if state_file.exists():
                        try:
                            with open(state_file, 'r', encoding='utf-8') as f:
                                state = json.load(f)
                            
                            projects[session_dir.name] = {
                                "session_id": session_dir.name,
                                "saved_at": state.get("saved_at"),
                                "current_idea": state.get("current_idea", ""),
                                "is_running": state.get("is_running", False),
                                "progress": state.get("progress", {}),
                                "file_path": str(state_file)
                            }
                        except Exception as e:
                            logger.warning(f"⚠️ 跳过损坏的项目状态文件: {state_file}, 错误: {e}")
                            
        except Exception as e:
            logger.error(f"❌ 列出可恢复项目失败: {e}")
        
        return projects
    
    def delete_project_state(self, session_id: str) -> bool:
        """
        删除项目状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            session_dir = self.storage_dir / session_id
            if session_dir.exists():
                import shutil
                shutil.rmtree(session_dir)
                logger.info(f"✅ 项目状态已删除: {session_id}")
                return True
            else:
                logger.warning(f"⚠️ 项目状态不存在: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 删除项目状态失败 {session_id}: {e}")
            return False
    
    def _make_serializable(self, obj: Any) -> Any:
        """
        将对象转换为可序列化的格式
        
        Args:
            obj: 要序列化的对象
            
        Returns:
            Any: 可序列化的对象
        """
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                # 跳过不可序列化的对象
                if self._is_serializable(value):
                    result[key] = self._make_serializable(value)
                else:
                    # 对于不可序列化的对象，保存其类型信息
                    result[key] = {
                        "__type__": str(type(value)),
                        "__repr__": str(value)[:200] + "..." if len(str(value)) > 200 else str(value)
                    }
            return result
            
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj if self._is_serializable(item)]
            
        elif self._is_serializable(obj):
            return obj
        else:
            # 不可序列化的对象
            return {
                "__type__": str(type(obj)),
                "__repr__": str(obj)[:200] + "..." if len(str(obj)) > 200 else str(obj)
            }
    
    def _is_serializable(self, obj: Any) -> bool:
        """
        检查对象是否可以JSON序列化
        
        Args:
            obj: 要检查的对象
            
        Returns:
            bool: 是否可序列化
        """
        try:
            json.dumps(obj)
            return True
        except (TypeError, ValueError):
            return False

class BreakpointRecovery:
    """断点恢复管理器"""
    
    def __init__(self, persistence: ProjectPersistence):
        self.persistence = persistence
    
    def create_checkpoint(self, session_id: str, company_instance) -> bool:
        """
        创建检查点
        
        Args:
            session_id: 会话ID
            company_instance: Company实例
            
        Returns:
            bool: 创建是否成功
        """
        try:
            # 收集项目状态
            project_state = {
                "session_id": session_id,
                "saved_at": datetime.now().isoformat(),
                "current_idea": getattr(company_instance, 'current_idea', ''),
                "is_running": getattr(company_instance, 'is_running', False),
                "project_path": str(getattr(company_instance.project_repo, 'root', '')),
                "progress": self._extract_progress(company_instance),
                "agents_state": self._extract_agents_state(company_instance),
                "environment_state": self._extract_environment_state(company_instance)
            }
            
            return self.persistence.save_project_state(session_id, project_state)
            
        except Exception as e:
            logger.error(f"❌ 创建检查点失败 {session_id}: {e}")
            return False
    
    def recover_from_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        从检查点恢复
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Dict[str, Any]]: 恢复的状态数据
        """
        return self.persistence.load_project_state(session_id)
    
    def _extract_progress(self, company_instance) -> Dict[str, Any]:
        """提取项目进度信息"""
        try:
            progress = {}
            
            if hasattr(company_instance, 'team') and company_instance.team:
                # 提取团队成本信息
                if hasattr(company_instance.team, 'cost_manager'):
                    progress['total_cost'] = company_instance.team.cost_manager.total_cost
                    progress['max_budget'] = company_instance.team.cost_manager.max_budget
                
                # 提取环境信息
                if hasattr(company_instance.team, 'env') and company_instance.team.env:
                    progress['agents_count'] = len(company_instance.team.env.roles)
                    progress['message_count'] = len(company_instance.team.env.memory.storage) if hasattr(company_instance.team.env, 'memory') else 0
            
            return progress
            
        except Exception as e:
            logger.warning(f"⚠️ 提取进度信息失败: {e}")
            return {}
    
    def _extract_agents_state(self, company_instance) -> Dict[str, Any]:
        """提取智能体状态信息"""
        try:
            agents_state = {}
            
            if hasattr(company_instance, 'team') and company_instance.team and hasattr(company_instance.team, 'env'):
                for role_name, role in company_instance.team.env.roles.items():
                    agents_state[role_name] = {
                        "name": getattr(role, 'name', ''),
                        "profile": str(getattr(role, 'profile', '')),
                        "goal": getattr(role, 'goal', ''),
                        "state": getattr(role.rc, 'state', 0) if hasattr(role, 'rc') else 0
                    }
            
            return agents_state
            
        except Exception as e:
            logger.warning(f"⚠️ 提取智能体状态失败: {e}")
            return {}
    
    async def can_recover(self, session_id: str) -> bool:
        """
        检查是否可以从断点恢复
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否可以恢复
        """
        state = self.persistence.load_project_state(session_id)
        return state is not None and state.get("status") != "completed"
    
    async def recover_project(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        恢复项目
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Dict[str, Any]]: 恢复的项目数据
        """
        return self.persistence.load_project_state(session_id)
    
    async def save_breakpoint(self, session_id: str, stage: str, data: Dict[str, Any]) -> bool:
        """
        保存断点数据
        
        Args:
            session_id: 会话ID
            stage: 阶段名称
            data: 断点数据
            
        Returns:
            bool: 保存是否成功
        """
        try:
            session_dir = self.persistence.storage_dir / session_id
            session_dir.mkdir(exist_ok=True)
            
            breakpoint_file = session_dir / f"breakpoint_{stage}.json"
            
            with open(breakpoint_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 断点已保存: {session_id} - {stage}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存断点失败 {session_id} - {stage}: {e}")
            return False