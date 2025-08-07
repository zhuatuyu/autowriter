#!/usr/bin/env python
"""
架构师Action集合 - 报告结构设计和指标分析
重构实现三环节逻辑：分析简报 -> RAG检索 -> 综合设计
"""
import pandas as pd
import json
import re
from typing import List, Tuple, Optional
from pydantic import BaseModel, Field
from metagpt.actions import Action
from metagpt.logs import logger
from backend.actions.research_action import ResearchData


# --- 架构师专用提示词模板 ---
ARCHITECT_BASE_SYSTEM = """你是绩效评价报告的架构师。你的目标是：
1. 深入分析研究简报，提取项目核心信息
2. 基于标准绩效评价框架设计报告结构
3. 构建科学的指标体系，确保评价的全面性和准确性
"""

PROJECT_INFO_EXTRACTION_PROMPT = """你是绩效评价报告的架构师。请从以下研究简报中提取项目的核心信息，用于后续基于标准模板的报告结构设计。

研究简报：
{research_brief}

请返回JSON格式，包含以下字段：
1. project_name: 项目全称
2. project_type: 项目类型（如：财政支出项目、专项资金项目等）
3. budget_amount: 项目预算金额（如果有）
4. implementation_period: 实施期间
5. target_beneficiaries: 主要受益对象
6. main_objectives: 主要目标（列表形式）
7. key_activities: 主要活动内容（列表形式）
8. performance_focus: 绩效重点关注领域（如：经济效益、社会效益、生态效益等）

要求：
- 信息要准确、完整
- 如果某些信息不明确，标注为"待补充"
- 重点关注与绩效评价相关的信息
"""

RAG_KEYWORDS_GENERATION_PROMPT = """你是架构师的RAG检索助手。基于以下项目信息，生成用于检索向量知识库的关键词组。

项目信息：
{project_info}

请生成6个类别的检索关键词，每个类别包含3-5个具体的检索词：

返回JSON格式：
[
  {{
    "category": "项目背景与目标",
    "keywords": ["项目立项背景", "主要目标", "预期成果"]
  }},
  {{
    "category": "资金与预算",
    "keywords": ["预算总额", "资金来源", "资金分配"]
  }},
  {{
    "category": "实施方案",
    "keywords": ["实施步骤", "技术方案", "管理措施"]
  }},
  {{
    "category": "效果与成效",
    "keywords": ["实施效果", "产出指标", "效益分析"]
  }},
  {{
    "category": "政策依据",
    "keywords": ["政策文件", "法规依据", "标准规范"]
  }},
  {{
    "category": "风险与挑战",
    "keywords": ["存在问题", "风险因素", "改进建议"]
  }}
]

要求：关键词要具体、准确，能在{project_name}相关资料中找到对应信息。
"""

SECTION_PROMPT_GENERATION_TEMPLATE = """针对{project_name}，{base_prompt}

### 📋 具体写作指导与检索要求：

{rag_instructions}

### 🔍 RAG检索策略：
写作时请严格按照以下步骤进行：
1. 首先检索上述关键信息项，获取具体数据和事实
2. 基于检索到的真实信息进行分析和论述
3. 避免泛泛而谈，确保每个论点都有具体的数据支撑
4. 如果某项信息检索不到，明确标注"信息待补充"

### 📊 质量要求：
- 数据准确：所有数字、时间、名称必须来自检索到的原始资料
- 逻辑清晰：按照检索指导的顺序组织内容结构
- 深度分析：不仅要列出事实，还要分析原因和影响
"""

