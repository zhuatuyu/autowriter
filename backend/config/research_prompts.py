# 系统级提示
COMPREHENSIVE_RESEARCH_BASE_SYSTEM = (
    "你是一名专业的AI研究分析师和产品经理。你的目标是：\n"
    "1. 深入理解用户需求和业务背景\n"
    "2. 进行全面的市场和案例研究\n"
    "3. 生成高质量的研究简报，为后续的架构设计和内容生成提供坚实基础\n\n"
    "【事实收集原则】\n"
    "- 优先收集量化数据：具体数字、百分比、时间、金额、数量等\n"
    "- 注重政策依据：文件名称、文号、关键条款、适用范围等\n"
    "- 关注实施细节：具体措施、流程步骤、责任主体、资源配置等\n"
    "- 重视效果评估：成果数据、影响范围、受益对象、满意度等\n"
    "- 深入问题分析：具体问题、数据支撑、原因分析、影响评估等\n"
    "- 提供改进建议：可操作措施、预期效果、实施路径、资源需求等\n\n"
    "【质量要求】\n"
    "- 所有结论必须有具体事实支撑\n"
    "- 避免泛泛而谈，必须提供可验证的信息\n"
    "- 优先使用权威来源和一手资料\n"
    "- 确保信息的时效性和准确性"
)

RESEARCH_TOPIC_SYSTEM = (
    "你是一名AI研究分析师，你的研究主题是:\n#主题#\n{topic}"
)

# 关键词与问题分解/URL排序/网页分析
SEARCH_KEYWORDS_PROMPT = (
    "请根据你的研究主题，提供最多3个必要的关键词用于网络搜索。\n"
    "这些关键词应该能够帮助收集到最相关和最有价值的信息。\n"
    "你的回应必须是JSON格式，例如：[\"关键词1\", \"关键词2\", \"关键词3\"]。"
)

DECOMPOSE_RESEARCH_PROMPT = (
    "### 要求\n"
    "1. 你的研究主题和初步搜索结果展示在\"参考信息\"部分。\n"
    "2. 请基于这些信息，生成最多 {decomposition_nums} 个与研究主题相关的、更具体的调查问题。\n"
    "3. 这些问题应该能够帮助深入了解主题的不同方面，包括市场趋势、最佳实践、技术方案等。\n"
    "4. 你的回应必须是JSON格式：[\"问题1\", \"问题2\", ...]。\n\n"
    "### 事实收集重点\n"
    "生成的问题应该能够收集到以下类型的具体事实：\n"
    "- 量化数据：金额、数量、比例、时间、完成率等\n"
    "- 政策依据：文件名称、文号、关键条款、适用范围等\n"
    "- 实施细节：具体措施、流程步骤、责任主体、资源配置等\n"
    "- 效果评估：成果数据、影响范围、受益对象、满意度等\n"
    "- 问题分析：具体问题、数据支撑、原因分析、影响评估等\n"
    "- 改进建议：可操作措施、预期效果、实施路径、资源需求等\n\n"
    "### 参考信息\n{search_results}"
)

RANK_URLS_PROMPT = (
    "### 主题\n{topic}\n"
    "### 具体问题\n{query}\n"
    "### 原始搜索结果\n{results}\n"
    "### 要求\n"
    "1) 先移除不相关的搜索结果；\n"
    "2) 如果问题具有时效性，移除过时信息（当前时间 {time_stamp}）；\n"
    "3) 域名白名单强约束：只保留以下来源（非白名单一律淘汰）：\n"
    "   - *.gov.cn、*.edu.cn 及权威部委官网\n"
    "   - 权威机构/监管部门官方网站\n"
    "   - 主流权威媒体与学术数据库\n"
    "4) 在白名单结果中再按可信度与相关性排序；\n"
    "5) 仅以 JSON 数组输出排序后保留结果的索引，例如 [0, 1, 3]。"
)

