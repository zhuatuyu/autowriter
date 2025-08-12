"""
绩效分析业务常量 - 类似MetaGPT的const模式
通过常量方式提供配置访问，避免重复函数调用

使用方式：
from backend.config.performance_constants import ENV_DIMENSION_WEIGHTS, ENV_SCORE_LEVELS
"""

from .performance_config import PerformanceConfig

# =============================================================================
# 知识图谱常量
# =============================================================================
ENV_ENTITY_TYPES = PerformanceConfig.get_entity_types()
ENV_RELATION_TYPES = PerformanceConfig.get_relation_types()

# =============================================================================
# 报告结构常量
# =============================================================================
ENV_REPORT_SECTIONS = PerformanceConfig.get_report_structure()

# =============================================================================
# 研究方向常量
# =============================================================================
ENV_ENHANCEMENT_QUERIES = PerformanceConfig.get_enhancement_queries()
ENV_EVIDENCE_CATEGORIES = PerformanceConfig.get_evidence_categories()
ENV_DECOMPOSITION_DIMENSIONS = PerformanceConfig.get_research_directions().get('decomposition_dimensions', [])
ENV_FALLBACK_KEYWORDS = PerformanceConfig.get_fallback_keywords()
ENV_DESIGN_QUERIES = PerformanceConfig.get_design_queries()

# =============================================================================
# 评价标准常量
# =============================================================================
try:
    ENV_SCORE_LEVELS = PerformanceConfig.get_score_levels()
except Exception:
    ENV_SCORE_LEVELS = {}
try:
    ENV_DIMENSION_WEIGHTS = PerformanceConfig.get_dimension_weights()
except Exception:
    ENV_DIMENSION_WEIGHTS = {}
try:
    ENV_LEVEL1_INDICATORS = PerformanceConfig.get_level1_indicators()
except Exception:
    ENV_LEVEL1_INDICATORS = []
ENV_EVIDENCE_KEYWORD_MAPPING = PerformanceConfig.get_evidence_keyword_mapping()

# =============================================================================
# 智能检索常量
# =============================================================================
ENV_QUERY_INTENT_MAPPING = PerformanceConfig.get_intelligent_search_config().get('query_intent_mapping', {})
ENV_SEARCH_MODE_WEIGHTS = PerformanceConfig.get_intelligent_search_config().get('search_mode_weights', {})
ENV_INTELLIGENT_TOPK = PerformanceConfig.get_intelligent_search_config().get('top_k', {})

# 可选：知识图谱关键词上限（默认5，可在 config/performance_config.yaml 配置）
try:
    _KG_CONF = PerformanceConfig.get_intelligent_search_config().get('knowledge_graph', {})
except Exception:
    _KG_CONF = {}
ENV_KG_MAX_KEYWORDS = int(_KG_CONF.get('max_keywords', 5) or 5)

# 可选：LLM输入token上限（默认120000，可在 config/performance_config.yaml 配置）
try:
    _LLM_LIMITS = PerformanceConfig.get_llm_limits()
except Exception:
    _LLM_LIMITS = {}
try:
    ENV_MAX_INPUT_TOKENS = int(_LLM_LIMITS.get('max_input_tokens', 120000) or 120000)
except Exception:
    ENV_MAX_INPUT_TOKENS = 120000

# =============================================================================
# 领域信息常量
# =============================================================================
ENV_DOMAIN_INFO = PerformanceConfig.get_domain_info()
ENV_DOMAIN_NAME = ENV_DOMAIN_INFO.get('name', '绩效分析报告')
ENV_DOMAIN_VERSION = ENV_DOMAIN_INFO.get('version', '1.0.0')

# =============================================================================
# 评价类型常量
# =============================================================================
try:
    ENV_EVALUATION_TYPES = PerformanceConfig.get_evaluation_types()
except Exception:
    ENV_EVALUATION_TYPES = {}

# =============================================================================
# 章节配置常量
# =============================================================================
ENV_SECTION_CONFIGURATIONS = PerformanceConfig.get_section_configurations()

# =============================================================================
# 提示词模板常量
# =============================================================================
ENV_ARCHITECT_BASE_SYSTEM = PerformanceConfig.get_architect_base_system()
# 不再需要LLM提取项目信息，改由项目yaml提供，移除相关提示词常量
ENV_RAG_KEYWORDS_GENERATION_PROMPT = PerformanceConfig.get_rag_keywords_generation_prompt()
ENV_SECTION_PROMPT_GENERATION_TEMPLATE = PerformanceConfig.get_section_prompt_generation_template()
ENV_METRICS_DESIGN_PROMPT = PerformanceConfig.get_metrics_design_prompt()
 
# 研究类提示词常量
ENV_COMPREHENSIVE_RESEARCH_BASE_SYSTEM = PerformanceConfig.get_research_prompt('comprehensive_research_base_system')
ENV_RESEARCH_TOPIC_SYSTEM = PerformanceConfig.get_research_prompt('research_topic_system')
ENV_SEARCH_KEYWORDS_PROMPT = PerformanceConfig.get_research_prompt('search_keywords_prompt')
ENV_DECOMPOSE_RESEARCH_PROMPT = PerformanceConfig.get_research_prompt('decompose_research_prompt')
ENV_RANK_URLS_PROMPT = PerformanceConfig.get_research_prompt('rank_urls_prompt')
ENV_WEB_CONTENT_ANALYSIS_PROMPT = PerformanceConfig.get_research_prompt('web_content_analysis_prompt')
ENV_GENERATE_RESEARCH_BRIEF_PROMPT = PerformanceConfig.get_research_prompt('generate_research_brief_prompt')
ENV_RESEARCH_DECOMPOSITION_NUMS = PerformanceConfig.get_research_decomposition_nums()
ENV_RESEARCH_URLS_PER_QUERY = PerformanceConfig.get_research_url_per_query()

# 写作类提示词常量（SOP2）
ENV_WRITER_BASE_SYSTEM = PerformanceConfig.get_writer_prompt('writer_base_system')
ENV_SECTION_WRITING_PROMPT = PerformanceConfig.get_writer_prompt('section_writing_prompt')

# 评价类提示词常量（SOP1）
ENV_EVALUATOR_BASE_SYSTEM = PerformanceConfig.get_evaluator_prompt('evaluator_base_system')
ENV_EVALUATOR_PROMPT_TEMPLATE = PerformanceConfig.get_evaluator_prompt('evaluation_prompt_template')

# 指标级提示词组合规范（与评价类型联动，放在 evaluator 下）
ENV_METRIC_PROMPT_SPEC = PerformanceConfig.get_evaluator_prompts().get('metric_prompt_spec', {})

# =============================================================================
# 辅助函数常量（保留常用的评价函数）
# =============================================================================
def ENV_GET_EVALUATION_LEVEL(total_score: float) -> str:
    """根据总分获取评价等级 - 常量化的辅助函数"""
    return PerformanceConfig.get_evaluation_level(total_score)

def ENV_GET_SECTION_CONFIG(section_key: str) -> dict:
    """获取特定章节配置 - 常量化的辅助函数"""
    return PerformanceConfig.get_section_config(section_key)

def ENV_GET_SECTION_KEY_BY_TITLE(section_title: str) -> str:
    """根据章节标题自动匹配section key - 常量化的辅助函数"""
    return PerformanceConfig.get_section_key_by_title(section_title)