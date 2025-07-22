"""
自定义长期记忆，使用阿里云DashScope Embedding
"""
from typing import Optional, List

from pydantic import ConfigDict, Field

from metagpt.logs import logger
from metagpt.memory import Memory
from metagpt.roles.role import RoleContext
from metagpt.schema import Message

from backend.services.llm.simple_memory_storage import SimpleMemoryStorage


class CustomLongTermMemory(Memory):
    """
    自定义长期记忆，使用阿里云DashScope Embedding
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    memory_storage: SimpleMemoryStorage = Field(default_factory=SimpleMemoryStorage)
    rc: Optional[RoleContext] = None
    msg_from_recover: bool = False

    def recover_memory(self, role_id: str, rc: RoleContext, agent_workspace=None):
        """恢复记忆"""
        try:
            self.memory_storage.recover_memory(role_id, agent_workspace)
            self.rc = rc
            
            if not self.memory_storage.is_initialized:
                logger.warning(f"⚠️ Agent {role_id} 首次运行，长期记忆为空")
            else:
                logger.info(f"🧠 Agent {role_id} 已恢复历史记忆")
                
        except Exception as e:
            logger.error(f"❌ 恢复记忆失败: {e}")

    def add(self, message: Message):
        """添加消息到记忆"""
        try:
            super().add(message)
            
            # 将所有消息都添加到长期存储（简化版本）
            if not self.msg_from_recover:
                self.memory_storage.add(message)
                        
        except Exception as e:
            logger.error(f"❌ 添加记忆失败: {e}")

    async def find_news(self, observed: List[Message], k=0) -> List[Message]:
        """
        查找新消息（之前未见过的消息）
        1. 先从短期记忆中找到新消息
        2. 然后基于长期记忆过滤掉相似的消息，得到最终的新消息
        """
        try:
            # 获取短期记忆中的新消息
            stm_news = super().find_news(observed, k=k)
            
            if not self.memory_storage.is_initialized:
                # 记忆存储未初始化，直接返回短期记忆的新消息
                return stm_news

            # 基于长期记忆过滤相似消息
            ltm_news: List[Message] = []
            for mem in stm_news:
                # 搜索长期记忆中的相似消息
                mem_searched = await self.memory_storage.search_similar(mem)
                if len(mem_searched) == 0:
                    # 没有找到相似消息，这是真正的新消息
                    ltm_news.append(mem)
                    
            return ltm_news[-k:] if k > 0 else ltm_news
            
        except Exception as e:
            logger.error(f"❌ 查找新消息失败: {e}")
            # 如果出错，返回短期记忆的结果
            return super().find_news(observed, k=k)

    def persist(self):
        """持久化记忆"""
        try:
            self.memory_storage.persist()
        except Exception as e:
            logger.error(f"❌ 持久化记忆失败: {e}")

    def delete(self, message: Message):
        """删除消息"""
        try:
            super().delete(message)
            # TODO: 从memory_storage中删除消息
        except Exception as e:
            logger.error(f"❌ 删除记忆失败: {e}")

    def clear(self):
        """清空记忆"""
        try:
            super().clear()
            self.memory_storage.clean()
        except Exception as e:
            logger.error(f"❌ 清空记忆失败: {e}")

    def count(self) -> int:
        """获取记忆数量"""
        try:
            return len(self.storage)
        except:
            return 0

    def get(self, k: int = 10) -> List[Message]:
        """获取最近的k条记忆"""
        try:
            return self.storage[-k:] if k > 0 else self.storage
        except:
            return []

    def try_remember(self, keyword: str) -> List[Message]:
        """尝试回忆包含关键词的记忆"""
        try:
            relevant_memories = []
            for message in self.storage:
                if keyword.lower() in message.content.lower():
                    relevant_memories.append(message)
            return relevant_memories
        except Exception as e:
            logger.error(f"❌ 回忆记忆失败: {e}")
            return []