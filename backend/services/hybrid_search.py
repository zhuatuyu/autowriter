"""
混合检索服务
同时检索全局知识库和项目知识库，合并结果
"""

import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from metagpt.logs import logger
from metagpt.rag.engines.simple import SimpleEngine
from metagpt.rag.schema import FAISSRetrieverConfig
from metagpt.config2 import Config

from .global_knowledge import global_knowledge


class HybridSearchService:
    """混合检索服务：全局知识库 + 项目知识库"""
    
    def __init__(self):
        self._project_engines = {}  # 缓存项目引擎
        self._config = None
    
    def _get_config(self) -> Config:
        """获取配置"""
        if self._config is None:
            self._config = Config.from_yaml_file(Path('config/config2.yaml'))
        return self._config
    
    def _create_llm_and_embed_model(self):
        """创建LLM和嵌入模型"""
        config = self._get_config()
        llm_config = config.llm
        embed_config = config.embedding
        
        # 🔧 按照阿里云官方文档使用OpenAI-Like方式 
        from llama_index.embeddings.dashscope import DashScopeEmbedding
        from llama_index.llms.openai_like import OpenAILike
        
        # 创建LLM - 使用官方推荐的OpenAI-Like方式
        llm = OpenAILike(
            model=llm_config.model,  # 从配置文件读取：qwen-max-latest
            api_base=llm_config.base_url,  # "https://dashscope.aliyuncs.com/compatible-mode/v1"
            api_key=llm_config.api_key,
            is_chat_model=True
        )
        
        # 创建Embedding模型 - 使用官方DashScopeEmbedding
        embed_model = DashScopeEmbedding(
            model_name=embed_config.model,  # text-embedding-v3
            api_key=embed_config.api_key,
            dashscope_api_key=embed_config.api_key  # DashScope专用参数
        )
        embed_model.embed_batch_size = 8
        
        return llm, embed_model
    
    def _get_project_vector_index_path(self, project_vector_storage_path: str) -> str:
        """获取项目向量索引路径"""
        project_dir = Path(project_vector_storage_path).parent
        return str(project_dir / "vector_index")
    
    def _is_project_index_exists(self, index_path: str) -> bool:
        """检查项目索引是否存在"""
        index_path = Path(index_path)
        # 使用正确的FAISS索引文件名
        index_files = ['default__vector_store.json', 'docstore.json', 'index_store.json']
        return all((index_path / f).exists() for f in index_files)
    
    async def _build_project_index(self, project_vector_storage_path: str) -> bool:
        """构建项目向量索引"""
        try:
            # 收集项目文档
            project_files = []
            if os.path.isdir(project_vector_storage_path):
                project_files = [
                    os.path.join(project_vector_storage_path, f) 
                    for f in os.listdir(project_vector_storage_path) 
                    if f.endswith(('.md', '.txt'))
                ]
            
            if not project_files:
                logger.warning(f"⚠️ 项目知识库为空: {project_vector_storage_path}")
                return False
            
            logger.info(f"🔧 构建项目知识库索引: {len(project_files)} 个文件")
            llm, embed_model = self._create_llm_and_embed_model()
            
            # 🚀 使用FAISS Retriever支持持久化
            from metagpt.rag.schema import FAISSRetrieverConfig
            
            # 构建引擎时就指定支持持久化的配置
            engine = SimpleEngine.from_docs(
                input_files=project_files,
                llm=llm,
                embed_model=embed_model,
                retriever_configs=[FAISSRetrieverConfig(dimensions=1024)]  # 使用FAISS支持持久化
            )
            
            index_path = self._get_project_vector_index_path(project_vector_storage_path)
            Path(index_path).mkdir(parents=True, exist_ok=True)
            
            # 持久化索引
            engine.persist(index_path)
            
            logger.info(f"✅ 项目知识库索引已保存到: {index_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 构建项目知识库索引失败: {e}")
            return False
    
    async def _get_project_engine(self, project_vector_storage_path: str) -> SimpleEngine:
        """获取或创建项目知识库引擎"""
        cache_key = project_vector_storage_path
        
        # 检查缓存
        if cache_key in self._project_engines:
            return self._project_engines[cache_key]
        
        try:
            index_path = self._get_project_vector_index_path(project_vector_storage_path)
            
            # 检查索引是否存在，不存在则构建
            if not self._is_project_index_exists(index_path):
                logger.info("📁 项目索引不存在，开始构建...")
                if not await self._build_project_index(project_vector_storage_path):
                    raise Exception("构建项目索引失败")
            
            # 从索引加载引擎
            logger.info(f"📖 加载项目知识库索引: {index_path}")
            llm, embed_model = self._create_llm_and_embed_model()
            
            from metagpt.rag.schema import FAISSIndexConfig
            config = FAISSIndexConfig(
                persist_path=index_path,
                embed_model=embed_model
            )
            engine = SimpleEngine.from_index(
                index_config=config,
                embed_model=embed_model,
                llm=llm,
                retriever_configs=[FAISSRetrieverConfig(dimensions=1024)]
            )
            
            # 缓存引擎
            self._project_engines[cache_key] = engine
            logger.info("✅ 项目知识库引擎加载成功")
            return engine
            
        except Exception as e:
            logger.error(f"❌ 获取项目知识库引擎失败: {e}")
            raise
    
    async def _search_project_knowledge(self, query: str, project_vector_storage_path: str, top_k: int = 3) -> List[str]:
        """搜索项目知识库"""
        try:
            engine = await self._get_project_engine(project_vector_storage_path)
            results = await engine.aretrieve(query)
            return [result.text.strip() for result in results[:top_k]]
        except Exception as e:
            logger.error(f"❌ 项目知识库搜索失败: {e}")
            return []
    
    def _merge_search_results(
        self, 
        global_results: List[str], 
        project_results: List[str],
        global_weight: float = 0.3,
        project_weight: float = 0.7,
        limit: int = 6,
    ) -> List[str]:
        """合并检索结果，项目知识库权重更高"""
        
        merged_results = []
        
        # 先添加项目结果（权重更高）
        for result in project_results:
            if result and result.strip():
                merged_results.append(f"📁 [项目知识] {result.strip()}")
        
        # 再添加全局结果
        for result in global_results:
            if result and result.strip():
                merged_results.append(f"🌍 [全局知识] {result.strip()}")
        
        # 去重并限制总数
        seen = set()
        unique_results = []
        for result in merged_results:
            if result not in seen:
                seen.add(result)
                unique_results.append(result)
        
        return unique_results[:limit]  # 限制总结果数（可配置）
    
    async def hybrid_search(
        self, 
        query: str, 
        project_vector_storage_path: str,
        enable_global: bool = True,
        global_top_k: int = 2,
        project_top_k: int = 4
    ) -> List[str]:
        """
        混合检索：同时搜索全局知识库和项目知识库
        
        Args:
            query: 搜索查询
            project_vector_storage_path: 项目向量存储路径
            enable_global: 是否启用全局知识库搜索
            global_top_k: 全局知识库返回结果数
            project_top_k: 项目知识库返回结果数
        """
        try:
            tasks = []
            
            # 项目知识库搜索（总是执行）
            project_task = self._search_project_knowledge(
                query, project_vector_storage_path, project_top_k
            )
            tasks.append(project_task)
            
            # 全局知识库搜索（可选）
            if enable_global:
                global_task = global_knowledge.search_global(query, global_top_k)
                tasks.append(global_task)
            else:
                tasks.append(asyncio.coroutine(lambda: [])())
            
            # 并行执行
            project_results, global_results = await asyncio.gather(*tasks)
            
            logger.info(f"🔍 混合检索完成 - 项目结果: {len(project_results)}, 全局结果: {len(global_results)}")
            
            # 合并结果（按 top_k 之和限制总结果数）
            return self._merge_search_results(global_results, project_results, limit=max(1, int(global_top_k) + int(project_top_k)))
            
        except Exception as e:
            logger.error(f"❌ 混合检索失败: {e}")
            return []
    
    def invalidate_project_cache(self, project_vector_storage_path: str):
        """清除项目引擎缓存（当项目文档更新时调用）"""
        cache_key = project_vector_storage_path
        if cache_key in self._project_engines:
            del self._project_engines[cache_key]
            logger.info(f"🗑️ 已清除项目引擎缓存: {cache_key}")
    
    # ========== 📁 项目知识库管理功能 ==========
    
    def create_project_knowledge_base(self, project_id: str, workspace_root: str = "workspace") -> str:
        """
        为项目创建专用知识库目录
        
        Returns:
            str: 项目向量存储路径
        """
        project_vector_path = Path(workspace_root) / project_id / "vector_storage" / "project_docs"
        project_vector_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 项目知识库已创建: {project_vector_path}")
        return str(project_vector_path)
    
    def add_content_to_project(self, content: str, filename: str, project_vector_storage_path: str, invalidate_cache: bool = True) -> bool:
        """
        添加内容到项目知识库 - 🚀 统一使用MetaGPT原生分块策略
        
        Args:
            content: 文档内容
            filename: 文件名
            project_vector_storage_path: 项目向量存储路径
        """
        try:
            # 确保目录存在
            Path(project_vector_storage_path).mkdir(parents=True, exist_ok=True)
            
            # 🚀 改为保存完整文件，让MetaGPT内部处理分块
            file_path = Path(project_vector_storage_path) / filename
            file_path.write_text(content, encoding='utf-8')
            
            # 清除缓存，强制重建索引（可配置）
            if invalidate_cache:
                self.invalidate_project_cache(project_vector_storage_path)
            
            logger.info(f"📄 已添加完整文档到项目知识库: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加内容到项目知识库失败: {e}")
            return False
    
    def add_multiple_contents_to_project(self, contents: List[dict], project_vector_storage_path: str) -> bool:
        """
        批量添加内容到项目知识库
        
        Args:
            contents: 内容列表，格式为 [{"content": "内容", "filename": "文件名"}, ...]
            project_vector_storage_path: 项目向量存储路径
        """
        try:
            # 仅对“新增或内容变更”的文件进行写入，并在最后统一失效缓存
            Path(project_vector_storage_path).mkdir(parents=True, exist_ok=True)

            added_or_updated = 0
            skipped_unchanged = 0

            for idx, item in enumerate(contents):
                new_content = item.get("content", "")
                filename = item.get("filename", f"content_{idx}.txt")
                file_path = Path(project_vector_storage_path) / filename

                is_unchanged = False
                if file_path.exists():
                    try:
                        old_content = file_path.read_text(encoding='utf-8')
                        is_unchanged = (old_content == new_content)
                    except Exception:
                        # 读取失败则视为需要更新
                        is_unchanged = False

                if is_unchanged:
                    skipped_unchanged += 1
                    continue

                # 新增或变更：写入但不立即失效缓存
                file_path.write_text(new_content, encoding='utf-8')
                added_or_updated += 1

            # 仅当有变更时，统一失效缓存
            if added_or_updated > 0:
                self.invalidate_project_cache(project_vector_storage_path)

            logger.info(
                f"📦 批量同步完成: 新增/更新 {added_or_updated} 个，跳过未变化 {skipped_unchanged} 个，总计 {len(contents)} 个"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ 批量添加内容失败: {e}")
            return False
    
    # 🗑️ 移除复杂的手动分块逻辑，统一使用MetaGPT原生SentenceSplitter
    # 这样与全局知识库保持一致，简化维护复杂度
    
    def get_project_knowledge_stats(self, project_vector_storage_path: str) -> dict:
        """获取项目知识库统计信息"""
        try:
            if not Path(project_vector_storage_path).exists():
                return {"exists": False, "file_count": 0, "index_exists": False}
            
            # 统计文件数量
            files = list(Path(project_vector_storage_path).glob("*.txt"))
            file_count = len(files)
            
            # 检查索引是否存在
            index_path = self._get_project_vector_index_path(project_vector_storage_path)
            index_exists = self._is_project_index_exists(index_path)
            
            return {
                "exists": True,
                "file_count": file_count,
                "index_exists": index_exists,
                "storage_path": project_vector_storage_path,
                "index_path": index_path
            }
        except Exception as e:
            logger.error(f"❌ 获取项目知识库统计失败: {e}")
            return {"exists": False, "error": str(e)}


# 全局单例实例
hybrid_search = HybridSearchService()