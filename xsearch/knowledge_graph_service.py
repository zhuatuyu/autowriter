#!/usr/bin/env python3
"""
xsearch专用知识图谱服务
基于LlamaIndex KnowledgeGraphIndex，构建领域特定的知识图谱
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from llama_index.core import KnowledgeGraphIndex, Settings
    from llama_index.core.storage.storage_context import StorageContext
    from llama_index.core.graph_stores import SimpleGraphStore
    from llama_index.core.query_engine import KnowledgeGraphQueryEngine
    KG_AVAILABLE = True
    print("✅ 知识图谱依赖加载成功")
except ImportError as e:
    KG_AVAILABLE = False
    print(f"⚠️ 知识图谱依赖不可用: {e}，将使用传统RAG检索")

try:
    from llama_index.llms.openai_like import OpenAILike
    from llama_index.embeddings.dashscope import DashScopeEmbedding
    MODELS_AVAILABLE = True
except ImportError as e:
    MODELS_AVAILABLE = False
    print(f"⚠️ 模型依赖不可用: {e}")


class XSearchKnowledgeGraph:
    """xsearch专用知识图谱服务"""
    
    def __init__(self):
        self._kg_index = None
        self._kg_storage_path = "workspace/vector_storage/global_graph"
        
        # 🎯 绩效分析报告领域的实体/关系（从global_prompts复制）
        self.entity_types = {
            "项目": ["项目名称", "项目类型", "实施地点", "资金规模"],
            "指标体系": ["决策指标", "过程指标", "产出指标", "效益指标"],
            "具体指标": ["指标名称", "计算方法", "目标值", "权重"],
            "政策法规": ["法规名称", "适用范围", "发布机构", "生效时间"],
            "最佳实践": ["实践名称", "适用场景", "实施要点", "预期效果"],
            "问题案例": ["问题类型", "原因分析", "解决方案", "改进建议"],
            "行业类型": ["基础设施", "公益事业", "民生保障", "环境治理"],
        }
        
        self.relation_types = [
            "包含", "属于", "适用于", "遵循", "参考",
            "导致", "解决", "改进", "关联", "影响"
        ]
    
    def _get_config(self) -> Dict[str, Any]:
        """获取配置"""
        try:
            config_path = Path(project_root) / 'config' / 'config2.yaml'
            if config_path.exists():
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                print("⚠️ 配置文件不存在")
                return {}
        except Exception as e:
            print(f"⚠️ 加载配置文件失败: {e}")
            return {}
    
    def _create_kg_llm_and_embed_model(self):
        """创建知识图谱专用的LLM和嵌入模型"""
        if not MODELS_AVAILABLE:
            print("⚠️ 模型依赖不可用")
            return None, None
        
        try:
            config = self._get_config()
            kg_config = config.get('knowledge_graph', {})
            embed_config = config.get('embedding', {})
            
            # 创建知识图谱专用LLM
            llm = OpenAILike(
                model=kg_config.get('model', 'qwen-flash'),
                api_base=kg_config.get('base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
                api_key=kg_config.get('api_key', ''),
                is_chat_model=True
            )
            
            # 创建Embedding模型
            embed_model = DashScopeEmbedding(
                model_name=embed_config.get('model', 'text-embedding-v3'),
                api_key=embed_config.get('api_key', ''),
                dashscope_api_key=embed_config.get('api_key', '')
            )
            embed_model.embed_batch_size = 8
            
            return llm, embed_model
            
        except Exception as e:
            print(f"⚠️ 创建模型失败: {e}")
            return None, None
    
    async def build_knowledge_graph(self, project_vector_storage_path: str) -> bool:
        """构建知识图谱"""
        if not KG_AVAILABLE:
            print("⚠️ 知识图谱功能不可用，跳过构建")
            return False
            
        try:
            print("🧠 开始构建知识图谱...")
            
            # 1. 收集文档
            documents = self._collect_documents(project_vector_storage_path)
            if not documents:
                print("⚠️ 没有找到文档，无法构建知识图谱")
                return False
            
            # 2. 创建存储上下文
            storage_context = self._create_storage_context()
            
            # 3. 设置专用的知识图谱LLM和embedding模型
            llm, embed_model = self._create_kg_llm_and_embed_model()
            if not llm or not embed_model:
                print("❌ 模型创建失败")
                return False
            
            Settings.llm = llm
            Settings.embed_model = embed_model
            Settings.chunk_size = 512
            
            print(f"🧠 知识图谱使用LLM: {type(llm).__name__}")
            print(f"🧠 知识图谱使用Embedding: {type(embed_model).__name__}")
            
            # 4. 构建知识图谱索引
            self._kg_index = KnowledgeGraphIndex.from_documents(
                documents=documents,
                storage_context=storage_context,
                max_triplets_per_chunk=10,
                show_progress=True,
            )
            
            # 5. 保存知识图谱
            self._kg_index.storage_context.persist(self._kg_storage_path)
            
            print(f"✅ 知识图谱构建完成，保存到: {self._kg_storage_path}")
            return True
            
        except Exception as e:
            print(f"❌ 构建知识图谱失败: {e}")
            return False
    
    async def query_knowledge_graph(
        self, 
        query: str, 
        mode: str = "keyword",
        max_knowledge_sequence: int = 5
    ) -> str:
        """查询知识图谱"""
        if not KG_AVAILABLE:
            print("⚠️ 知识图谱功能不可用，降级到向量检索")
            return "知识图谱功能不可用"
            
        try:
            if not self._kg_index:
                print("⚠️ 知识图谱未构建，尝试加载...")
                if not await self._load_knowledge_graph():
                    return "知识图谱不可用，请先构建知识图谱"
            
            # 创建知识图谱查询引擎
            kg_query_engine = self._kg_index.as_query_engine(
                include_text=True,
                retriever_mode=mode,
                response_mode="tree_summarize",
                similarity_top_k=max_knowledge_sequence,
                verbose=True,
            )
            
            # 执行查询
            response = await kg_query_engine.aquery(query)
            
            # 后处理
            enhanced_response = await self._post_process_kg_response(str(response), query)
            
            print(f"🧠 知识图谱推理查询完成: {query}")
            return enhanced_response
            
        except Exception as e:
            print(f"❌ 知识图谱查询失败: {e}")
            return f"查询失败: {e}"
    
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
                    print(f"⚠️ 读取文件失败 {file_path}: {e}")
        
        print(f"📚 收集到 {len(documents)} 个文档用于构建知识图谱")
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
    
    async def _load_knowledge_graph(self) -> bool:
        """加载已保存的知识图谱"""
        if not KG_AVAILABLE:
            return False
            
        try:
            if not Path(self._kg_storage_path).exists():
                return False
            
            # 配置全局设置
            llm, embed_model = self._create_kg_llm_and_embed_model()
            if not llm or not embed_model:
                return False
            
            Settings.llm = llm
            Settings.embed_model = embed_model
            Settings.chunk_size = 512
            
            # 创建存储上下文
            storage_context = StorageContext.from_defaults(persist_dir=self._kg_storage_path)
            
            # 加载知识图谱
            from llama_index.core import load_index_from_storage
            self._kg_index = load_index_from_storage(
                storage_context=storage_context,
            )
            
            print(f"✅ 知识图谱加载成功: {self._kg_storage_path}")
            return True
            
        except Exception as e:
            print(f"❌ 加载知识图谱失败: {e}")
            return False
    
    async def _post_process_kg_response(self, response: str, original_query: str) -> str:
        """知识图谱响应的智能后处理"""
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
        """提取绩效分析报告领域的特定实体"""
        entities = {}
        
        # 简单的关键词匹配
        for entity_type, keywords in self.entity_types.items():
            found_entities = []
            for keyword in keywords:
                if keyword in text:
                    found_entities.append(keyword)
            if found_entities:
                entities[entity_type] = found_entities
        
        return entities
    
    def generate_performance_insights(self, entities: Dict[str, List[str]]) -> List[str]:
        """基于提取的实体生成绩效分析洞察"""
        insights = []
        
        # 生成领域特定的洞察
        if "项目" in entities and "指标体系" in entities:
            insights.append("🎯 该项目应建立完整的绩效指标体系，涵盖决策、过程、产出、效益四个维度")
        
        if "政策法规" in entities:
            insights.append("📋 项目实施应严格遵循相关政策法规要求")
        
        if "最佳实践" in entities:
            insights.append("⭐ 可借鉴相关最佳实践经验，提升项目实施效果")
        
        return insights


# 全局实例
xsearch_kg = XSearchKnowledgeGraph()
