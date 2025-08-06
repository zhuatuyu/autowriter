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
from metagpt.rag.factories.embedding import get_rag_embedding
from metagpt.rag.schema import FAISSRetrieverConfig
from metagpt.config2 import Config
from llama_index.llms.openai import OpenAI as LlamaOpenAI

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
        
        llm = LlamaOpenAI(
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            model="gpt-3.5-turbo"
        )
        
        embed_model = get_rag_embedding(config=config)
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
        project_weight: float = 0.7
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
        
        return unique_results[:6]  # 限制总结果数
    
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
            
            # 合并结果
            return self._merge_search_results(global_results, project_results)
            
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
    
    def add_content_to_project(self, content: str, filename: str, project_vector_storage_path: str) -> bool:
        """
        添加内容到项目知识库
        
        Args:
            content: 文档内容
            filename: 文件名
            project_vector_storage_path: 项目向量存储路径
        """
        try:
            # 确保目录存在
            Path(project_vector_storage_path).mkdir(parents=True, exist_ok=True)
            
            # 内容分块处理
            chunks = self._split_content_to_chunks(content)
            
            # 保存分块到文件
            for i, chunk in enumerate(chunks):
                chunk_filename = f"{Path(filename).stem}_chunk_{i}.txt"
                chunk_file_path = Path(project_vector_storage_path) / chunk_filename
                chunk_file_path.write_text(chunk.strip(), encoding='utf-8')
            
            # 清除缓存，强制重建索引
            self.invalidate_project_cache(project_vector_storage_path)
            
            logger.info(f"📄 已添加 {len(chunks)} 个内容块到项目知识库: {filename}")
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
            success_count = 0
            for item in contents:
                if self.add_content_to_project(
                    content=item.get("content", ""),
                    filename=item.get("filename", f"content_{success_count}.txt"),
                    project_vector_storage_path=project_vector_storage_path
                ):
                    success_count += 1
            
            logger.info(f"📦 批量添加完成: {success_count}/{len(contents)} 个内容成功添加")
            return success_count == len(contents)
            
        except Exception as e:
            logger.error(f"❌ 批量添加内容失败: {e}")
            return False
    
    def _split_content_to_chunks(self, content: str, max_chunk_size: int = 2000) -> List[str]:
        """
        🚀 智能内容分块逻辑 - 基于语义边界的优化策略
        参考业界最佳实践：1024 tokens ≈ 2000字符 为最优平衡点
        """
        # 🎯 优化1: 提高最小有效chunk大小，避免无意义的小片段
        min_chunk_size = 200  # 避免产生过小的无意义chunk
        
        if len(content) <= max_chunk_size:
            return [content] if len(content.strip()) >= min_chunk_size else []
        
        chunks = []
        
        # 🎯 优化2: 优先保护表格完整性
        if self._contains_table(content):
            table_chunks = self._handle_table_content(content, max_chunk_size)
            if table_chunks:
                return table_chunks
        
        # 🎯 优化3: 递归分块策略，保持语义完整性
        # 分隔符优先级：章节 > 段落 > 句子 > 强制分割
        separators = [
            '\n\n## ',  # 章节标题
            '\n\n# ',   # 主标题  
            '\n\n',     # 段落分隔
            '\n',       # 行分隔
            '。',       # 句子分隔
            '；',       # 分句
            '，',       # 短语分隔
        ]
        
        # 递归分块
        chunks = self._recursive_split(content, max_chunk_size, min_chunk_size, separators)
        
        # 🎯 优化4: 添加10%重叠，避免边界信息丢失
        overlapped_chunks = self._add_overlap(chunks, overlap_ratio=0.1)
        
        # 🎯 优化5: 过滤过小的chunks，避免噪声
        valid_chunks = [chunk for chunk in overlapped_chunks if len(chunk.strip()) >= min_chunk_size]
        
        logger.debug(f"📝 智能分块完成: {len(content)} 字符 -> {len(valid_chunks)} 个有效块")
        return valid_chunks
    
    def _contains_table(self, content: str) -> bool:
        """检测内容是否包含表格"""
        table_indicators = ['<table>', '<tr>', '<td>', '|---|', '|----']
        return any(indicator in content for indicator in table_indicators)
    
    def _handle_table_content(self, content: str, max_chunk_size: int) -> List[str]:
        """处理包含表格的内容，保持表格完整性"""
        # 简单策略：如果整个内容包含表格且不超过最大大小，保持完整
        if len(content) <= max_chunk_size * 1.5:  # 表格允许稍微超过限制
            return [content]
        
        # 复杂表格：尝试按表格分割
        table_parts = content.split('<table>')
        if len(table_parts) > 1:
            chunks = []
            current_chunk = table_parts[0]
            
            for i, part in enumerate(table_parts[1:], 1):
                table_content = '<table>' + part
                if len(current_chunk + table_content) <= max_chunk_size:
                    current_chunk += table_content
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = table_content
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            return chunks
        
        return []
    
    def _recursive_split(self, text: str, max_size: int, min_size: int, separators: List[str], depth: int = 0) -> List[str]:
        """递归分割策略"""
        if len(text) <= max_size:
            return [text] if len(text.strip()) >= min_size else []
        
        if depth >= len(separators):
            # 强制按字符分割
            return [text[i:i+max_size] for i in range(0, len(text), max_size)]
        
        separator = separators[depth]
        parts = text.split(separator)
        
        if len(parts) == 1:
            # 当前分隔符无效，尝试下一个
            return self._recursive_split(text, max_size, min_size, separators, depth + 1)
        
        chunks = []
        current_chunk = ""
        
        for i, part in enumerate(parts):
            # 重新添加分隔符
            if i > 0:
                part = separator + part
            
            if len(current_chunk + part) <= max_size:
                current_chunk += part
            else:
                if current_chunk.strip() and len(current_chunk.strip()) >= min_size:
                    chunks.append(current_chunk.strip())
                
                # 如果单个part还是太大，递归分割
                if len(part) > max_size:
                    chunks.extend(self._recursive_split(part, max_size, min_size, separators, depth + 1))
                    current_chunk = ""
                else:
                    current_chunk = part
        
        if current_chunk.strip() and len(current_chunk.strip()) >= min_size:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _add_overlap(self, chunks: List[str], overlap_ratio: float = 0.1) -> List[str]:
        """添加chunk间重叠，避免边界信息丢失"""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = [chunks[0]]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i-1]
            curr_chunk = chunks[i]
            
            # 计算重叠长度
            overlap_length = int(len(prev_chunk) * overlap_ratio)
            if overlap_length > 0:
                # 从前一个chunk末尾取重叠内容
                overlap_text = prev_chunk[-overlap_length:]
                overlapped_chunk = overlap_text + "\n\n" + curr_chunk
                overlapped_chunks.append(overlapped_chunk)
            else:
                overlapped_chunks.append(curr_chunk)
        
        return overlapped_chunks
    
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