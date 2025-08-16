#!/usr/bin/env python3
"""
本地向量化服务
借鉴现有服务的实现方式，为xsearch提供本地文档向量化能力
参考已验证的backend/services代码
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    # 🔧 参考已验证的代码：使用MetaGPT的SimpleEngine
    from metagpt.rag.engines.simple import SimpleEngine
    from metagpt.rag.schema import FAISSRetrieverConfig
    from metagpt.config2 import Config
    from llama_index.llms.openai_like import OpenAILike
    from llama_index.embeddings.dashscope import DashScopeEmbedding
    VECTOR_SERVICES_AVAILABLE = True
except ImportError as e:
    VECTOR_SERVICES_AVAILABLE = False
    print(f"⚠️ 向量化服务依赖不可用: {e}")


class LocalVectorService:
    """本地向量化服务 - 使用MetaGPT SimpleEngine"""
    
    def __init__(self, project_config: Dict[str, Any]):
        self.project_config = project_config
        self.doc_dir = Path(project_config['project_root']) / 'xsearch' / 'doc'
        self.index_dir = Path(project_config['project_root']) / 'xsearch' / 'vector_index'
        
        # 确保目录存在
        self.doc_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置
        self._config = None
        self._engine = None
    
    def _get_config(self) -> Config:
        """获取系统配置"""
        if self._config is None:
            try:
                config_path = Path(self.project_config['project_root']) / 'config' / 'config2.yaml'
                self._config = Config.from_yaml_file(config_path)
            except Exception as e:
                print(f"⚠️ 加载配置文件失败: {e}")
                self._config = None
        return self._config
    
    def _create_llm_and_embed_model(self):
        """创建LLM和嵌入模型"""
        config = self._get_config()
        if not config:
            return None, None
        
        try:
            llm_config = config.llm
            embed_config = config.embedding
            
            # 创建LLM
            llm = OpenAILike(
                model=llm_config.model,
                api_base=llm_config.base_url,
                api_key=llm_config.api_key,
                is_chat_model=True
            )
            
            # 创建Embedding模型
            from metagpt.rag.factories.embedding import get_rag_embedding
            embed_model = get_rag_embedding(config=config)
            embed_model.embed_batch_size = 5  # 修复：降低batch size避免400错误
            
            return llm, embed_model
            
        except Exception as e:
            print(f"⚠️ 创建模型失败: {e}")
            return None, None
    
    def collect_local_documents(self) -> List[str]:
        """收集本地文档文件路径"""
        documents = []
        
        if not self.doc_dir.exists():
            print(f"⚠️ 文档目录不存在: {self.doc_dir}")
            return documents
        
        # 收集所有.md和.txt文件
        for pattern in ["*.md", "*.txt"]:
            for file_path in self.doc_dir.glob(pattern):
                try:
                    print(f"📄 加载文档: {file_path.name}")
                    documents.append(str(file_path))
                except Exception as e:
                    print(f"⚠️ 读取文档失败 {file_path}: {e}")
        
        print(f"📚 共收集到 {len(documents)} 个文档")
        return documents
    
    def is_index_exists(self) -> bool:
        """检查索引是否存在"""
        # 修复：使用正确的索引文件名
        index_files = ['docstore.json', 'index_store.json', 'default__vector_store.json']
        return all((self.index_dir / f).exists() for f in index_files)
    
    async def build_vector_index(self, force_rebuild: bool = False) -> bool:
        """构建向量索引"""
        if not VECTOR_SERVICES_AVAILABLE:
            print("⚠️ 向量化服务不可用")
            return False
        
        try:
            if self.is_index_exists() and not force_rebuild:
                print("✅ 本地向量索引已存在，跳过构建")
                return True
            
            # 收集文档
            documents = self.collect_local_documents()
            if not documents:
                print("⚠️ 没有找到文档，无法构建索引")
                return False
            
            # 创建模型
            llm, embed_model = self._create_llm_and_embed_model()
            if not embed_model:
                print("❌ 嵌入模型创建失败")
                return False
            
            print("🔧 开始构建本地向量索引...")
            
            # 🔧 参考已验证的代码：使用MetaGPT SimpleEngine
            engine = SimpleEngine.from_docs(
                input_files=documents,
                llm=llm,
                embed_model=embed_model,
                retriever_configs=[FAISSRetrieverConfig(dimensions=1024)]  # 使用FAISS支持持久化
            )
            
            # 持久化索引
            engine.persist(str(self.index_dir))
            
            print(f"✅ 本地向量索引构建完成，保存到: {self.index_dir}")
            return True
            
        except Exception as e:
            print(f"❌ 构建本地向量索引失败: {e}")
            return False
    
    async def search_local_documents(self, query: str, top_k: int = 5) -> List[str]:
        """搜索本地文档"""
        if not VECTOR_SERVICES_AVAILABLE:
            print("⚠️ 向量化服务不可用")
            return []
        
        try:
            # 检查索引是否存在
            if not self.is_index_exists():
                print("⚠️ 本地向量索引不存在，尝试构建...")
                if not await self.build_vector_index():
                    return []
            
            # 加载索引
            if not self._engine:
                await self._load_index()
            
            if not self._engine:
                print("❌ 无法加载向量索引")
                return []
            
            # 执行搜索
            results = await self._engine.aretrieve(query)
            
            # 提取搜索结果
            search_results = []
            for result in results[:top_k]:
                if hasattr(result, 'text'):
                    search_results.append(result.text.strip())
            
            print(f"🔍 本地文档搜索完成，找到 {len(search_results)} 条结果")
            return search_results
            
        except Exception as e:
            print(f"❌ 本地文档搜索失败: {e}")
            return []
    
    async def _load_index(self) -> bool:
        """加载已保存的索引"""
        try:
            if not self.index_dir.exists():
                return False
            
            # 创建模型
            llm, embed_model = self._create_llm_and_embed_model()
            if not embed_model:
                return False
            
            print("📖 加载已存在的本地向量索引...")
            
            # 🔧 参考已验证的代码：使用MetaGPT SimpleEngine.from_index
            from metagpt.rag.schema import FAISSIndexConfig
            
            config = FAISSIndexConfig(
                persist_path=str(self.index_dir),
                embed_model=embed_model
            )
            
            self._engine = SimpleEngine.from_index(
                index_config=config,
                embed_model=embed_model,
                llm=llm,
                retriever_configs=[FAISSRetrieverConfig(dimensions=1024)]
            )
            
            print(f"✅ 本地向量索引加载成功")
            return True
            
        except Exception as e:
            print(f"❌ 加载本地向量索引失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "doc_dir": str(self.doc_dir),
            "index_dir": str(self.index_dir),
            "index_exists": self.is_index_exists(),
            "doc_count": 0,
            "index_loaded": self._engine is not None
        }
        
        # 统计文档数量
        if self.doc_dir.exists():
            for pattern in ["*.md", "*.txt"]:
                stats["doc_count"] += len(list(self.doc_dir.glob(pattern)))
        
        return stats
