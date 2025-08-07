#!/usr/bin/env python
"""
架构师Action集合 - 报告结构设计和指标分析
重构实现三环节逻辑：分析简报 -> RAG检索 -> 综合设计
配置驱动版本 - 所有业务逻辑通过配置文件管理
"""
import pandas as pd
import json
import re
from typing import List, Tuple, Optional
from pydantic import BaseModel, Field
from metagpt.actions import Action
from metagpt.logs import logger
from backend.actions.research_action import ResearchData
from backend.config.performance_constants import (
    ENV_ARCHITECT_BASE_SYSTEM,
    ENV_RAG_KEYWORDS_GENERATION_PROMPT,
    ENV_SECTION_PROMPT_GENERATION_TEMPLATE,
    ENV_METRICS_DESIGN_PROMPT,
    ENV_EVALUATION_TYPES,
    ENV_SECTION_CONFIGURATIONS,
    ENV_REPORT_SECTIONS,
    ENV_GET_SECTION_CONFIG,
    ENV_GET_SECTION_KEY_BY_TITLE,
    ENV_FALLBACK_KEYWORDS,
    ENV_LEVEL1_INDICATORS,
    ENV_EVIDENCE_KEYWORD_MAPPING
)

# 配置驱动版本 - 所有硬编码常量已移至配置文件
# 通过 ENV_* 常量访问配置化的业务逻辑


class Section(BaseModel):
    """报告章节的结构化模型"""
    section_title: str = Field(..., description="章节标题")
    metric_ids: List[str] = Field(default_factory=list, description="本章节关联的指标ID列表")
    description_prompt: str = Field(..., description="指导本章节写作的核心要点或问题")


class ReportStructure(BaseModel):
    """报告整体架构的结构化模型"""
    title: str = Field(..., description="报告主标题")
    sections: List[Section] = Field(..., description="报告的章节列表")


class MetricAnalysisTable(BaseModel):
    """指标分析表的结构化模型"""
    data_json: str = Field(..., description="存储指标分析结果的DataFrame (JSON格式)")


class ArchitectOutput(BaseModel):
    """Architect输出的复合数据结构"""
    report_structure: ReportStructure = Field(..., description="报告结构设计")
    metric_analysis_table: MetricAnalysisTable = Field(..., description="指标分析表")