METRICS_DESIGN_PROMPT = """你是绩效评价指标体系的架构师。请基于以下项目信息，设计一套完整的绩效评价指标体系。

项目信息：
{project_info}

指标体系设计要求：
1. 一级指标权重分配：决策(15分)、过程(25分)、产出(35分)、效益(25分)
2. 每个一级指标下设置2-3个具体指标
3. 每个指标必须选择一种评价类型，共6种可选：
   - "要素符合度计分": 根据符合的要素数量计分
   - "公式计算得分": 通过数学公式计算得分  
   - "条件判断得分": 根据是否满足条件计分
   - "定性与定量结合": 综合定性和定量评价
   - "递减扣分机制": 从满分开始根据问题扣分
   - "李克特量表法": 通过满意度调查计分

请返回JSON格式，每个指标包含：
- metric_id: 唯一标识（英文）
- name: 指标名称（中文）
- category: 指标分类
- 一级指标: "决策"/"过程"/"产出"/"效益"
- 二级指标: 具体的二级指标名称
- 三级指标: 具体的三级指标名称
- 分值: 该指标权重分值（与一级指标权重匹配）
- evaluation_type: 评价类型（必须选择上述6种之一）
- evaluation_points: 具体评价要点（数组格式，如["①立项符合法规","②符合规划"]）
- scoring_method: 详细计分方式（如"具备一个要素得20%分值"）
- 评分过程: Writer执行评价的具体指导

⚠️ 重要格式要求：
- 所有字段名必须使用英文或中文，不能混用
- scoring_method字段必须一致，不能使用"评分方法"或"scoring方法"
- 确保JSON格式完全正确，所有字段都有值

标准示例：
[
  {{
    "metric_id": "policy_compliance",
    "name": "政策合规性",
    "category": "决策指标",
    "一级指标": "决策",
    "二级指标": "政策符合性",
    "三级指标": "政策合规率",
    "分值": 7.5,
    "evaluation_type": "要素符合度计分",
    "evaluation_points": [
      "①项目立项符合国家法律法规、国民经济发展规划和相关政策",
      "②项目立项符合行业发展规划和政策要求",
      "③项目立项与部门职责范围相符，属于部门履职所需",
      "④项目属于公共财政支持范围，符合中央、地方事权支出责任划分原则",
      "⑤该项目与相关部门同类项目或者部门内部相关项目无交叉重复"
    ],
    "scoring_method": "具备一个得分要素，得到指标分值的20%",
    "评分过程": "Writer需核对项目文件与国家、地方政府政策的匹配程度，检查相关法律法规引用情况及政策依据材料，对照评价要点逐一判断符合情况"
  }}
]

请为{project_name}（{project_type}）设计8-12个指标，确保：
- 决策类指标总分值=15分
- 过程类指标总分值=25分  
- 产出类指标总分值=35分
- 效益类指标总分值=25分
- 每个指标都有明确的评价类型和详细评价要点
"""

