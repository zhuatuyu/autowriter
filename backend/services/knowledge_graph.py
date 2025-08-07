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


class PerformanceKnowledgeGraph:
    """绩效分析报告领域知识图谱"""
    
    def __init__(self):
        self._kg_index = None
        self._kg_storage_path = "workspace/vector_storage/global_graph"
        
        # 🎯 绩效分析报告领域的实体类型定义
        self.entity_types = {
            "项目": ["项目名称", "项目类型", "实施地点", "资金规模"],
            "指标体系": ["决策指标", "过程指标", "产出指标", "效益指标"],
            "具体指标": ["指标名称", "计算方法", "目标值", "权重"],
            "政策法规": ["法规名称", "适用范围", "发布机构", "生效时间"],
            "最佳实践": ["实践名称", "适用场景", "实施要点", "预期效果"],
            "问题案例": ["问题类型", "原因分析", "解决方案", "改进建议"],
            "行业类型": ["基础设施", "公益事业", "民生保障", "环境治理"],
        }
        
        # 🎯 关系类型定义
        self.relation_types = [
            "包含", "属于", "适用于", "遵循", "参考",
            "导致", "解决", "改进", "关联", "影响"
        ]
    
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
            
            # 创建知识图谱查询引擎 - 使用正确的参数
            kg_query_engine = self._kg_index.as_query_engine(
                include_text=True,
                retriever_mode="keyword",  # "keyword", "embedding", "keyword_embedding"
                response_mode="tree_summarize",  # 使用官方推荐的响应模式
                similarity_top_k=max_knowledge_sequence,
                verbose=True,
            )
            
            # 🧠 智能查询增强 - 根据领域特点优化查询
            enhanced_query = await self._enhance_domain_query(query)
            
            # 执行查询
            response = await kg_query_engine.aquery(enhanced_query)
            
            # 🧠 后处理 - 提取关系推理结果
            enhanced_response = await self._post_process_kg_response(str(response), query)
            
            logger.info(f"🧠 知识图谱推理查询完成: {query}")
            return enhanced_response
            
        except Exception as e:
            logger.error(f"❌ 知识图谱查询失败: {e}")
            return f"查询失败: {e}"
    
    async def _enhance_domain_query(self, query: str) -> str:
        """🎯 绩效分析领域的查询增强"""
        # 检测查询类型并添加领域特定的上下文
        if any(keyword in query for keyword in ["指标", "评价", "绩效"]):
            return f"在绩效分析评价体系中，{query}。请重点关注决策、过程、产出、效益四个维度的相关信息。"
        elif any(keyword in query for keyword in ["项目", "实施", "管理"]):
            return f"关于项目实施和管理，{query}。请分析项目背景、实施过程、组织管理等方面的信息。"
        elif any(keyword in query for keyword in ["问题", "风险", "挑战"]):
            return f"针对项目风险和问题，{query}。请识别潜在风险因素及其影响。"
        elif any(keyword in query for keyword in ["建议", "改进", "优化"]):
            return f"关于改进建议，{query}。请结合最佳实践和成功案例提供建议。"
        else:
            return query
    
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
        
        # 直接读取YAML文件来获取knowledge_graph配置
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