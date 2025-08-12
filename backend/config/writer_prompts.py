#!/usr/bin/env python
"""
章节写作（SOP2）相关常量（替代 YAML 配置，供 section_writer_action/architect_content_action 使用）
"""

WRITER_BASE_SYSTEM = (
    "你是绩效评价报告的写作专家。你的目标是：\n"
    "1. 基于事实依据和数据支撑，撰写高质量的报告章节\n"
    "2. 严格遵循架构师制定的写作指导和检索要求\n"
    "3. 确保内容专业、准确、深入，符合绩效评价报告的标准"
)

SECTION_WRITING_PROMPT = (
    "请根据以下信息撰写报告章节：\n\n"
    "## 章节标题\n{section_title}\n\n"
    "## 写作要求与指导\n{instruction}\n\n"
    "## 相关事实依据（来自向量检索）\n{factual_basis}\n\n"
    "## 关联的绩效指标\n{metrics_text}\n\n"
    "## 📋 写作标准与质量要求\n"
    "1. 数据驱动：基于事实依据，避免空泛\n"
    "2. 结构清晰：按指导顺序组织内容\n"
    "3. 深度分析：给出原因、影响与趋势\n"
)

# 章节提示词生成模板（架构师用于拼装章节写作指导）
SECTION_PROMPT_GENERATION_TEMPLATE = (
    "{base_prompt}\n\n"
    "### 📋 具体写作指导与检索要求：\n"
    "{rag_instructions}\n\n"
    "### 🔍 RAG检索策略：\n"
    "1. 优先检索关键信息项，获取具体数据和事实\n"
    "2. 基于检索到的真实信息进行分析和论述\n"
    "3. 避免泛泛而谈，确保每个论点都有具体的数据支撑\n"
    "4. 如缺失信息，标注 \"信息待补充\"\n"
)

# 报告章节结构（SOP2 默认五章）
REPORT_SECTIONS = [
    {"title": "一、项目概述", "key": "overview", "prompt_template": "请围绕项目背景、资金与预算、实施情况、组织管理、绩效目标（表格展示）进行撰写。"},
    {"title": "二、综合绩效评价结论", "key": "conclusion", "prompt_template": "必须依据 metric_analysis_table.md 的评分结果，汇总总分与各维度分值与得分率，并引用关键opinion要点。"},
    {"title": "三、主要成效及经验", "key": "achievements", "prompt_template": "结合数据和事实，总结成效，提炼可借鉴做法。"},
    {"title": "四、存在的问题和原因分析", "key": "problems", "prompt_template": "针对扣分项逐条分析原因、依据与影响范围。"},
    {"title": "五、改进建议", "key": "suggestions", "prompt_template": "针对问题提出具体可操作建议，标注责任与预期效果。"},
]

# 章节特定配置（RAG指引）
SECTION_CONFIGURATIONS = {
    "overview": {
        "title_keywords": ["项目概述", "概述"],
        "rag_instructions": (
            "1) 项目立项背景及目的：政策依据/立项依据/目标设定\n"
            "2) 资金投入和使用情况：预算总额、来源、分配、执行进度\n"
            "3) 项目组织管理：机构、职责分工、流程制度\n"
            "4) 绩效目标：绩效目标表、指标设定、预期成果（表格展示）"
        ),
    },
    "conclusion": {
        "title_keywords": ["综合绩效评价结论", "评价结论", "绩效结论"],
        "rag_instructions": (
            "- 汇总：各维度（决策/过程/产出/效益）得分与得分率\n"
            "- 依据：引用指标表关键 opinion 要点\n"
            "- 输出：一级指标得分表（分值、得分、得分率）"
        ),
    },
    "achievements": {
        "title_keywords": ["主要成效及经验", "成效", "经验"],
        "rag_instructions": (
            "- 具体成效数据：量化成果、受益人群、对比数据\n"
            "- 成功经验总结：创新做法、管理经验、技术亮点"
        ),
    },
    "problems": {
        "title_keywords": ["存在的问题和原因分析", "问题", "原因分析"],
        "rag_instructions": (
            "- 问题识别：调研发现/数据反映/反馈意见\n"
            "- 原因分析：政策执行/管理制度/技术条件/外部环境\n"
            "- 对接指标：结合扣分项的原因、依据、影响范围"
        ),
    },
    "suggestions": {
        "title_keywords": ["改进建议", "建议"],
        "rag_instructions": (
            "- 针对性建议：责任主体/时间安排/预期效果\n"
            "- 可操作性验证：类似项目最佳实践/政策可行性"
        ),
    },
}

def GET_SECTION_KEY_BY_TITLE(section_title: str) -> str:
    title = section_title or ""
    for key, cfg in SECTION_CONFIGURATIONS.items():
        for kw in cfg.get("title_keywords", []):
            if kw in title:
                return key
    return "general"

def GET_SECTION_CONFIG(section_key: str) -> dict:
    return SECTION_CONFIGURATIONS.get(section_key, {})