# 6种标准化评价类型定义
EVALUATION_TYPES = {
    "要素符合度计分": {
        "description": "根据各项要素的符合情况进行计分",
        "scoring_guidance": """要素符合度计分计算步骤：
1. 从事实中识别符合的要素（如"符合评价要点①②"）
2. 从规则中提取每个要素的分值
3. 将符合要素的分值相加得到最终得分

示例：事实"符合①②，不符合③"，规则"①②各30%，③40%"
计算：30+30+0=60分""",
        "opinion_requirements": """- 必须包含具体的法规引用、文件名称等详实内容
- 明确列出每个评价要点的符合/不符合情况
- 使用分号分隔各要点的评价
- 不得包含任何最终得分或结论性语句"""
    },
    
    "公式计算得分": {
        "description": "通过特定公式计算得出分数",
        "scoring_guidance": """公式计算得分步骤：
1. 从规则中找到计算公式
2. 从事实中提取数值
3. 代入公式计算，结果换算到100分制

示例：预算执行率=实际支出/预算金额×100%
实际支出800万，预算1000万
计算：800/1000×100%=80%，得80分""",
        "opinion_requirements": """- 必须列出具体的计算数据和来源
- 展示完整的计算公式和计算过程
- 如有多年数据，需计算加权平均值
- 百分比保留两位小数
- 不得包含任何最终得分或结论性语句"""
    },
    
    "条件判断得分": {
        "description": "根据是否满足特定条件来计分",
        "scoring_guidance": """条件判断得分步骤：
1. 识别事实满足的条件档次
2. 给予该档次对应的分数

示例：条件"项目有完整预算"，事实"项目编制了详细预算"
判断：满足条件，得100分""",
        "opinion_requirements": """- 明确说明每个条件的满足/不满足情况
- 提供具体的证据材料或事实依据
- 对于不满足的条件，说明具体缺失什么
- 不得包含任何最终得分或结论性语句"""
    },
    
    "定性与定量结合": {
        "description": "结合定性描述和定量数据进行评价",
        "scoring_guidance": """定性与定量结合步骤：
1. 分别计算定量和定性部分分数
2. 按权重合并分数

示例：定量部分（60%权重）：完成率90%，得90分
定性部分（40%权重）：质量优秀，得95分
综合得分：90×0.6+95×0.4=92分""",
        "opinion_requirements": """- 定量部分：列出具体数据、百分比、金额等
- 定性部分：描述实地调研、访谈等发现的情况
- 两部分要有机结合，不能割裂
- 对于部分达标的情况，明确扣分比例
- 不得包含任何最终得分或结论性语句"""
    },
    
    "递减扣分机制": {
        "description": "从满分开始根据问题情况进行扣分",
        "scoring_guidance": """递减扣分机制步骤：
1. 从满分开始
2. 根据问题数量扣分
3. 计算最终剩余分数

示例：满分100分，每个问题扣10分
发现3个问题，扣30分
最终得分：100-30=70分""",
        "opinion_requirements": """- 列出发现的每个问题及具体表现
- 说明每类问题的扣分标准
- 问题要具体到时间、地点、责任主体
- 不得包含任何最终得分或结论性语句"""
    },
    
    "李克特量表法": {
        "description": "通过调查问卷和统计分析计算满意度",
        "scoring_guidance": """李克特量表法步骤：
1. 根据满意度百分比对应分数档次
2. 或直接将满意度百分比作为得分

示例：满意度调查结果92.8%
90%以上为优秀，得满分
最终得分：100分""",
        "opinion_requirements": """- 说明调查方法和样本量
- 列出各满意度等级的具体人数
- 展示满意度计算公式和过程
- 满意度百分比保留两位小数
- 不得包含任何最终得分或结论性语句"""
    }
}


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
    
    async def run(self, enhanced_research_context: str, research_data: Optional[ResearchData] = None) -> Tuple[ReportStructure, MetricAnalysisTable]:
        """
        基于标准绩效评价模板设计报告结构，内容根据项目特点定制
        
        Args:
            enhanced_research_context: 可能已经经过RAG增强的研究上下文
            research_data: ProductManager提供的研究数据（包含向量知识库）
        """
        logger.info("🏗️ 开始基于标准模板的报告结构设计...")
        self._research_data = research_data
        
        # 从增强上下文中提取原始研究简报
        research_brief = self._extract_original_brief(enhanced_research_context)
        
        # 步骤一：项目信息提取 - 从研究简报和RAG中提取项目核心信息
        logger.info("📋 步骤一：提取项目核心信息...")
        project_info = await self._extract_project_info(research_brief)
        
        # 步骤二：RAG增强 - 查询详细资料丰富项目信息
        logger.info("🔍 步骤二：RAG检索增强项目信息...")
        enriched_info = await self._enrich_with_rag(project_info)
        
        # 步骤三：标准结构定制 - 基于固定模板生成定制化内容
        logger.info("🏗️ 步骤三：基于标准模板生成定制化内容...")
        report_structure, metric_table = await self._generate_customized_template(enriched_info)
        
        logger.info(f"✅ 报告蓝图设计完成: {report_structure.title}")
        logger.info(f"📊 指标体系: {len(json.loads(metric_table.data_json))} 个指标")
        
        return report_structure, metric_table
    
    def _extract_original_brief(self, enhanced_context: str) -> str:
        """从增强上下文中提取原始研究简报"""
        # 如果包含RAG增强内容，提取原始部分
        if "### RAG检索增强内容" in enhanced_context:
            parts = enhanced_context.split("### RAG检索增强内容")
            return parts[0].strip()
        return enhanced_context
    
    async def _extract_project_info(self, research_brief: str) -> dict:
        """
        步骤一：从研究简报中提取项目核心信息
        """
        extraction_prompt = PROJECT_INFO_EXTRACTION_PROMPT.format(research_brief=research_brief)
        
        try:
            extraction_result = await self._aask(extraction_prompt, [ARCHITECT_BASE_SYSTEM])
            
            # 从LLM回复中提取JSON内容
            project_info = self._extract_json_from_llm_response(extraction_result)
            
            logger.info(f"📋 项目名称: {project_info.get('project_name', '未知项目')}")
            logger.info(f"📋 项目类型: {project_info.get('project_type', '待补充')}")
            return project_info
        except Exception as e:
            logger.error(f"项目信息提取失败，无法继续设计: {e}")
            raise ValueError(f"无法从研究简报中提取有效项目信息: {e}")
    
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
        
        keyword_generation_prompt = RAG_KEYWORDS_GENERATION_PROMPT.format(
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
            logger.warning(f"动态关键词生成失败，使用基础关键词: {e}")
            # 基础关键词作为备用
            return [
                {"category": "项目基本信息", "keywords": ["项目名称", "项目背景", "主要目标"]},
                {"category": "资金预算", "keywords": ["预算金额", "资金来源", "支出明细"]},
                {"category": "实施内容", "keywords": ["实施方案", "技术措施", "管理流程"]},
                {"category": "绩效指标", "keywords": ["评价指标", "成果产出", "效益分析"]}
            ]
    
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
        # 标准绩效评价报告结构（基于reportmodel.yaml）
        standard_sections = [
            {
                "title": "一、项目概述",
                "key": "overview",
                "prompt_template": "请围绕以下方面详细描述项目概况：1. 项目立项背景及目的、项目主要内容；2. 资金投入和使用情况、项目实施情况；3. 项目组织管理；4. 项目绩效目标：通过知识库搜索绩效目标表复制相关内容，务必以表格形式展示项目绩效指标"
            },
            {
                "title": "二、综合绩效评价结论",
                "key": "conclusion", 
                "prompt_template": "请基于对项目决策、过程、产出和效益四个维度的全面绩效分析，给出项目的综合评价结论。应包含项目总得分、评价等级，并务必以表格形式清晰展示各一级指标（决策、过程、产出、效益）的计划分值、实际得分和得分率"
            },
            {
                "title": "三、主要成效及经验",
                "key": "achievements",
                "prompt_template": "请详细总结项目实施过程中所取得的各项主要成效，需结合具体数据和事实进行阐述。同时，提炼出项目在政策执行、资金管理、部门协同、服务优化等方面可供其他地区或类似项目借鉴的成功经验和有效做法"
            },
            {
                "title": "四、存在的问题和原因分析",
                "key": "problems",
                "prompt_template": "请根据调研（如问卷调查、访谈）和数据分析，客观、准确地指出项目在实施过程中存在的主要问题。对于每个识别出的问题，都应深入剖析其产生的内外部原因"
            },
            {
                "title": "五、改进建议",
                "key": "suggestions",
                "prompt_template": "针对在'存在的问题和原因分析'部分指出的各项主要问题，请逐条提出具体的、有针对性的、可操作的改进建议。建议应明确改进方向、责任主体和预期效果"
            }
        ]
        
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
        定制化章节内容描述
        """
        customized_sections = []
        project_name = enriched_info.get('project_name', '项目')
        
        for section in standard_sections:
            # 基于项目信息调整prompt
            customized_prompt = await self._generate_section_prompt(section, enriched_info)
            
            customized_section = {
                "title": section["title"],
                "description_prompt": customized_prompt,
                "metric_ids": []
            }
            
            # 为"项目概述"章节添加指标关联
            if "概述" in section["title"]:
                customized_section["metric_ids"] = ["project_scope", "budget_execution", "target_completion"]
            elif "评价结论" in section["title"]:
                customized_section["metric_ids"] = ["overall_score", "decision_score", "process_score", "output_score", "benefit_score"]
                
            customized_sections.append(customized_section)
        
        return customized_sections
    
    async def _generate_section_prompt(self, section: dict, enriched_info: dict) -> str:
        """
        生成特定章节的写作指导prompt - 基于RAG证据给出具体检索指导
        """
        base_prompt = section["prompt_template"]
        project_name = enriched_info.get('project_name', '项目')
        section_title = section["title"]
        
        # 根据章节特点生成具体的RAG检索指导
        rag_instructions = await self._generate_chapter_rag_instructions(section_title, enriched_info)
        
        customized_prompt = SECTION_PROMPT_GENERATION_TEMPLATE.format(
            project_name=project_name,
            base_prompt=base_prompt,
            rag_instructions=rag_instructions
        )
        
        return customized_prompt
    
    async def _generate_chapter_rag_instructions(self, section_title: str, enriched_info: dict) -> str:
        """
        为每个章节生成具体的RAG检索指导
        """
        rag_evidence = enriched_info.get("rag_evidence", {})
        
        # 根据章节标题生成具体的检索指导
        if "项目概述" in section_title:
            instructions = f"""
**1. 项目立项背景及目的**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "项目背景与目标")}
   - 重点查找：政策文件引用、立项依据、目标设定
   