WEB_CONTENT_ANALYSIS_PROMPT = (
    "### 要求\n"
    "1. 利用\"参考信息\"中的文本来回答问题\"{query}\"。\n"
    "2. 若无法直接回答但内容相关，请进行全面总结；完全不相关则回复\"不相关\"。\n"
    "3. 重点提取：关键数据、统计信息、最佳实践、指标体系、政策法规等。\n\n"
    "### 事实提取重点\n"
    "在总结内容时，请特别关注并提取以下具体事实：\n"
    "- 量化数据：具体数字、百分比、时间节点、金额、数量等\n"
    "- 政策文件：文件名称、文号、发布机构、生效时间、关键条款等\n"
    "- 实施措施：具体做法、流程步骤、技术方案、管理方法等\n"
    "- 效果成果：完成情况、达标率、受益范围、满意度等\n"
    "- 问题挑战：具体问题、数据支撑、原因分析、影响评估等\n"
    "- 经验做法：成功案例、创新举措、最佳实践、可推广经验等\n\n"
    "### 参考信息\n{content}"
)

# 研究简报（扁平JSON）
# SOP1：指标导向（突出 metric_focus）
GENERATE_RESEARCH_BRIEF_PROMPT_SOP1 = (
    "【输出格式硬性约束 - 仅输出JSON（扁平结构）】\n"
    "- 你必须仅输出一个 JSON 对象，键严格为：\n"
    "  [\"topic\",\"generated_at\",\"kb_sources\",\"overview\",\"conclusion\",\"achievements\",\"problems\",\"suggestions\",\"metric_focus\",\"policy_refs\",\"method_refs\",\"case_refs\"]。\n"
    "- allowed_web_urls: {allowed_web_urls}\n- allowed_project_docs: {allowed_project_docs}\n\n"
    "【内容质量要求 - 提高事实密度】\n"
    "- overview: 必须包含具体的项目数据（如预算金额、实施周期、主要建设内容、受益范围等）\n"
    "- achievements: 必须包含量化的成果数据（如完成率、数量、金额、时间节点等）\n"
    "- problems: 必须基于具体事实和数据，避免泛泛而谈\n"
    "- suggestions: 必须针对具体问题提出可操作的建议\n"
    "- metric_focus: 必须包含可量化的指标建议，如'项目完成率≥95%'、'资金使用合规率100%'等\n"
    "- policy_refs: 必须包含具体的政策文件名称、文号、关键条款等\n"
    "- method_refs: 必须包含具体的评价方法、标准、工具等\n"
    "- case_refs: 必须包含可参考的案例名称、来源、关键做法等\n\n"
    "【仅输出JSON示例】\n"
    "{{\n"
    "  \"topic\": \"{topic}\",\n"
    "  \"generated_at\": \"{time_stamp}\",\n"
    "  \"kb_sources\": [\"global_kg\",\"project_vector\",\"web\"],\n"
    "  \"overview\": \"...\",\n"
    "  \"conclusion\": \"...\",\n"
    "  \"achievements\": \"...\",\n"
    "  \"problems\": \"...\",\n"
    "  \"suggestions\": \"...\",\n"
    "  \"metric_focus\": \"...\",\n"
    "  \"policy_refs\": \"...\",\n"
    "  \"method_refs\": \"...\",\n"
    "  \"case_refs\": \"...\"\n"
    "}}"
)

# SOP2：章节导向（突出 structure_focus/metric_citations）
GENERATE_RESEARCH_BRIEF_PROMPT_SOP2 = (
    "【输出格式硬性约束 - 仅输出JSON（扁平结构）】\n"
    "- 你必须仅输出一个 JSON 对象，键严格为：\n"
    "  [\"topic\",\"generated_at\",\"kb_sources\",\"overview\",\"conclusion\",\"achievements\",\"problems\",\"suggestions\",\"structure_focus\",\"metric_citations\",\"policy_refs\",\"method_refs\",\"case_refs\"]。\n"
    "- allowed_web_urls: {allowed_web_urls}\n- allowed_project_docs: {allowed_project_docs}\n\n"
    "【仅输出JSON示例】\n"
    "{{\n"
    "  \"topic\": \"{topic}\",\n"
    "  \"generated_at\": \"{time_stamp}\",\n"
    "  \"kb_sources\": [\"global_kg\",\"project_vector\",\"web\"],\n"
    "  \"overview\": \"...\",\n"
    "  \"conclusion\": \"...\",\n"
    "  \"achievements\": \"...\",\n"
    "  \"problems\": \"...\",\n"
    "  \"suggestions\": \"...\",\n"
    "  \"structure_focus\": \"...\",\n"
    "  \"metric_citations\": \"...\",\n"
    "  \"policy_refs\": \"...\",\n"
    "  \"method_refs\": \"...\",\n"
    "  \"case_refs\": \"...\"\n"
    "}}"
)

