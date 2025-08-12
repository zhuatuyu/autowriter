"""
绩效分析报告知识图谱服务
专门针对绩效分析报告领域的知识图谱构建和查询

基于LlamaIndex KnowledgeGraphIndex，构建领域特定的知识图谱：
- 项目 -> 指标体系 -> 具体指标
- 项目 -> 行业类型 -> 最佳实践
- 政策法规 -> 适用项目类型
- 案例 -> 解决方案 -> 改进建议
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from metagpt.logs import logger
try:
    from llama_index.core import KnowledgeGraphIndex, Settings
    from llama_index.core.storage.storage_context import StorageContext
    from llama_index.core.graph_stores import SimpleGraphStore
    from llama_index.core.query_engine import KnowledgeGraphQueryEngine
    KG_AVAILABLE = True
    logger.info("✅ 知识图谱依赖加载成功")
except ImportError as e:
    KG_AVAILABLE = False
    logger.warning(f"⚠️ 知识图谱依赖不可用: {e}，将使用传统RAG检索")

from .hybrid_search import hybrid_search
from metagpt.config2 import Config
from pathlib import Path

# 配置驱动
from backend.config.global_prompts import (
    QUERY_INTENT_MAPPING,
    KG_CONF,
    KG_ENTITY_TYPES,
    KG_RELATION_TYPES,
)


class PerformanceKnowledgeGraph:
    """绩效分析报告领域知识图谱"""
    
    def __init__(self):
        self._kg_index = None
        self._kg_storage_path = "workspace/vector_storage/global_graph"
        # 🎯 绩效分析报告领域的实体/关系（常量化默认集）
        # 从全局常量读取（可在 global_prompts 中调整）
        self.entity_types = KG_ENTITY_TYPES
        self.relation_types = KG_RELATION_TYPES
    
    async def build_knowledge_graph(self, project_vector_storage_path: str) -> bool:
        """
        构建绩效分析报告知识图谱
        
        Args:
            project_vector_storage_path: 项目知识库路径
        """
        if not KG_AVAILABLE:
            logger.warning("⚠️ 知识图谱功能不可用，跳过构建")
            return False
            
        try:
            logger.info("🧠 开始构建绩效分析报告知识图谱...")
            
            # 1. 收集文档
            documents = self._collect_documents(project_vector_storage_path)
            if not documents:
                logger.warning("⚠️ 没有找到文档，无法构建知识图谱")
                return False
            
            # 2. 创建存储上下文
            storage_context = self._create_storage_context()
            
            # 3. 设置专用的知识图谱LLM和embedding模型
            llm, embed_model = self._create_kg_llm_and_embed_model()
            Settings.llm = llm
            Settings.embed_model = embed_model
            Settings.chunk_size = 512  # 知识图谱适合较小的chunk
            
            logger.info(f"🧠 知识图谱使用LLM: {type(llm).__name__}")
            logger.info(f"🧠 知识图谱使用Embedding: {type(embed_model).__name__}")
            logger.info(f"🔑 LLM API Key: {llm.api_key[:8]}...")
            logger.info(f"🤖 LLM Model: {getattr(llm, 'model', getattr(llm, 'model_name', 'Unknown'))}")
            
            # 4. 构建知识图谱索引
            self._kg_index = KnowledgeGraphIndex.from_documents(
                documents=documents,
                storage_context=storage_context,
                max_triplets_per_chunk=10,  # 每个chunk最多提取10个三元组
                show_progress=True,
            )
            
            # 5. 保存知识图谱
            self._kg_index.storage_context.persist(self._kg_storage_path)
            
            logger.info(f"✅ 知识图谱构建完成，保存到: {self._kg_storage_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 构建知识图谱失败: {e}")
            return False
    
    async def query_knowledge_graph(
        self, 
        query: str, 
        mode: str = "keyword",
        max_knowledge_sequence: int = 5
    ) -> str:
        """
        🧠 智能推理式查询知识图谱
        
        Args:
            query: 查询问题
            mode: 查询模式 ("keyword", "embedding", "keyword_embedding") - 注意：不支持"hybrid"
            max_knowledge_sequence: 最大知识序列长度
        """
        if not KG_AVAILABLE:
            logger.warning("⚠️ 知识图谱功能不可用，降级到向量检索")
            # 降级到传统RAG检索
            from .hybrid_search import hybrid_search
            results = await hybrid_search.hybrid_search(
                query=query,
                project_vector_storage_path="",
                enable_global=True,
                global_top_k=max_knowledge_sequence
            )
            return "\n".join(results) if results else "无可用结果"
            
        try:
            if not self._kg_index:
                logger.warning("⚠️ 知识图谱未构建，尝试加载...")
                if not await self._load_knowledge_graph():
                    return "知识图谱不可用，请先构建知识图谱"
            
            # 创建知识图谱查询引擎 - 配置驱动（支持 kg_profiles 按意图切档）
            retriever_mode = "keyword"
            response_mode = "tree_summarize"
            similarity_top_k_cfg = max_knowledge_sequence
            # 简化：使用默认 retriever/response 配置，可按需要扩展


            kg_query_engine = self._kg_index.as_query_engine(
                include_text=True,
                retriever_mode=retriever_mode,  # "keyword", "embedding"
                response_mode=response_mode,
                similarity_top_k=similarity_top_k_cfg,
                verbose=True,
            )
            
            # 🧠 智能查询增强 - 根据领域特点优化查询
            enhanced_query = await self._enhance_domain_query(query)

            # 🚦 增强后再次限词（可配置），避免增强文本引入过多关键词导致KG冗长推理
            # 从全局配置读取增强后限词策略
            try:
                limit_after = bool(KG_CONF.get("limit_keywords_after_enhance", True))
                max_after = int(KG_CONF.get("max_keywords_after_enhance", 5))
            except Exception:
                limit_after, max_after = True, 5
            if limit_after and max_after > 0:
                enhanced_query = self._limit_keywords_in_text(enhanced_query, max_after)
            
            # 执行查询
            response = await kg_query_engine.aquery(enhanced_query)
            
            # 🧠 后处理 - 提取关系推理结果
            enhanced_response = await self._post_process_kg_response(str(response), query)
            
            logger.info(f"🧠 知识图谱推理查询完成: {query}")
            return enhanced_response
            
        except Exception as e:
            logger.error(f"❌ 知识图谱查询失败: {e}")
            return f"查询失败: {e}"

    def _limit_keywords_in_text(self, text: str, max_keywords: int) -> str:
        """将文本按空白/标点切分后取前N个标记再拼接，控制查询长度。"""
        if not text or max_keywords <= 0:
            return text
        import re
        tokens = [t for t in re.split(r"[\s,;，；。.!！？、]+", text) if t]
        if len(tokens) <= max_keywords:
            return text
        return " ".join(tokens[:max_keywords])
    
    async def _enhance_domain_query(self, query: str) -> str:
        """🎯 基于配置的查询增强：使用 intelligent_search.query_intent_mapping 动态分析意图"""
        intents = self._analyze_intents_by_config(query)
        if not intents:
            return query
        context = self._build_intent_context(intents)
        # 提示实体类型与关系类型，利于KG推理
        entity_type_list = ", ".join(list(self.entity_types.keys())[:8])
        relation_type_list = ", ".join(self.relation_types[:8])
        preface = (
            f"请结合领域知识图谱进行回答；优先使用已知实体类型（{entity_type_list} 等）与关系（{relation_type_list} 等）进行推理与引用。\n"
        )
        return f"{context}\n{preface}{query}"

    def _analyze_intents_by_config(self, query: str) -> List[str]:
        """根据配置的意图关键词映射分析查询意图"""
        try:
            mapping: Dict[str, List[str]] = QUERY_INTENT_MAPPING or {}
            matched: List[str] = []
            q = query or ""
            for intent, keywords in mapping.items():
                if not isinstance(keywords, list):
                    continue
                if any(kw for kw in keywords if kw and kw in q):
                    matched.append(intent)
            return matched
        except Exception:
            return []

    def _build_intent_context(self, intents: List[str]) -> str:
        """把意图映射为领域上下文说明，避免硬编码 if/else，采用意图到模板的映射"""
        intent_to_template: Dict[str, str] = {
            "policy": "围绕政策/法规条款进行回答，注明条款出处，阐明适用范围与合规要求。",
            "method": "围绕评价/分析方法与步骤（如AHP、计分规则）进行说明，并给出可复用的操作路径。",
            "case": "围绕相似项目/案例进行对标，总结关键做法与成效，提供可引用的证据来源。",
            "metric": "围绕绩效指标体系进行回答，优先按决策、过程、产出、效益四个维度组织，明确评价要点与计分方法。",
            # 允许透传未知意图
        }
        parts = [intent_to_template.get(i, f"围绕{i} 相关知识进行说明，并提供证据与可执行路径。") for i in intents]
        return "\n".join(parts)
    
    async def _post_process_kg_response(self, response: str, original_query: str) -> str:
        """🧠 知识图谱响应的智能后处理"""
        # 添加推理路径说明
        enhanced_response = f"### 🧠 知识图谱推理结果\n\n{response}\n\n"
        
        # 尝试提取实体关系
        entities = self.extract_domain_entities(response)
        if entities:
            enhanced_response += "### 🕸️ 发现的实体关系\n"
            for entity_type, entity_list in entities.items():
                enhanced_response += f"- **{entity_type}**: {', '.join(entity_list)}\n"
        
        # 生成领域洞察
        insights = self.generate_performance_insights(entities)
        if insights:
            enhanced_response += "\n### 💡 绩效分析洞察\n"
            for insight in insights:
                enhanced_response += f"- {insight}\n"
        
        return enhanced_response
    
    def extract_domain_entities(self, text: str) -> Dict[str, List[str]]:
        """
        提取绩效分析报告领域的特定实体
        
        Args:
            text: 输入文本
            
        Returns:
            Dict[实体类型, 实体列表]
        """
        entities = {}
        
        # 简单的关键词匹配（生产环境应使用NER模型）
        for entity_type, keywords in self.entity_types.items():
            found_entities = []
            for keyword in keywords:
                if keyword in text:
                    found_entities.append(keyword)
            if found_entities:
                entities[entity_type] = found_entities
        
        return entities
    
    def generate_performance_insights(self, entities: Dict[str, List[str]]) -> List[str]:
        """
        基于提取的实体生成绩效分析洞察
        
        Args:
            entities: 提取的实体字典
            
        Returns:
            洞察列表
        """
        insights = []
        
        # 生成领域特定的洞察
        if "项目" in entities and "指标体系" in entities:
            insights.append("🎯 该项目应建立完整的绩效指标体系，涵盖决策、过程、产出、效益四个维度")
        
        if "政策法规" in entities:
            insights.append("📋 项目实施应严格遵循相关政策法规要求")
        
        if "最佳实践" in entities:
            insights.append("⭐ 可借鉴相关最佳实践经验，提升项目实施效果")
        
        return insights
    
    def _create_kg_llm_and_embed_model(self):
        """
        🎯 创建知识图谱专用的LLM和嵌入模型
        使用config2.yaml中的knowledge_graph配置
        """
        import yaml
        # 只读取我们应用侧的 config/config2.yaml，避免 example/MetaGPT_bak 生效
        with open('config/config2.yaml', 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f)
        
        kg_config = yaml_config.get('knowledge_graph', {})
        embed_config = yaml_config.get('embedding', {})
        
        # 🔧 按照阿里云官方文档使用OpenAI-Like方式创建图谱专用LLM
        from llama_index.embeddings.dashscope import DashScopeEmbedding
        from llama_index.llms.openai_like import OpenAILike
        
        # 创建知识图谱专用LLM - 使用qwen-flash快速低成本模型
        kg_llm = OpenAILike(
            model=kg_config.get('model', 'qwen-flash'),  # qwen-flash
            api_base=kg_config.get('base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
            api_key=kg_config.get('api_key', ''),
            is_chat_model=True
        )
        
        # 创建Embedding模型 - 复用embedding配置
        embed_model = DashScopeEmbedding(
            model_name=embed_config.get('model', 'text-embedding-v3'),  # text-embedding-v3
            api_key=embed_config.get('api_key', ''),
            dashscope_api_key=embed_config.get('api_key', '')
        )
        embed_model.embed_batch_size = 8
        
        return kg_llm, embed_model
    
    def _collect_documents(self, project_vector_storage_path: str) -> List[Any]:
        """收集项目文档"""
        from llama_index.core import Document
        
        documents = []
        project_path = Path(project_vector_storage_path)
        
        if not project_path.exists():
            return documents
        
        # 收集所有.md和.txt文件
        for pattern in ["*.md", "*.txt"]:
            for file_path in project_path.glob(pattern):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    doc = Document(text=content, metadata={"filename": file_path.name})
                    documents.append(doc)
                except Exception as e:
                    logger.warning(f"读取文件失败 {file_path}: {e}")
        
        logger.info(f"📚 收集到 {len(documents)} 个文档用于构建知识图谱")
        return documents
    
    def _create_storage_context(self):
        """创建存储上下文"""
        if not KG_AVAILABLE:
            return None
            
        # 确保存储目录存在
        Path(self._kg_storage_path).mkdir(parents=True, exist_ok=True)
        
        # 创建图存储
        graph_store = SimpleGraphStore()
        storage_context = StorageContext.from_defaults(graph_store=graph_store)
        
        return storage_context
    
    def _configure_settings(self):
        """配置全局设置"""
        # 使用与hybrid_search相同的LLM和embedding配置
        llm, embed_model = hybrid_search._create_llm_and_embed_model()
        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.chunk_size = 512
    
    async def _load_knowledge_graph(self) -> bool:
        """加载已保存的知识图谱"""
        if not KG_AVAILABLE:
            return False
            
        try:
            if not Path(self._kg_storage_path).exists():
                return False
            
            # 配置全局设置
            self._configure_settings()
            
            # 创建存储上下文
            storage_context = StorageContext.from_defaults(persist_dir=self._kg_storage_path)
            
            # 加载知识图谱 - 修复加载方法
            from llama_index.core import load_index_from_storage
            self._kg_index = load_index_from_storage(
                storage_context=storage_context,
            )
            
            logger.info(f"✅ 知识图谱加载成功: {self._kg_storage_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 加载知识图谱失败: {e}")
            return False


# 全局实例
performance_kg = PerformanceKnowledgeGraph()