class DesignReportStructure(Action):
    """
    设计报告结构Action - Architect的核心能力
    实现三环节逻辑：分析简报 -> RAG检索 -> 综合设计
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._research_data: Optional[ResearchData] = None
        # 🎯 从app2.py传入的项目配置中获取项目信息
        self._project_info: Optional[dict] = None
    
    def set_project_info(self, project_info: dict):
        """设置项目信息（从项目配置文件获取）"""
        self._project_info = project_info
    
    async def run(self, enhanced_research_context: str, research_data: Optional[ResearchData] = None, project_info: dict = None) -> Tuple[ReportStructure, MetricAnalysisTable]:
        """
        🎯 配置驱动的报告结构设计 - 直接使用项目配置，无需LLM提取
        
        Args:
            enhanced_research_context: 可能已经经过RAG增强的研究上下文
            research_data: ProductManager提供的研究数据（包含向量知识库）
            project_info: 从项目配置文件获取的项目信息
        """
        logger.info("🏗️ 开始基于标准模板的报告结构设计...")
        self._research_data = research_data
        
        # 🎯 直接使用配置化的项目信息，无需LLM提取
        if project_info:
            self._project_info = project_info
            logger.info(f"📋 使用配置化项目信息: {project_info.get('project_name', '未知项目')}")
        else:
            # 如果没有传入项目信息，尝试从类属性获取
            if not self._project_info:
                raise ValueError("项目信息未提供，无法进行架构设计。请确保通过项目配置文件提供项目信息")
            project_info = self._project_info
        
        # 步骤一：RAG增强 - 查询详细资料丰富项目信息
        logger.info("🔍 步骤一：RAG检索增强项目信息...")
        enriched_info = await self._enrich_with_rag(project_info)
        
        # 步骤二：标准结构定制 - 基于固定模板生成定制化内容
        logger.info("🏗️ 步骤二：基于标准模板生成定制化内容...")
        report_structure, metric_table = await self._generate_customized_template(enriched_info)
        
        logger.info(f"✅ 报告蓝图设计完成: {report_structure.title}")
        logger.info(f"📊 指标体系: {len(json.loads(metric_table.data_json))} 个指标")
        
        return report_structure, metric_table
    
    # 🎯 移除LLM项目信息提取逻辑 - 直接使用配置化项目信息
    
    def _extract_json_from_llm_response(self, response: str) -> dict:
        """
        从LLM回复中提取JSON内容，处理markdown格式和额外说明
        """
        try:
            # 方法1：尝试直接解析（如果是纯JSON）
            return json.loads(response)
        except:
            pass
        
        try:
            # 方法2：提取```json代码块中的内容
            import re
            json_pattern = r'```json\s*(.*?)\s*```'
            match = re.search(json_pattern, response, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                return json.loads(json_str)
        except:
            pass
        
        try:
            # 方法3：查找大括号包围的JSON内容
            start_idx = response.find('{')
            if start_idx != -1:
                # 找到第一个{，然后找到匹配的}
                brace_count = 0
                end_idx = start_idx
                for i, char in enumerate(response[start_idx:], start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break
                
                if brace_count == 0:
                    json_str = response[start_idx:end_idx+1]
                    return json.loads(json_str)
        except:
            pass
        
        # 如果所有方法都失败，抛出异常
        raise ValueError(f"无法从LLM回复中提取有效JSON: {response[:200]}...")
    
    async def _enrich_with_rag(self, project_info: dict) -> dict:
        """
        步骤二：通过RAG检索丰富项目信息 - 动态生成检索关键词
        """
        if not self._research_data or not self._research_data.content_chunks:
            logger.error("❌ 向量知识库不可用！无法进行RAG增强")
            raise ValueError("向量知识库不可用，无法进行RAG增强。请确保ResearchData包含有效的content_chunks")
        
        # 动态生成检索关键词
        search_keywords = await self._generate_rag_search_keywords(project_info)
        
        enriched_info = project_info.copy()
        enriched_info["rag_evidence"] = {}
        
        logger.info(f"🔍 开始对 {len(search_keywords)} 个动态关键词进行RAG检索...")
        
        # 逐个类别检索
        for keyword_group in search_keywords:
            category = keyword_group["category"]
            keywords = keyword_group["keywords"]
            
            category_evidence = []
            for keyword in keywords:
                try:
                    relevant_chunks = await self._search_chunks(keyword)
                    if relevant_chunks:
                        category_evidence.extend(relevant_chunks[:2])
                except Exception as e:
                    logger.warning(f"关键词 '{keyword}' 检索失败: {e}")
            
            if category_evidence:
                enriched_info["rag_evidence"][category] = category_evidence
                logger.debug(f"📋 {category}: 检索到 {len(category_evidence)} 条相关证据")
        
        # 最后清理重复内容并限制数量
        for category in enriched_info["rag_evidence"]:
            # 去重并限制数量
            unique_chunks = list(dict.fromkeys(enriched_info["rag_evidence"][category]))
            enriched_info["rag_evidence"][category] = unique_chunks[:6]  # 每个类别最多6条
            logger.debug(f"📋 {category}: 最终检索到 {len(enriched_info['rag_evidence'][category])} 条相关证据")
        
        logger.info(f"📋 RAG检索完成，丰富了 {len(enriched_info['rag_evidence'])} 个信息类别")
        return enriched_info
    
    async def _generate_rag_search_keywords(self, project_info: dict) -> List[dict]:
        """
        动态生成RAG检索关键词（类似PM的关键词生成逻辑）
        """
        project_name = project_info.get('project_name', '项目')
        
        keyword_generation_prompt = ENV_RAG_KEYWORDS_GENERATION_PROMPT.format(
            project_info=json.dumps(project_info, ensure_ascii=False, indent=2),
            project_name=project_name
        )
        
        try:
            keywords_result = await self._aask(keyword_generation_prompt)
            
            # 使用同样的JSON提取逻辑
            search_keywords = self._extract_json_from_llm_response(keywords_result)
            
            logger.info(f"🔍 动态生成了 {len(search_keywords)} 个关键词组")
            return search_keywords
        except Exception as e:
            logger.warning(f"动态关键词生成失败，使用配置化备用关键词: {e}")
            # 🎯 使用配置化的备用关键词
            return ENV_FALLBACK_KEYWORDS
    
    async def _search_chunks(self, query: str) -> List[str]:
        """
        🧠 使用智能检索服务进行增强检索
        """
        try:
            from backend.services.intelligent_search import intelligent_search
            
            # 🧠 使用智能检索服务
            if self._research_data and hasattr(self._research_data, 'vector_store_path'):
                search_result = await intelligent_search.intelligent_search(
                    query=query,
                    project_vector_storage_path=self._research_data.vector_store_path,
                    mode="hybrid",  # 使用混合智能检索，自动选择最佳方法
                    enable_global=True,
                    max_results=5
                )
                
                results = search_result.get("results", [])
                
                # 🧠 添加智能分析洞察到结果中
                if search_result.get("insights"):
                    insights_text = "\n💡 智能分析洞察:\n" + "\n".join(search_result["insights"])
                    if results:
                        results[0] = results[0] + insights_text
                    else:
                        results = [insights_text]
                
                logger.debug(f"🧠 智能检索完成，查询: '{query}'，模式: {search_result.get('mode_used', 'unknown')}，找到 {len(results)} 条相关内容")
                return results
                    
        except Exception as e:
            logger.error(f"❌ 智能检索失败: {e}")
            return []
    
    async def _generate_customized_template(self, enriched_info: dict) -> Tuple[ReportStructure, MetricAnalysisTable]:
        """
        步骤三：基于标准绩效评价模板生成定制化内容
        """
        # 🎯 使用配置化的标准绩效评价报告结构
        standard_sections = ENV_REPORT_SECTIONS
        
        # 基于项目信息定制内容描述
        customized_sections = await self._customize_section_content(standard_sections, enriched_info)
        
        # 生成标准指标体系
        metric_table = await self._generate_standard_metrics(enriched_info)
        
        # 构造ReportStructure
        sections = []
        for section_data in customized_sections:
            section = Section(
                section_title=section_data["title"],
                metric_ids=section_data.get("metric_ids", []),
                description_prompt=section_data["description_prompt"]
            )
            sections.append(section)
        
        project_name = enriched_info.get('project_name', '项目')
        report_structure = ReportStructure(
            title=f"{project_name}绩效评价报告",
            sections=sections
        )
        
        return report_structure, metric_table
    
    async def _customize_section_content(self, standard_sections: List[dict], enriched_info: dict) -> List[dict]:
        """
        🎯 配置驱动的章节内容定制 - 移除硬编码的指标关联
        """
        customized_sections = []
        
        for section in standard_sections:
            # 基于项目信息调整prompt
            customized_prompt = await self._generate_section_prompt(section, enriched_info)
            
            customized_section = {
                "title": section["title"],
                "description_prompt": customized_prompt,
                "metric_ids": []  # 🎯 章节不与特定指标关联，由Writer根据实际情况处理
            }
                
            customized_sections.append(customized_section)
        
        return customized_sections
    
    async def _generate_section_prompt(self, section: dict, enriched_info: dict) -> str:
        """
        🎯 配置驱动的章节写作指导生成 - 使用配置化项目信息
        """
        base_prompt = section["prompt_template"]
        # 🎯 使用配置化的项目名称
        project_name = enriched_info.get('project_name', '项目')
        section_title = section["title"]
        
        # 根据章节特点生成具体的RAG检索指导
        rag_instructions = await self._generate_chapter_rag_instructions(section_title, enriched_info)
        
        customized_prompt = ENV_SECTION_PROMPT_GENERATION_TEMPLATE.format(
            project_name=project_name,
            base_prompt=base_prompt,
            rag_instructions=rag_instructions
        )
        
        return customized_prompt
    
    async def _generate_chapter_rag_instructions(self, section_title: str, enriched_info: dict) -> str:
        """
        🎯 配置驱动的章节RAG指导生成 - 替代硬编码条件判断
        """
        rag_evidence = enriched_info.get("rag_evidence", {})
        
        # 🎯 根据章节标题确定对应的配置key
        section_key = self._get_section_key_from_title(section_title)
        
        # 🎯 从配置获取章节特定的RAG指导
        section_config = ENV_GET_SECTION_CONFIG(section_key)
        
        if section_config and 'rag_instructions' in section_config:
            # 使用配置中的指导内容
            instructions = section_config['rag_instructions']
            
            # 动态替换证据摘要占位符
            for category in section_config.get('keywords', []):
                placeholder = f"{{evidence_summary_{category}}}"
                if placeholder in instructions:
                    evidence_summary = self._get_evidence_summary(rag_evidence, category)
                    instructions = instructions.replace(placeholder, evidence_summary)
        else:
            # 通用指导作为备用
            instructions = """