def select_generate_research_brief_prompt(sop: str) -> str:
    sop = (sop or "sop1").lower()
    if sop == "sop2":
        return GENERATE_RESEARCH_BRIEF_PROMPT_SOP2
    return GENERATE_RESEARCH_BRIEF_PROMPT_SOP1

# 研究增强查询与参数

# 用于在研究简报生成前，基于主题追加若干通用增强查询（配置驱动，避免业务硬编码）
ENHANCEMENT_QUERIES = [
    "最佳实践案例和成功经验",
    "常见问题和风险因素",
    "绩效评价指标和评价方法",
    "相关的政策法规和标准规范",
]

RESEARCH_DECOMPOSITION_NUMS = 2
RESEARCH_URLS_PER_QUERY = 3

FALLBACK_KEYWORDS = [
    {"category": "项目基本信息", "keywords": ["项目名称", "项目背景", "主要目标"]},
    {"category": "资金预算", "keywords": ["预算金额", "资金来源", "支出明细"]},
]

# 研究辅助项
# 指标研究方向
METRIC_DECOMPOSITION_DIMENSIONS = [
    "决策维度：项目立项依据、政策符合性、绩效目标设定、决策程序合规性",
    "过程维度：资金管理合规性、过程监管完整性、资料归档及时性、变更管理规范性",
    "产出维度：工程建设完成率、质量达标情况、工期控制效果、成本控制成果",
    "效益维度：社会效益实现度、经济效益量化、生态效益评估、可持续性保障机制",
]
# 章节研究方向
SECTION_DECOMPOSITION_DIMENSIONS = [
    "一章-项目概述基线清单：权威政策/文号、资金与来源、工期、建设范围与规模、受益群体与口径",
    "二章-结论对齐清单：按四维度生成“分值/得分/得分率/引用的opinion要点/证据来源”的指标-结论对齐表",
    "可复核数据资产表：预算/支付/工程量/验收/移交/满意度等“表格字段定义+可追溯来源”清单",
    "四章-扣分项证据链：每条扣分→原文证据摘录→出处(文号/页码/URL)→影响范围→整改状态/空缺",
    "三章-成效与可比性：目标值vs实际值、同期/同类对照、案例可比性判据(同类型/同地域/同规模/同政策口径)",
    "五章-建议与可行性：建议-责任-时限-资源-政策可行性-预期效果-验证指标(闭环矩阵)",
    "方法与计分复算：关键公式/参数解释/数据来源/复算过程(含单位与口径)",
    "风险与不确定性：数据缺口/假设与依据/敏感性分析(参数±x%对结论影响)",
    "引用与合规规范：政策/标准/报告引用均要求“全称+文号/版次+具体条款/页码/URL可追溯”",
]

EVIDENCE_CATEGORIES = [
    {"category": "项目基本信息", "keywords": ["项目名称", "项目背景", "主要目标"]},
    {"category": "资金预算", "keywords": ["预算金额", "资金来源", "支出明细"]},
    {"category": "实施内容", "keywords": ["实施方案", "技术措施", "管理流程"]},
    {"category": "绩效指标", "keywords": ["评价指标", "成果产出", "效益分析"]},
]
EVIDENCE_KEYWORD_MAPPING = {
    "预算资金数据": {"keywords": ["预算", "资金", "金额", "支出", "拨款"]},
    "目标指标设定": {"keywords": ["目标", "指标", "计划", "预期", "设定"]},
    "实施管理措施": {"keywords": ["实施", "管理", "措施", "方案", "流程"]},
    "实施效果数据": {"keywords": ["效果", "成果", "成效", "数据", "统计"]},
}

# LLM输入长度限制
MAX_INPUT_TOKENS = 120000


