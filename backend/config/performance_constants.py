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
ENV_SCORE_LEVELS = PerformanceConfig.get_score_levels()
ENV_DIMENSION_WEIGHTS = PerformanceConfig.get_dimension_weights()
ENV_LEVEL1_INDICATORS = PerformanceConfig.get_level1_indicators()
ENV_EVIDENCE_KEYWORD_MAPPING = PerformanceConfig.get_evidence_keyword_mapping()

# =============================================================================
# 智能检索常量
# =============================================================================
ENV_QUERY_INTENT_MAPPING = PerformanceConfig.get_intelligent_search_config().get('query_intent_mapping', {})
ENV_SEARCH_MODE_WEIGHTS = PerformanceConfig.get_intelligent_search_config().get('search_mode_weights', {})

# =============================================================================
# 领域信息常量
# =============================================================================
ENV_DOMAIN_INFO = PerformanceConfig.get_domain_info()
ENV_DOMAIN_NAME = ENV_DOMAIN_INFO.get('name', '绩效分析报告')
ENV_DOMAIN_VERSION = ENV_DOMAIN_INFO.get('version', '1.0.0')

# =============================================================================
# 评价类型常量
# =============================================================================
ENV_EVALUATION_TYPES = PerformanceConfig.get_evaluation_types()

# =============================================================================
# 章节配置常量
# =============================================================================
ENV_SECTION_CONFIGURATIONS = PerformanceConfig.get_section_configurations()

# =============================================================================
# 提示词模板常量
# =============================================================================
ENV_ARCHITECT_BASE_SYSTEM = PerformanceConfig.get_architect_base_system()
ENV_PROJECT_INFO_EXTRACTION_PROMPT = PerformanceConfig.get_project_info_extraction_prompt()
ENV_RAG_KEYWORDS_GENERATION_PROMPT = PerformanceConfig.get_rag_keywords_generation_prompt()
ENV_SECTION_PROMPT_GENERATION_TEMPLATE = PerformanceConfig.get_section_prompt_generation_template()
ENV_METRICS_DESIGN_PROMPT = PerformanceConfig.get_metrics_design_prompt()

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