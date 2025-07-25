"""
统一记忆存储系统 - 基于MetaGPT官方推荐的序列化方案
所有Agent共享一个项目级别的状态文件
"""
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from metagpt.logs import logger


class UnifiedMemoryStorage:
    """
    统一记忆存储 - 项目级别的Agent状态管理
    基于MetaGPT官方序列化方案设计
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.state_file = self.workspace_path / "project_state.json"
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化项目状态结构
        self.project_state = {
            "env": {
                "desc": "AutoWriter Enhanced 虚拟办公室环境",
                "roles": {},
                "history": "",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            },
            "investment": 0.0,
            "idea": "",
            "session_info": {},
            "shared_memory": {
                "storage": [],  # 共享消息存储
                "index": {},    # 消息索引
                "context": {}   # 共享上下文
            }
        }
        
        # 加载现有状态
        self._load_state()
    
    def _load_state(self):
        """加载项目状态"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    loaded_state = json.load(f)
                    # 合并状态，保留新字段
                    self._merge_state(loaded_state)
                logger.info(f"📂 项目状态已从 {self.state_file} 加载")
            else:
                logger.info(f"🆕 创建新的项目状态文件: {self.state_file}")
                self._save_state()
        except Exception as e:
            logger.error(f"❌ 加载项目状态失败: {e}")
            # 使用默认状态
    
    def _merge_state(self, loaded_state: Dict[str, Any]):
        """合并加载的状态与默认状态"""
        def deep_merge(default: dict, loaded: dict) -> dict:
            for key, value in loaded.items():
                if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                    default[key] = deep_merge(default[key], value)
                else:
                    default[key] = value
            return default
        
        self.project_state = deep_merge(self.project_state, loaded_state)
        self.project_state["env"]["last_updated"] = datetime.now().isoformat()
    
    def _save_state(self):
        """保存项目状态"""
        try:
            self.project_state["env"]["last_updated"] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.project_state, f, ensure_ascii=False, indent=2)
            logger.debug(f"💾 项目状态已保存到 {self.state_file}")
        except Exception as e:
            logger.error(f"❌ 保存项目状态失败: {e}")
    
    def register_agent(self, agent_id: str, agent_info: Dict[str, Any]):
        """注册Agent到项目环境"""
        try:
            self.project_state["env"]["roles"][agent_id] = {
                "name": agent_info.get("name", agent_id),
                "profile": agent_info.get("profile", "Agent"),
                "goal": agent_info.get("goal", "协助完成任务"),
                "constraints": agent_info.get("constraints", "遵循专业标准"),
                "desc": agent_info.get("desc", ""),
                "is_human": False,
                "role_id": agent_id,
                "states": [],
                "actions": [],
                "rc": {
                    "memory": {
                        "storage": [],
                        "index": {}
                    },
                    "state": 0
                },
                "addresses": [agent_id],
                "recovered": True,
                "latest_observed_msg": None,
                "registered_at": datetime.now().isoformat()
            }
            self._save_state()
            logger.info(f"✅ Agent {agent_id} 已注册到项目环境")
        except Exception as e:
            logger.error(f"❌ 注册Agent {agent_id} 失败: {e}")
    
    def add_message(self, message: Dict[str, Any]):
        """添加消息到共享记忆"""
        try:
            # 生成消息ID
            message_id = message.get("id", f"msg_{datetime.now().timestamp()}")
            message["id"] = message_id
            message["timestamp"] = datetime.now().isoformat()
            
            # 添加到共享存储
            self.project_state["shared_memory"]["storage"].append(message)
            
            # 更新索引
            cause_by = message.get("cause_by", "unknown")
            if cause_by not in self.project_state["shared_memory"]["index"]:
                self.project_state["shared_memory"]["index"][cause_by] = []
            self.project_state["shared_memory"]["index"][cause_by].append(message)
            
            # 更新Agent的最新观察消息
            sent_from = message.get("sent_from", "")
            if sent_from in self.project_state["env"]["roles"]:
                self.project_state["env"]["roles"][sent_from]["latest_observed_msg"] = message
            
            # 更新历史记录
            role = message.get("role", "Unknown")
            content = message.get("content", "")
            self.project_state["env"]["history"] += f"\n{role}: {content}"
            
            self._save_state()
            logger.debug(f"📝 消息已添加到共享记忆: {message_id}")
            
        except Exception as e:
            logger.error(f"❌ 添加消息失败: {e}")
    
    def get_agent_memory(self, agent_id: str) -> List[Dict[str, Any]]:
        """获取Agent的记忆"""
        try:
            if agent_id in self.project_state["env"]["roles"]:
                agent_memory = self.project_state["env"]["roles"][agent_id]["rc"]["memory"]["storage"]
                # 同时返回共享记忆中相关的消息
                shared_messages = [
                    msg for msg in self.project_state["shared_memory"]["storage"]
                    if msg.get("sent_from") == agent_id or msg.get("send_to") == [agent_id] or msg.get("send_to") == ["<all>"]
                ]
                return agent_memory + shared_messages
            return []
        except Exception as e:
            logger.error(f"❌ 获取Agent {agent_id} 记忆失败: {e}")
            return []
    
    def get_shared_context(self) -> Dict[str, Any]:
        """获取共享上下文"""
        return self.project_state["shared_memory"]["context"]
    
    def update_shared_context(self, key: str, value: Any):
        """更新共享上下文"""
        try:
            self.project_state["shared_memory"]["context"][key] = value
            self._save_state()
            logger.debug(f"🔄 共享上下文已更新: {key}")
        except Exception as e:
            logger.error(f"❌ 更新共享上下文失败: {e}")
    
    def get_conversation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取对话历史"""
        try:
            messages = self.project_state["shared_memory"]["storage"]
            return messages[-limit:] if limit > 0 else messages
        except Exception as e:
            logger.error(f"❌ 获取对话历史失败: {e}")
            return []
    
    def update_agent_state(self, agent_id: str, state_data: Dict[str, Any]):
        """更新Agent状态"""
        try:
            if agent_id in self.project_state["env"]["roles"]:
                agent_role = self.project_state["env"]["roles"][agent_id]
                
                # 更新基本信息
                for key in ["name", "profile", "goal", "constraints", "desc"]:
                    if key in state_data:
                        agent_role[key] = state_data[key]
                
                # 更新状态
                if "state" in state_data:
                    agent_role["rc"]["state"] = state_data["state"]
                
                # 更新动作列表
                if "actions" in state_data:
                    agent_role["actions"] = state_data["actions"]
                
                # 更新状态列表
                if "states" in state_data:
                    agent_role["states"] = state_data["states"]
                
                agent_role["last_updated"] = datetime.now().isoformat()
                self._save_state()
                logger.debug(f"🔄 Agent {agent_id} 状态已更新")
            else:
                logger.warning(f"⚠️ Agent {agent_id} 未注册，无法更新状态")
        except Exception as e:
            logger.error(f"❌ 更新Agent {agent_id} 状态失败: {e}")
    
    def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取Agent状态"""
        try:
            return self.project_state["env"]["roles"].get(agent_id)
        except Exception as e:
            logger.error(f"❌ 获取Agent {agent_id} 状态失败: {e}")
            return None
    
    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """获取所有Agent状态"""
        return self.project_state["env"]["roles"]
    
    def set_project_info(self, idea: str, investment: float = 0.0, session_info: Dict[str, Any] = None):
        """设置项目信息"""
        try:
            self.project_state["idea"] = idea
            self.project_state["investment"] = investment
            if session_info:
                self.project_state["session_info"] = session_info
            self._save_state()
            logger.info(f"📋 项目信息已更新: {idea}")
        except Exception as e:
            logger.error(f"❌ 设置项目信息失败: {e}")
    
    def get_project_info(self) -> Dict[str, Any]:
        """获取项目信息"""
        return {
            "idea": self.project_state.get("idea", ""),
            "investment": self.project_state.get("investment", 0.0),
            "session_info": self.project_state.get("session_info", {}),
            "created_at": self.project_state["env"].get("created_at", ""),
            "last_updated": self.project_state["env"].get("last_updated", "")
        }
    
    def clear_memory(self, agent_id: str = None):
        """清除记忆"""
        try:
            if agent_id:
                # 清除特定Agent的记忆
                if agent_id in self.project_state["env"]["roles"]:
                    self.project_state["env"]["roles"][agent_id]["rc"]["memory"] = {
                        "storage": [],
                        "index": {}
                    }
                    self.project_state["env"]["roles"][agent_id]["latest_observed_msg"] = None
                    logger.info(f"🧹 Agent {agent_id} 记忆已清除")
            else:
                # 清除所有共享记忆
                self.project_state["shared_memory"] = {
                    "storage": [],
                    "index": {},
                    "context": {}
                }
                self.project_state["env"]["history"] = ""
                # 清除所有Agent记忆
                for role_id in self.project_state["env"]["roles"]:
                    self.project_state["env"]["roles"][role_id]["rc"]["memory"] = {
                        "storage": [],
                        "index": {}
                    }
                    self.project_state["env"]["roles"][role_id]["latest_observed_msg"] = None
                logger.info(f"🧹 所有记忆已清除")
            
            self._save_state()
        except Exception as e:
            logger.error(f"❌ 清除记忆失败: {e}")
    
    def export_state(self) -> Dict[str, Any]:
        """导出完整状态"""
        return self.project_state.copy()
    
    def import_state(self, state_data: Dict[str, Any]):
        """导入状态"""
        try:
            self.project_state = state_data
            self._save_state()
            logger.info(f"📥 项目状态已导入")
        except Exception as e:
            logger.error(f"❌ 导入状态失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            return {
                "total_agents": len(self.project_state["env"]["roles"]),
                "total_messages": len(self.project_state["shared_memory"]["storage"]),
                "active_agents": len([
                    role for role in self.project_state["env"]["roles"].values()
                    if role.get("latest_observed_msg") is not None
                ]),
                "project_age_hours": (
                    datetime.now() - datetime.fromisoformat(self.project_state["env"]["created_at"])
                ).total_seconds() / 3600,
                "last_activity": self.project_state["env"]["last_updated"]
            }
        except Exception as e:
            logger.error(f"❌ 获取统计信息失败: {e}")
            return {}