**2. 资金投入和使用情况**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "资金与预算")}
   - 重点查找：预算总额、资金来源、分配明细、执行进度
   
**3. 项目组织管理**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "实施方案")}
   - 重点查找：管理机构、职责分工、流程制度
   
**4. 项目绩效目标**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "效果与成效")}
   - 重点查找：绩效目标表、指标设定、预期成果（务必以表格形式展示）
"""
        elif "综合绩效评价结论" in section_title:
            instructions = f"""
**决策、过程、产出、效益四个维度分析**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "效果与成效")}
   - 重点查找：各项指标完成情况、评分结果、综合得分
   - 必须输出：指标得分情况表（一级指标、分值、得分、得分率）
"""
        elif "主要成效及经验" in section_title:
            instructions = f"""
**具体成效数据**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "效果与成效")}
   - 重点查找：量化成果数据、受益人群统计、效果对比
   
**成功经验总结**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "实施方案")}
   - 重点查找：创新做法、管理经验、技术亮点
"""
        elif "存在的问题和原因分析" in section_title:
            instructions = f"""
**问题识别**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "风险与挑战")}
   - 重点查找：调研发现的问题、数据反映的不足、反馈意见
   
**原因深度分析**
   - 检索关键词：政策执行、管理制度、技术条件、外部环境
   - 重点查找：问题产生的内在机制和外部因素