**通用检索指导**
   - 优先检索：项目相关的具体数据、政策文件、实施效果
   - 重点关注：数量化指标、时间节点、责任主体、具体措施
"""
        
        return instructions

    def _get_section_key_from_title(self, section_title: str) -> str:
        """
        🎯 配置驱动的章节标题映射 - 完全消除硬编码
        """
        # 🎯 使用配置管理类的自动匹配方法
        return ENV_GET_SECTION_KEY_BY_TITLE(section_title)
    
    def _get_evidence_summary(self, rag_evidence: dict, category: str) -> str:
        """
        🎯 配置驱动的证据摘要生成 - 消除硬编码关键词判断
        """
        if category in rag_evidence and rag_evidence[category]:
            # 从证据中提取关键词作为检索指导
            evidence_text = " ".join(rag_evidence[category][:2])  # 取前2条证据
            
            # 🎯 使用配置化的关键词映射，消除硬编码
            keywords = []
            for summary_type, mapping in ENV_EVIDENCE_KEYWORD_MAPPING.items():
                type_keywords = mapping.get('keywords', [])
                # 检查证据文本中是否包含该类型的关键词
                if any(keyword in evidence_text for keyword in type_keywords):
                    keywords.append(summary_type)
            
            return ", ".join(keywords) if keywords else "相关项目信息"
        return "项目相关信息（待检索）"
    
    async def _generate_standard_metrics(self, enriched_info: dict) -> MetricAnalysisTable:
        """
        基于项目特点动态生成绩效指标体系
        一级指标固定为：决策、过程、产出、效益
        二级、三级指标根据项目特点由LLM动态生成
        """
        project_name = enriched_info.get('project_name', '项目')
        project_type = enriched_info.get('project_type', '财政支出项目')
        
        # 构造指标设计prompt
        metrics_design_prompt = ENV_METRICS_DESIGN_PROMPT.format(
            project_info=json.dumps(enriched_info, ensure_ascii=False, indent=2),
            project_name=project_name,
            project_type=project_type
        )
        
        try:
            metrics_result = await self._aask(metrics_design_prompt, [ENV_ARCHITECT_BASE_SYSTEM])
            
            # 从LLM回复中提取JSON内容
            metrics_data = self._extract_json_from_llm_response(metrics_result)
            
            # 验证数据完整性和一级指标分布
            validated_metrics = self._validate_metrics_structure(metrics_data)
            
            logger.info(f"📊 动态生成了 {len(validated_metrics)} 个绩效指标")
            logger.info(f"📊 指标分布 - 决策:{self._count_metrics_by_level1(validated_metrics, '决策')}个, "
                       f"过程:{self._count_metrics_by_level1(validated_metrics, '过程')}个, "
                       f"产出:{self._count_metrics_by_level1(validated_metrics, '产出')}个, "
                       f"效益:{self._count_metrics_by_level1(validated_metrics, '效益')}个")
            
            return MetricAnalysisTable(data_json=json.dumps(validated_metrics, ensure_ascii=False))
            
        except Exception as e:
            logger.error(f"LLM指标生成失败，条件不足无法构建指标体系: {e}")
            # 不使用备用方案，直接返回空指标表示无法构建
            empty_metrics = {
                "error": "条件不足，无法构建指标体系",
                "reason": str(e),
                "suggestion": "请确保项目信息完整后重新生成"
            }
            return MetricAnalysisTable(data_json=json.dumps(empty_metrics, ensure_ascii=False))
    
    def _validate_metrics_structure(self, metrics_data: List[dict]) -> List[dict]:
        """
        验证指标数据结构的完整性
        """
        validated_metrics = []
        # 🔧 修复：支持多种字段名格式，兼容新的指标结构
        required_fields = ['metric_id', 'name', 'category', '一级指标', '二级指标', '三级指标', '分值']
        # 可选字段，支持多种格式
        optional_fields = [
            ('evaluation_type', '评价类型'),
            ('evaluation_points', '评价要点'), 
            ('scoring_method', '评分方法', '评分规则'),
            ('评分过程', '评分过程')
        ]
        
        for metric in metrics_data:
            # 检查必需字段
            if all(field in metric for field in required_fields):
                # 🎯 使用配置化的一级指标验证，消除硬编码
                if metric['一级指标'] in ENV_LEVEL1_INDICATORS:
                    # 🔧 标准化字段名，确保兼容性
                    standardized_metric = metric.copy()
                    
                    # 处理评分方法字段的多种格式
                    if 'scoring_method' not in standardized_metric:
                        if '评分方法' in standardized_metric:
                            standardized_metric['scoring_method'] = standardized_metric['评分方法']
                        elif '评分规则' in standardized_metric:
                            standardized_metric['scoring_method'] = standardized_metric['评分规则']
                    
                    # 确保有评分过程字段
                    if '评分过程' not in standardized_metric:
                        if 'evaluation_process' in standardized_metric:
                            standardized_metric['评分过程'] = standardized_metric['evaluation_process']
                        else:
                            standardized_metric['评分过程'] = f"对指标'{metric.get('name', '未知指标')}'进行专业评价"
                    
                    validated_metrics.append(standardized_metric)
                    logger.debug(f"✅ 验证通过指标: {metric.get('name', '未知指标')}")
                else:
                    logger.warning(f"指标 {metric.get('name', '未知')} 的一级指标不符合要求: {metric.get('一级指标', '')}")
            else:
                missing_fields = [field for field in required_fields if field not in metric]
                logger.warning(f"指标数据不完整，缺失字段 {missing_fields}: {metric.get('name', '未知指标')}")
        
        return validated_metrics
    
    def _count_metrics_by_level1(self, metrics: List[dict], level1: str) -> int:
        """
        统计指定一级指标下的指标数量
        """
        return len([m for m in metrics if m.get('一级指标') == level1])
    
