"""
🧠 智能检索统一接口
统一管理向量检索、知识图谱查询和混合智能检索
为所有action提供最智能的检索能力
"""

from typing import List, Dict, Optional, Literal
from metagpt.logs import logger
from .hybrid_search import hybrid_search
from .knowledge_graph import performance_kg
from backend.config.performance_constants import (
    ENV_QUERY_INTENT_MAPPING,
    ENV_SEARCH_MODE_WEIGHTS,
    ENV_INTELLIGENT_TOPK,
)
from backend.config.performance_constants import ENV_KG_MAX_KEYWORDS



class IntelligentSearchService:
    """🧠 智能检索服务 - 双核心检索架构
    
    提供两种核心检索方式：
    1. 🔍 向量检索：基于语义相似度的快速匹配
    2. 🕸️ 知识图谱：基于实体关系的结构化推理
    
    支持模式：
    - vector: 纯向量检索
    - knowledge_graph: 纯知识图谱检索  
    - hybrid: 双核心混合检索（推荐）
    """
    
    def __init__(self):
        self._search_modes = {
            "vector": "向量检索",
            "knowledge_graph": "知识图谱推理",
            "hybrid": "混合智能检索",
        }
    
    async def intelligent_search(
        self,
        query: str,
        project_vector_storage_path: str = "",
        mode: Literal["vector", "knowledge_graph", "hybrid"] = "hybrid",
        enable_global: bool = True,
        max_results: int = 5
    ) -> Dict[str, any]:
        """
        🧠 智能检索统一入口
        
        Args:
            query: 查询问题
            project_vector_storage_path: 项目知识库路径
            mode: 检索模式
            enable_global: 是否启用全局知识库
            max_results: 最大返回结果数
            
        Returns:
            Dict包含results, mode_used, insights等
        """
        logger.info(f"🧠 智能检索开始: {query}, 模式: {mode}")
        
        try:
            if mode == "vector":
                return await self._vector_search(query, project_vector_storage_path, enable_global, max_results)
            elif mode == "knowledge_graph":
                return await self._knowledge_graph_search(query, project_vector_storage_path, max_results)
            elif mode == "hybrid":
                return await self._hybrid_intelligent_search(query, project_vector_storage_path, enable_global, max_results)
            else:
                raise ValueError(f"不支持的检索模式: {mode}")
                
        except Exception as e:
            logger.error(f"❌ 智能检索失败: {e}")
            return {
                "results": [],
                "mode_used": "error",
                "error": str(e),
                "insights": []
            }
    
    async def _vector_search(
        self, 
        query: str, 
        project_path: str, 
        enable_global: bool, 
        max_results: int
    ) -> Dict[str, any]:
        """📊 向量检索模式"""
        try:
            results = await hybrid_search.hybrid_search(
                query=query,
                project_vector_storage_path=project_path,
                enable_global=enable_global,
                global_top_k=max_results//2,
                project_top_k=max_results//2
            )
            
            return {
                "results": results or [],
                "mode_used": "vector",
                "insights": [f"📊 基于向量相似度检索到 {len(results or [])} 条相关内容"],
                "search_summary": f"向量检索模式，查询: {query}"
            }
            
        except Exception as e:
            logger.error(f"❌ 向量检索失败: {e}")
            return {"results": [], "mode_used": "vector_error", "error": str(e), "insights": []}
    
    async def _knowledge_graph_search(
        self, 
        query: str, 
        project_path: str, 
        max_results: int
    ) -> Dict[str, any]:
        """🧠 知识图谱推理模式"""
        try:
            # 首先尝试从项目知识图谱查询
            kg_result = ""
            if project_path:
                try:
                    # 依据配置限制关键词数量：粗粒度按空白/标点分词截取
                    limited_query = self._limit_keywords_in_query(query, ENV_KG_MAX_KEYWORDS)
                    kg_result = await performance_kg.query_knowledge_graph(
                        query=limited_query,
                        mode="keyword",  # 修复：使用支持的模式
                        max_knowledge_sequence=max_results
                    )
                except Exception as e:
                    logger.warning(f"项目知识图谱查询失败: {e}")
            
            # 如果项目KG失败或没有结果，尝试全局知识图谱
            if not kg_result or "知识图谱不可用" in kg_result:
                # 这里可以扩展支持全局知识图谱
                kg_result = "知识图谱功能正在准备中"
            
            # 解析知识图谱结果
            insights = self._extract_kg_insights(kg_result)
            
            return {
                "results": [kg_result] if kg_result else [],
                "mode_used": "knowledge_graph",
                "insights": insights,
                "search_summary": f"知识图谱推理模式，查询: {query}",
                "entities_relations": self._extract_entities_from_kg_result(kg_result)
            }
            
        except Exception as e:
            logger.error(f"❌ 知识图谱查询失败: {e}")
            return {"results": [], "mode_used": "kg_error", "error": str(e), "insights": []}
    

    
    async def _hybrid_intelligent_search(
        self, 
        query: str, 
        project_path: str, 
        enable_global: bool, 
        max_results: int
    ) -> Dict[str, any]:
        """🚀 混合智能检索模式 - 多种方法结合"""
        logger.info("🚀 启动混合智能检索...")
        
        # 🧠 查询意图分析
        search_strategy = await self._analyze_query_intent(query)
        
        # 🔄 并行执行多种检索方法
        import asyncio
        
        tasks = []
        
        # 根据权重与意图选择方法
        vector_w = float(ENV_SEARCH_MODE_WEIGHTS.get("vector", 0))
        kg_w = float(ENV_SEARCH_MODE_WEIGHTS.get("knowledge_graph", 0))

        # 读取可配置的top_k（提供默认值）
        try:
            global_top_k = int(ENV_INTELLIGENT_TOPK.get("global_top_k", max_results // 2 or 2))
            project_top_k = int(ENV_INTELLIGENT_TOPK.get("project_top_k", max_results - global_top_k or 4))
        except Exception:
            global_top_k, project_top_k = max_results // 2 or 2, max_results - (max_results // 2 or 2)

        if vector_w > 0:
            # 在向量检索内部（hybrid_search）按 top_k 精细化控制项目/全局召回
            from .hybrid_search import hybrid_search as _hybrid
            async def _vector_adapter():
                results = await _hybrid.hybrid_search(
                    query=query,
                    project_vector_storage_path=project_path,
                    enable_global=enable_global,
                    global_top_k=global_top_k,
                    project_top_k=project_top_k,
                )
                return {"results": results, "mode_used": "vector", "insights": [f"📊 Vector召回: 项目{project_top_k}, 全局{global_top_k}"]}
            tasks.append(_vector_adapter())
        if kg_w > 0 and search_strategy["use_kg"]:
            tasks.append(self._knowledge_graph_search(query, project_path, max_results))
        

        
        # 并行执行
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 🧠 智能结果融合
        hybrid_result = await self._merge_search_results(search_results, query, search_strategy)
        
        return hybrid_result
    
    async def _analyze_query_intent(self, query: str) -> Dict[str, bool]:
        """🧠 查询意图分析（配置驱动：ENV_QUERY_INTENT_MAPPING）"""
        strategy: Dict[str, bool | str] = {"use_kg": False, "query_type": "general"}
        mapping: Dict[str, List[str]] = ENV_QUERY_INTENT_MAPPING or {}

        matched_type: Optional[str] = None
        for qtype, keywords in mapping.items():
            if any(kw in query for kw in (keywords or [])):
                matched_type = qtype
                break

        if matched_type:
            strategy["query_type"] = matched_type
            # 根据配置优先级：reasoning/policy 强制开启 KG；其余由权重决定
            if matched_type in ("reasoning", "policy"):
                strategy["use_kg"] = True

        logger.debug(f"🧠 查询意图分析(配置驱动): {strategy}")
        return strategy

    def _limit_keywords_in_query(self, query: str, max_keywords: int) -> str:
        """将查询按空白和常见标点粗分词，取前N个关键词，避免KG超长关键词集合导致超时。"""
        if not query or max_keywords <= 0:
            return query
        import re
        # 分割为词元（中文/英文/数字混合场景的粗切分）
        tokens = [t for t in re.split(r"[\s,;，；。.!！？、]+", query) if t]
        if len(tokens) <= max_keywords:
            return query
        limited = tokens[:max_keywords]
        return " ".join(limited)
    
    async def _merge_search_results(
        self, 
        search_results: List[Dict], 
        query: str, 
        strategy: Dict
    ) -> Dict[str, any]:
        """🧠 智能结果融合"""
        merged_results = []
        all_insights = []
        modes_used = []
        
        for result in search_results:
            if isinstance(result, dict) and not isinstance(result, Exception):
                if result.get("results"):
                    merged_results.extend(result["results"])
                if result.get("insights"):
                    all_insights.extend(result["insights"])
                if result.get("mode_used"):
                    modes_used.append(result["mode_used"])
        
        # 🧠 结果去重和排序
        unique_results = self._deduplicate_and_rank_results(merged_results, query)
        
        # 🧠 生成综合洞察
        comprehensive_insights = self._generate_comprehensive_insights(
            unique_results, all_insights, strategy, query
        )
        
        return {
            "results": unique_results,
            "mode_used": "hybrid_intelligent",
            "modes_combined": modes_used,
            "insights": comprehensive_insights,
            "search_summary": f"混合智能检索，结合了{len(modes_used)}种检索方法",
            "strategy_used": strategy
        }
    
    def _deduplicate_and_rank_results(self, results: List[str], query: str) -> List[str]:
        """🧠 结果去重和智能排序"""
        if not results:
            return []
        
        # 简单去重（基于内容相似度）
        unique_results = []
        for result in results:
            # 检查是否与已有结果重复（简单字符串匹配）
            is_duplicate = False
            for existing in unique_results:
                if len(result) > 50 and len(existing) > 50:
                    # 检查长结果的重复度
                    overlap = len(set(result.split()) & set(existing.split()))
                    total_words = len(set(result.split()) | set(existing.split()))
                    if overlap / total_words > 0.7:  # 70%重复度阈值
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_results.append(result)
        
        # 简单排序：较长的、包含查询关键词的结果优先
        query_keywords = set(query.lower().split())
        
        def relevance_score(text: str) -> float:
            text_lower = text.lower()
            keyword_matches = sum(1 for kw in query_keywords if kw in text_lower)
            length_factor = min(len(text) / 1000, 1.0)  # 长度因子，最大1.0
            return keyword_matches + length_factor
        
        unique_results.sort(key=relevance_score, reverse=True)
        
        return unique_results[:5]  # 返回最相关的5个结果
    
    def _generate_comprehensive_insights(
        self, 
        results: List[str], 
        all_insights: List[str], 
        strategy: Dict, 
        query: str
    ) -> List[str]:
        """🧠 生成综合洞察"""
        insights = []
        
        # 基础统计洞察
        if results:
            insights.append(f"🧠 智能检索发现 {len(results)} 条相关信息")
        
        # 策略相关洞察
        if strategy["query_type"] == "reasoning":
            insights.append("🕸️ 检测到关系推理查询，已启用知识图谱分析")
        elif strategy["query_type"] == "exploration":
            insights.append("🔍 检测到探索性查询，已启用深度向量检索")
        elif strategy["query_type"] == "performance":
            insights.append("📊 检测到绩效评价专业查询，已优化检索策略")
        
        # 合并其他洞察
        unique_insights = list(dict.fromkeys(all_insights))  # 去重
        insights.extend(unique_insights[:3])  # 最多保留3个额外洞察
        
        return insights
    
    def _extract_kg_insights(self, kg_result: str) -> List[str]:
        """从知识图谱结果中提取洞察"""
        insights = []
        
        if "### 🕸️ 发现的实体关系" in kg_result:
            insights.append("🕸️ 知识图谱发现了实体间的关系")
        
        if "### 💡 绩效分析洞察" in kg_result:
            insights.append("💡 知识图谱生成了绩效分析专业洞察")
        
        if not insights:
            insights.append("🧠 知识图谱提供了结构化推理结果")
        
        return insights
    
    def _extract_entities_from_kg_result(self, kg_result: str) -> Dict[str, List[str]]:
        """从知识图谱结果中提取实体关系"""
        # 这里可以解析知识图谱结果中的实体关系信息
        # 简化实现
        return {}


# 全局实例
intelligent_search = IntelligentSearchService()