"""
        elif "改进建议" in section_title:
            instructions = f"""
**针对性建议**
   - 基于前述问题分析，检索关键词：{self._get_evidence_summary(rag_evidence, "风险与挑战")}
   - 重点查找：改进措施、政策建议、技术优化方案
   
**可操作性验证**
   - 检索关键词：成功案例、最佳实践、政策支持
   - 重点查找：类似项目的改进经验、政策可行性分析
"""
        else:
            # 通用指导
            instructions = f"""
**通用检索指导**
   - 优先检索：项目相关的具体数据、政策文件、实施效果
   - 重点关注：数量化指标、时间节点、责任主体、具体措施
"""
        
        return instructions
    
    def _get_evidence_summary(self, rag_evidence: dict, category: str) -> str:
        """
        获取特定类别的RAG证据摘要，用于指导检索
        """
        if category in rag_evidence and rag_evidence[category]:
            # 从证据中提取关键词作为检索指导
            evidence_text = " ".join(rag_evidence[category][:2])  # 取前2条证据
            # 简单提取关键概念
            keywords = []
            if "预算" in evidence_text or "资金" in evidence_text:
                keywords.append("预算资金数据")
            if "目标" in evidence_text or "指标" in evidence_text:
                keywords.append("目标指标设定")
            if "实施" in evidence_text or "管理" in evidence_text:
                keywords.append("实施管理措施")
            if "效果" in evidence_text or "成果" in evidence_text:
                keywords.append("实施效果数据")
            
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
        metrics_design_prompt = METRICS_DESIGN_PROMPT.format(
            project_info=json.dumps(enriched_info, ensure_ascii=False, indent=2),
            project_name=project_name,
            project_type=project_type
        )
        
        try:
            metrics_result = await self._aask(metrics_design_prompt, [ARCHITECT_BASE_SYSTEM])
            
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
                # 确保一级指标只能是固定的四个值
                if metric['一级指标'] in ['决策', '过程', '产出', '效益']:
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
    
