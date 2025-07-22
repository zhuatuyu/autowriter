"""
简化的记忆存储，使用JSON文件存储，避免embedding依赖问题
"""
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from metagpt.logs import logger
from metagpt.schema import Message


class SimpleMemoryStorage:
    """简化的记忆存储，使用JSON文件"""
    
    def __init__(self):
        self.role_id: str = None
        self.memory_file: Path = None
        self.memories: List[Dict[str, Any]] = []
        self._initialized = False
    
    def recover_memory(self, role_id: str, agent_workspace: Path = None) -> List[Message]:
        """恢复记忆"""
        try:
            self.role_id = role_id
            
            # 确定记忆文件路径
            if agent_workspace:
                memory_dir = agent_workspace / "memory"
            else:
                from metagpt.const import DATA_PATH
                memory_dir = Path(DATA_PATH) / f"role_mem/{role_id}"
            
            memory_dir.mkdir(parents=True, exist_ok=True)
            self.memory_file = memory_dir / "memories.json"
            
            # 加载现有记忆
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.memories = json.load(f)
                logger.info(f"🧠 {role_id} 恢复了 {len(self.memories)} 条历史记忆")
            else:
                self.memories = []
                logger.info(f"🆕 {role_id} 是新Agent，创建空记忆存储")
            
            self._initialized = True
            return []
            
        except Exception as e:
            logger.error(f"❌ 恢复记忆失败: {e}")
            self.memories = []
            self._initialized = False
            return []
    
    def add(self, message: Message) -> bool:
        """添加消息到记忆"""
        try:
            if not self._initialized:
                logger.warning("记忆存储未初始化，跳过添加消息")
                return False
            
            # 将消息转换为可序列化的字典
            memory_item = {
                'content': message.content,
                'role': message.role,
                'timestamp': datetime.now().isoformat(),
                'cause_by': str(message.cause_by) if message.cause_by else None,
                'sent_from': message.sent_from if hasattr(message, 'sent_from') else None
            }
            
            self.memories.append(memory_item)
            
            # 限制记忆数量，保留最近的100条
            if len(self.memories) > 100:
                self.memories = self.memories[-100:]
            
            # 立即持久化
            self.persist()
            
            logger.debug(f"✅ Agent {self.role_id} 添加记忆: {message.content[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加记忆失败: {e}")
            return False
    
    def search_similar(self, message: Message, k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似记忆（简化版本，基于关键词匹配）"""
        try:
            if not self._initialized or not self.memories:
                return []
            
            # 简单的关键词匹配
            keywords = message.content.lower().split()
            similar_memories = []
            
            for memory in self.memories:
                content_lower = memory['content'].lower()
                score = sum(1 for keyword in keywords if keyword in content_lower)
                if score > 0:
                    memory_with_score = memory.copy()
                    memory_with_score['similarity_score'] = score
                    similar_memories.append(memory_with_score)
            
            # 按相似度排序并返回前k个
            similar_memories.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_memories[:k]
            
        except Exception as e:
            logger.error(f"❌ 搜索相似记忆失败: {e}")
            return []
    
    def get_recent_memories(self, k: int = 10) -> List[Dict[str, Any]]:
        """获取最近的k条记忆"""
        try:
            if not self._initialized:
                return []
            return self.memories[-k:] if k > 0 else self.memories
        except Exception as e:
            logger.error(f"❌ 获取最近记忆失败: {e}")
            return []
    
    def persist(self):
        """持久化记忆到文件"""
        try:
            if not self._initialized or not self.memory_file:
                return
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"💾 {self.role_id} 的记忆已持久化到 {self.memory_file}")
            
        except Exception as e:
            logger.error(f"❌ 持久化记忆失败: {e}")
    
    def clean(self):
        """清空记忆"""
        try:
            self.memories = []
            if self.memory_file and self.memory_file.exists():
                self.memory_file.unlink()
            logger.info(f"🧹 清理 {self.role_id} 的记忆存储")
        except Exception as e:
            logger.error(f"❌ 清理记忆存储失败: {e}")
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def count(self) -> int:
        """获取记忆数量"""
        return len(self.memories) if self._initialized else 0