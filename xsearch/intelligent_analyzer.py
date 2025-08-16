#!/usr/bin/env python3
"""
智能分析器核心类
实现完整的智能分析流程：意图理解 -> 策略生成 -> 检索提取 -> LLM评价
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, List

# Google API环境仅在LangExtract使用时设置

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False
    print("❌ LangExtract未安装，请运行: pip install langextract")

from .llm_client import LLMClient
from .vector_searcher import VectorSearcher
from .knowledge_graph_client import KnowledgeGraphClient

# 导入配置常量
from .config_constants import (
    LANGEXTRACT_CONFIG,
    VECTOR_SEARCH_CONFIG,
    EVALUATION_CONFIG,
    INTENT_ANALYSIS_CONFIG
)


class IntelligentAnalyzer:
    """智能分析器"""
    
    def __init__(self, project_config: Dict[str, Any]):
        self.project_config = project_config
        self.llm_client = LLMClient(project_config)
        self.vector_searcher = VectorSearcher(project_config)
        self.kg_client = KnowledgeGraphClient(project_config)
        
        # 在初始化时构建本地向量索引
        self._init_local_vector_index()
    
    def _init_local_vector_index(self):
        """初始化本地向量索引"""
        try:
            print("🔧 初始化本地向量索引...")
            # 这里只是初始化，实际的构建会在第一次搜索时进行
            stats = self.vector_searcher.local_vector_service.get_stats()
            print(f"📊 本地向量化服务状态:")
            print(f"   文档目录: {stats['doc_dir']}")
            print(f"   索引目录: {stats['index_dir']}")
            print(f"   文档数量: {stats['doc_count']}")
            print(f"   索引存在: {stats['index_exists']}")
        except Exception as e:
            print(f"⚠️ 初始化本地向量索引失败: {e}")
        
    async def analyze_query(self, user_query: str) -> Dict[str, Any]:
        """完整的智能分析流程"""
        
        print("🔍 阶段1: 动态理解查询意图...")
        intent_analysis = await self._analyze_query_intent(user_query)
        
        print("🔧 阶段2: 动态生成检索策略...")
        search_strategy = await self._generate_dynamic_search_strategy(intent_analysis)
        
        print("📊 阶段3: 动态执行检索与提取...")
        project_data, global_methods, extracted_data = await self._dynamic_hybrid_search(search_strategy)
        
        print("🧠 阶段4: 动态生成评价提示词...")
        evaluation_prompt = await self._generate_dynamic_evaluation_prompt(
            extracted_data, global_methods, search_strategy, user_query
        )
        
        print("💬 阶段5: LLM生成评价结果...")
        evaluation_result = await self.llm_client.generate_evaluation(evaluation_prompt)
        
        # 返回完整结果
        return {
            "user_query": user_query,
            "intent_analysis": intent_analysis,
            "search_strategy": search_strategy,
            "extracted_data": extracted_data.extractions[0].attributes if extracted_data.extractions else {},
            "evaluation_result": evaluation_result,
            "data_sources": {
                "project_docs": len(project_data),
                "global_methods": len(global_methods)
            },
            "evaluation_prompt": evaluation_prompt  # 用于调试
        }
    
    async def _analyze_query_intent(self, user_query: str) -> Dict[str, Any]:
        """动态分析用户查询意图，基于具体项目背景"""
        
        # 获取项目信息
        project_name = self.project_config.get('project_name', '未知项目')
        project_type = self.project_config.get('project_type', '未知类型')
        province = self.project_config.get('province', '')
        city = self.project_config.get('city', '')
        county = self.project_config.get('county', '')
        project_description = self.project_config.get('project_description', '')
        
        intent_analysis_prompt = f"""
        请基于以下具体项目背景，分析用户查询的意图，并生成相应的分析结果：

        ## 项目背景信息
        - 项目名称：{project_name}
        - 项目类型：{project_type}
        - 地理位置：{province}{city}{county}
        - 项目描述：{project_description}

        ## 用户查询
        {user_query}

        请结合上述项目背景，从以下维度进行分析：
        1. 查询的核心主题（要结合具体项目类型和特点）
        2. 需要的数据类型（要结合项目实际）
        3. 期望的分析维度（要结合项目类型和描述）
        4. 适合的评价结构（要结合项目特点）
        5. 检索关键词（要结合项目具体内容）
        6. 提取字段（要结合项目实际）

        请以JSON格式输出，确保格式完全正确：
        {{
            "core_topic": "核心主题",
            "data_requirements": ["需要的数据类型1", "需要的数据类型2"],
            "analysis_dimensions": ["分析维度1", "分析维度2"],
            "evaluation_structure": ["评价要点1", "评价要点2"],
            "search_keywords": ["检索关键词1", "检索关键词2"],
            "extraction_fields": ["提取字段1", "提取字段2"]
        }}
        
        分析时要充分考虑项目背景，使结果更加精准和实用。
        """
        
        intent_result = await self.llm_client.analyze_intent(intent_analysis_prompt)
        
        try:
            # 尝试解析JSON
            if isinstance(intent_result, str):
                intent_analysis = json.loads(intent_result)
            else:
                intent_analysis = intent_result
                
            print(f"✅ 查询意图分析完成：{intent_analysis['core_topic']}")
            return intent_analysis
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败，使用默认结构: {e}")
            # 返回默认结构
            return {
                "core_topic": INTENT_ANALYSIS_CONFIG["DEFAULT_CORE_TOPIC"],
                "data_requirements": INTENT_ANALYSIS_CONFIG["DEFAULT_DATA_REQUIREMENTS"],
                "analysis_dimensions": INTENT_ANALYSIS_CONFIG["DEFAULT_ANALYSIS_DIMENSIONS"],
                "evaluation_structure": EVALUATION_CONFIG["DEFAULT_STRUCTURE"],
                "search_keywords": EVALUATION_CONFIG["DEFAULT_SEARCH_KEYWORDS"],
                "extraction_fields": EVALUATION_CONFIG["DEFAULT_EXTRACTION_FIELDS"]
            }
    
    async def _generate_dynamic_search_strategy(self, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """基于意图分析动态生成检索策略"""
        
        # 动态生成项目检索查询
        project_query = " ".join(intent_analysis["search_keywords"])
        
        # 动态生成全局检索查询
        global_query = f"{intent_analysis['core_topic']} 评价规则要点 指标设计 政策法规依据"
        
        # 动态生成LangExtract提示词
        extraction_prompt = f"""
        从项目文档中提取与"{intent_analysis['core_topic']}"相关的信息，包括：
        {chr(10).join([f"- {field}" for field in intent_analysis['extraction_fields']])}
        
        请确保提取的信息准确、完整，能够支持后续的分析评价。
        """
        
        # 动态生成评价结构
        evaluation_structure = intent_analysis['evaluation_structure']
        
        return {
            "project_query": project_query,
            "global_query": global_query,
            "extraction_prompt": extraction_prompt,
            "evaluation_structure": evaluation_structure
        }
    
    async def _dynamic_hybrid_search(
        self, 
        search_strategy: Dict[str, Any]
    ):
        """按需准确搜索：直接调用相应的搜索服务"""
        
        # 1. 项目数据检索（直接搜索）
        project_data = await self.vector_searcher.search_project(
            search_strategy["project_query"]
        )
        
        # 2. 全局方法检索（直接搜索已构建的索引）
        global_methods = await self.vector_searcher.search_global(
            search_strategy["global_query"]
        )
        
        # 3. 动态LangExtract提取
        if LANGEXTRACT_AVAILABLE and project_data:
            extracted_data = await self._extract_with_langextract(
                project_data, search_strategy["extraction_prompt"]
            )
        else:
            # 如果没有LangExtract或没有项目数据，创建空结果
            extracted_data = self._create_empty_extraction_result()
        
        return project_data, global_methods, extracted_data
    
    async def _extract_with_langextract(self, project_data: List[str], extraction_prompt: str):
        """使用LangExtract进行信息提取"""
        
        try:
            # 仅在LangExtract使用时设置Google API环境
            os.environ['GOOGLE_API_KEY'] = 'AIzaSyA-gjWRxk6Y4DUQxIuKtF3R_tp8cjF28gs'
            os.environ['GOOGLE_GENERATIVE_AI_API_KEY'] = 'AIzaSyA-gjWRxk6Y4DUQxIuKtF3R_tp8cjF28gs'
            os.environ['GEMINI_API_KEY'] = 'AIzaSyA-gjWRxk6Y4DUQxIuKtF3R_tp8cjF28gs'
            
            # 合并项目数据
            combined_text = "\n".join(project_data[:LANGEXTRACT_CONFIG["MAX_DOCS_TO_PROCESS"]])  # 使用配置常量控制处理文档数
            
            # 创建示例
            examples = self._create_dynamic_examples(extraction_prompt)
            
            # 调用LangExtract
            result = lx.extract(
                text_or_documents=combined_text,
                prompt_description=extraction_prompt,
                examples=examples,
                model_id=LANGEXTRACT_CONFIG["MODEL_ID"],
                extraction_passes=LANGEXTRACT_CONFIG["EXTRACTION_PASSES"],
                max_workers=LANGEXTRACT_CONFIG["MAX_WORKERS"],
                max_char_buffer=LANGEXTRACT_CONFIG["MAX_CHAR_BUFFER"]
            )
            
            return result
            
        except Exception as e:
            print(f"⚠️ LangExtract提取失败: {e}")
            return self._create_empty_extraction_result()
    
    def _create_dynamic_examples(self, extraction_prompt: str):
        """动态创建示例"""
        return [
            lx.data.ExampleData(
                text="这是一个示例文档，包含项目的基本信息和关键指标。",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="document_summary",
                        extraction_text="示例摘要",
                        attributes={
                            "基本信息": "示例基本信息",
                            "关键指标": "示例关键指标",
                            "问题描述": "示例问题描述"
                        }
                    )
                ]
            )
        ]
    
    def _create_empty_extraction_result(self):
        """创建空的提取结果"""
        # 创建一个模拟的AnnotatedDocument对象
        class MockExtraction:
            def __init__(self):
                self.extractions = []
        
        return MockExtraction()
    
    async def _generate_dynamic_evaluation_prompt(
        self,
        extracted_data: Any,
        global_methods: List[str],
        search_strategy: Dict[str, Any],
        original_query: str
    ):
        """动态生成评价提示词"""
        
        # 构建评价提示词
        evaluation_prompt = f"""
        基于以下信息，回答用户查询：{original_query}
        
        ## 提取的项目数据
        {json.dumps(extracted_data.extractions[0].attributes if extracted_data.extractions else {}, ensure_ascii=False, indent=2)}
        
        ## 相关评价标准和方法
        {chr(10).join(global_methods[:VECTOR_SEARCH_CONFIG["GLOBAL_METHODS_DISPLAY_LIMIT"]])}
        
        请按照以下结构给出分析评价：
        {chr(10).join([f"{i+1}. {point}" for i, point in enumerate(search_strategy['evaluation_structure'])])}
        
        要求：
        1. 分析要基于提取的实际数据
        2. 评价要结合相关标准和方法
        3. 给出具体的评价意见和依据
        4. 提供可操作的改进建议
        """
        
        return evaluation_prompt
