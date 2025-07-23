"""
统一记忆适配器 - 让现有Agent无缝使用统一记忆存储
"""
from typing import Dict, List, Any, Optional
from metagpt.logs import logger
from metagpt.schema import Message
from .unified_memory_storage import UnifiedMemoryStorage


class UnifiedMemoryAdapter:
    """
    统一记忆适配器
    为现有的Agent提供兼容的记忆接口，底层使用统一存储
    """
    
    def __init__(self, agent_id: str, unified_storage: UnifiedMemoryStorage):
        self.agent_id = agent_id
        self.storage = unified_storage
        self.agent_info = None
    
    def register_agent(self, agent_info: Dict[str, Any]):
        """注册Agent信息"""
        self.agent_info = agent_info
        self.storage.register_agent(self.agent_id, agent_info)
    
    def add_message(self, message: Message):
        """添加消息 - 兼容MetaGPT Message格式"""
        try:
            message_dict = {
                "id": getattr(message, 'id', f"msg_{self.agent_id}_{len(self.get_memory())}"),
                "content": message.content,
                "role": f"{self.agent_id}({self.agent_info.get('name', self.agent_id) if self.agent_info else self.agent_id})",
                "cause_by": getattr(message, 'cause_by', 'unknown'),
                "sent_from": self.agent_id,
                "send_to": getattr(message, 'send_to', ["<all>"]),
                "instruct_content": getattr(message, 'instruct_content', None)
            }
            self.storage.add_message(message_dict)
        except Exception as e:
            logger.error(f"❌ Agent {self.agent_id} 添加消息失败: {e}")
    
    def add_simple_message(self, content: str, role: str = None, cause_by: str = None):
        """添加简单消息"""
        try:
            message_dict = {
                "content": content,
                "role": role or f"{self.agent_id}({self.agent_info.get('name', self.agent_id) if self.agent_info else self.agent_id})",
                "cause_by": cause_by or f"{self.agent_id}_action",
                "sent_from": self.agent_id,
                "send_to": ["<all>"]
            }
            self.storage.add_message(message_dict)
        except Exception as e:
            logger.error(f"❌ Agent {self.agent_id} 添加简单消息失败: {e}")
    
    def get_memory(self) -> List[Dict[str, Any]]:
        """获取Agent记忆"""
        return self.storage.get_agent_memory(self.agent_id)
    
    def get_recent_memory(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的记忆"""
        memory = self.get_memory()
        return memory[-limit:] if limit > 0 else memory
    
    def get_shared_context(self) -> Dict[str, Any]:
        """获取共享上下文"""
        return self.storage.get_shared_context()
    
    def update_shared_context(self, key: str, value: Any):
        """更新共享上下文"""
        context_key = f"{self.agent_id}_{key}"
        self.storage.update_shared_context(context_key, value)
    
    def get_conversation_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self.storage.get_conversation_history(limit)
    
    def update_state(self, state_data: Dict[str, Any]):
        """更新Agent状态"""
        self.storage.update_agent_state(self.agent_id, state_data)
    
    def get_state(self) -> Optional[Dict[str, Any]]:
        """获取Agent状态"""
        return self.storage.get_agent_state(self.agent_id)
    
    def clear_memory(self):
        """清除Agent记忆"""
        self.storage.clear_memory(self.agent_id)
    
    def get_other_agents(self) -> Dict[str, Dict[str, Any]]:
        """获取其他Agent信息"""
        all_agents = self.storage.get_all_agents()
        return {k: v for k, v in all_agents.items() if k != self.agent_id}
    
    def send_message_to_agent(self, target_agent_id: str, content: str, cause_by: str = None):
        """发送消息给特定Agent"""
        try:
            message_dict = {
                "content": content,
                "role": f"{self.agent_id}({self.agent_info.get('name', self.agent_id) if self.agent_info else self.agent_id})",
                "cause_by": cause_by or f"{self.agent_id}_to_{target_agent_id}",
                "sent_from": self.agent_id,
                "send_to": [target_agent_id]
            }
            self.storage.add_message(message_dict)
        except Exception as e:
            logger.error(f"❌ Agent {self.agent_id} 发送消息给 {target_agent_id} 失败: {e}")
    
    def get_messages_from_agent(self, source_agent_id: str) -> List[Dict[str, Any]]:
        """获取来自特定Agent的消息"""
        try:
            all_messages = self.get_memory()
            return [msg for msg in all_messages if msg.get("sent_from") == source_agent_id]
        except Exception as e:
            logger.error(f"❌ Agent {self.agent_id} 获取来自 {source_agent_id} 的消息失败: {e}")
            return []
    
    def get_team_summary(self) -> Dict[str, Any]:
        """获取团队摘要"""
        try:
            all_agents = self.storage.get_all_agents()
            project_info = self.storage.get_project_info()
            stats = self.storage.get_statistics()
            
            return {
                "project_info": project_info,
                "team_members": {
                    agent_id: {
                        "name": agent_data.get("name", agent_id),
                        "profile": agent_data.get("profile", "Agent"),
                        "last_activity": agent_data.get("last_updated", ""),
                        "message_count": len(agent_data.get("rc", {}).get("memory", {}).get("storage", []))
                    }
                    for agent_id, agent_data in all_agents.items()
                },
                "statistics": stats
            }
        except Exception as e:
            logger.error(f"❌ Agent {self.agent_id} 获取团队摘要失败: {e}")
            return {}


class UnifiedMemoryManager:
    """
    统一记忆管理器
    管理整个项目的记忆存储和Agent适配器
    """
    
    def __init__(self, workspace_path: str):
        self.storage = UnifiedMemoryStorage(workspace_path)
        self.adapters: Dict[str, UnifiedMemoryAdapter] = {}
    
    def get_adapter(self, agent_id: str) -> UnifiedMemoryAdapter:
        """获取或创建Agent适配器"""
        if agent_id not in self.adapters:
            self.adapters[agent_id] = UnifiedMemoryAdapter(agent_id, self.storage)
        return self.adapters[agent_id]
    
    def register_agent(self, agent_id: str, agent_info: Dict[str, Any]):
        """注册Agent"""
        adapter = self.get_adapter(agent_id)
        adapter.register_agent(agent_info)
    
    def set_project_info(self, idea: str, investment: float = 0.0, session_info: Dict[str, Any] = None):
        """设置项目信息"""
        self.storage.set_project_info(idea, investment, session_info)
    
    def get_project_summary(self) -> Dict[str, Any]:
        """获取项目摘要"""
        return {
            "project_info": self.storage.get_project_info(),
            "agents": self.storage.get_all_agents(),
            "statistics": self.storage.get_statistics(),
            "recent_messages": self.storage.get_conversation_history(10)
        }
    
    def clear_all_memory(self):
        """清除所有记忆"""
        self.storage.clear_memory()
    
    def export_project(self) -> Dict[str, Any]:
        """导出项目状态"""
        return self.storage.export_state()
    
    def import_project(self, state_data: Dict[str, Any]):
        """导入项目状态"""
        self.storage.import_state(state_data)
        # 重新创建适配器
        self.adapters.clear()
        for agent_id in state_data.get("env", {}).get("roles", {}):
            self.get_adapter(agent_id)