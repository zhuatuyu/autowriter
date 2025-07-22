"""
自定义记忆存储，使用阿里云DashScope Embedding
"""
import shutil
from pathlib import Path
from typing import List
import os

from llama_index.core.embeddings import BaseEmbedding
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.core.schema import TextNode

from metagpt.const import DATA_PATH, MEM_TTL
from metagpt.logs import logger
from metagpt.schema import Message

from backend.services.llm.embedding_config import get_embedding_for_memory


class CustomMemoryStorage:
    """
    自定义记忆存储，使用阿里云DashScope Embedding
    """

    def __init__(self, mem_ttl: int = MEM_TTL, embedding: BaseEmbedding = None):
        self.role_id: str = None
        self.role_mem_path: str = None
        self.mem_ttl: int = mem_ttl
        self.threshold: float = 0.1
        self._initialized: bool = False
        
        # 使用我们的自定义embedding配置
        try:
            self.embedding = embedding or get_embedding_for_memory()
            logger.info("✅ 自定义记忆存储使用阿里云DashScope Embedding")
        except Exception as e:
            logger.error(f"❌ 自定义embedding配置失败: {e}")
            # 如果失败，使用默认配置
            from metagpt.utils.embedding import get_embedding
            self.embedding = get_embedding()
            logger.warning("⚠️ 使用默认OpenAI Embedding作为备用")

        self.faiss_engine = None

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def recover_memory(self, role_id: str) -> List[Message]:
        """恢复记忆"""
        try:
            self.role_id = role_id
            self.role_mem_path = Path(DATA_PATH / f"role_mem/{self.role_id}/")
            self.role_mem_path.mkdir(parents=True, exist_ok=True)
            self.cache_dir = self.role_mem_path

            if self.role_mem_path.joinpath("default__vector_store.json").exists():
                logger.info(f"🧠 发现 {role_id} 的历史记忆，正在恢复...")
                self.faiss_engine = VectorStoreIndex.load_from_disk(
                    persist_dir=self.cache_dir,
                    storage_context=StorageContext.from_defaults(persist_dir=self.cache_dir),
                    service_context=self.embedding,
                )
                logger.info(f"✅ {role_id} 的历史记忆恢复成功")
            else:
                logger.info(f"🆕 {role_id} 是新Agent，创建空记忆存储")
                self.faiss_engine = VectorStoreIndex.from_documents(
                    documents=[],
                    storage_context=StorageContext.from_defaults(persist_dir=self.cache_dir),
                    service_context=self.embedding,
                )
            
            self._initialized = True
            return []
            
        except Exception as e:
            logger.error(f"❌ 恢复记忆失败: {e}")
            # 创建空的记忆存储作为备用
            try:
                self.faiss_engine = VectorStoreIndex.from_documents(
                    documents=[],
                    storage_context=StorageContext.from_defaults(persist_dir=self.cache_dir),
                    service_context=self.embedding,
                )
                self._initialized = True
            except Exception as e2:
                logger.error(f"❌ 创建备用记忆存储也失败了: {e2}")
                self._initialized = False
            return []

    def add(self, message: Message) -> bool:
        """添加消息到记忆存储"""
        try:
            if not self._initialized:
                logger.warning("记忆存储未初始化，跳过添加消息")
                return False
                
            self.faiss_engine.add_documents([TextNode(text=message.content)])
            logger.debug(f"✅ Agent {self.role_id} 添加记忆: {message.content[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加记忆失败: {e}")
            return False

    async def search_similar(self, message: Message, k=4) -> List[Message]:
        """搜索相似消息"""
        try:
            if not self._initialized:
                logger.warning("记忆存储未初始化，返回空结果")
                return []
                
            resp = await self.faiss_engine.aretrieve(message.content)
            filtered_resp = []
            
            for item in resp:
                if item.score < self.threshold:
                    obj = item.metadata.get("obj")
                    if obj:
                        filtered_resp.append(obj)
                        
            logger.debug(f"🔍 找到 {len(filtered_resp)} 条相似记忆")
            return filtered_resp
            
        except Exception as e:
            logger.error(f"❌ 搜索相似记忆失败: {e}")
            return []

    def clean(self):
        """清理记忆存储"""
        try:
            if self.cache_dir and self.cache_dir.exists():
                shutil.rmtree(self.cache_dir, ignore_errors=True)
            self._initialized = False
            logger.info(f"🧹 清理 {self.role_id} 的记忆存储")
        except Exception as e:
            logger.error(f"❌ 清理记忆存储失败: {e}")

    def persist(self):
        """持久化记忆存储"""
        try:
            if self.faiss_engine and self._initialized:
                self.faiss_engine.storage_context.persist(self.cache_dir)
                logger.debug(f"💾 {self.role_id} 的记忆已持久化")
        except Exception as e:
            logger.error(f"❌ 持久化记忆失败: {e}")