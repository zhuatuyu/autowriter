import yaml
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class PerformanceConfig:
    """绩效分析业务配置管理类"""
    
    _config = None
    _config_path = "config/performance_config.yaml"
    _base_config_path = None

    @classmethod
    def _deep_merge(cls, base: dict, override: dict) -> dict:
        """深度合并两个dict，override优先。"""
        if not isinstance(base, dict):
            return override
        result = dict(base)
        for k, v in (override or {}).items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = cls._deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    @classmethod
    def set_config_paths(cls, base_path: str | None, overlay_path: str | None):
        """显式设置基础配置与覆盖配置路径（后者优先）。"""
        cls._base_config_path = base_path
        if overlay_path:
            cls._config_path = overlay_path
        elif base_path:
            cls._config_path = base_path
        cls._config = None
    
    @classmethod
    def _load_config(cls):
        """加载配置文件"""
        if cls._config is None:
            try:
                import os
                # 支持通过环境变量设置 base/overlay 路径
                env_base = os.environ.get("PERF_CONFIG_BASE")
                env_overlay = os.environ.get("PERF_CONFIG_OVERLAY")
                if env_base or env_overlay:
                    cls._base_config_path = env_base or cls._base_config_path
                    if env_overlay:
                        cls._config_path = env_overlay

                # 读取基础配置
                base_cfg = {}
                base_path = cls._base_config_path or "config/performance_config.yaml"
                base_file = Path(base_path)
                if base_file.exists():
                    with open(base_file, 'r', encoding='utf-8') as bf:
                        base_cfg = yaml.safe_load(bf) or {}
                else:
                    # 若基础文件不存在且overlay就是默认路径，则强校验默认配置存在
                    if cls._config_path == base_path and not base_file.exists():
                        raise FileNotFoundError(f"配置文件不存在: {base_path}")

                # 读取覆盖配置
                overlay_cfg = {}
                overlay_file = Path(cls._config_path)
                if overlay_file.exists():
                    with open(overlay_file, 'r', encoding='utf-8') as of:
                        overlay_cfg = yaml.safe_load(of) or {}

                # 合并
                cls._config = cls._deep_merge(base_cfg, overlay_cfg)
                logger.info(
                    f"✅ 业务配置加载成功: base='{base_path}' overlay='{cls._config_path if overlay_cfg else ''}'"
                )
            except Exception as e:
                logger.error(f"❌ 业务配置加载失败: {e}")
                raise
    
    @classmethod
    def get_domain_info(cls) -> Dict[str, str]:
        """获取领域基本信息"""
        cls._load_config()
        return cls._config.get('domain_info', {})
    
    @classmethod
    def get_knowledge_graph_config(cls) -> Dict[str, Any]:
        """获取知识图谱配置"""
        cls._load_config()
        return cls._config.get('knowledge_graph', {})
    
    @classmethod
    def get_entity_types(cls) -> Dict[str, List[str]]:
        """获取实体类型定义"""
        kg_config = cls.get_knowledge_graph_config()
        return kg_config.get('entity_types', {})
    
    @classmethod
    def get_relation_types(cls) -> List[str]:
        """获取关系类型定义"""
        kg_config = cls.get_knowledge_graph_config()
        return kg_config.get('relation_types', [])
    
    @classmethod
    def get_report_structure(cls) -> List[Dict[str, Any]]:
        """获取报告结构配置"""
        cls._load_config()
        return cls._config.get('report_structure', {}).get('sections', [])
    
    @classmethod
    def get_research_directions(cls) -> Dict[str, Any]:
        """获取研究方向配置"""
        cls._load_config()
        return cls._config.get('research_directions', {})

    @classmethod
    def get_research_settings(cls) -> Dict[str, Any]:
        """获取研究流程参数配置"""
        cls._load_config()
        return cls._config.get('research_settings', {})

    @classmethod
    def get_research_decomposition_nums(cls) -> int:
        settings = cls.get_research_settings()
        return int(settings.get('decomposition_nums', 3))

    @classmethod
    def get_research_url_per_query(cls) -> int:
        settings = cls.get_research_settings()
        return int(settings.get('url_per_query', 3))
    
    @classmethod
    def get_enhancement_queries(cls) -> List[str]:
        """获取增强查询模板"""
        research_config = cls.get_research_directions()
        return research_config.get('enhancement_queries', [])
    
    @classmethod
    def get_evidence_categories(cls) -> List[Dict[str, Any]]:
        """获取证据收集类别"""
        research_config = cls.get_research_directions()
        return research_config.get('evidence_categories', [])
    
    @classmethod
    def get_evaluation_standards(cls) -> Dict[str, Any]:
        """获取评价标准配置"""
        cls._load_config()
        cfg = cls._config or {}
        val = cfg.get('evaluation_standards')
        return val if isinstance(val, dict) else {}
    
    @classmethod
    def get_score_levels(cls) -> Dict[str, Dict[str, Any]]:
        """获取评分等级定义"""
        eval_config = cls.get_evaluation_standards() or {}
        return eval_config.get('score_levels', {}) if isinstance(eval_config, dict) else {}
    
    @classmethod
    def get_dimension_weights(cls) -> Dict[str, int]:
        """获取维度权重配置"""
        eval_config = cls.get_evaluation_standards() or {}
        return eval_config.get('dimension_weights', {}) if isinstance(eval_config, dict) else {}
    
    @classmethod
    def get_level1_indicators(cls) -> List[str]:
        """获取一级指标定义"""
        eval_config = cls.get_evaluation_standards()
        return eval_config.get('level1_indicators', [])
    
    @classmethod
    def get_evidence_keyword_mapping(cls) -> Dict[str, Dict[str, List[str]]]:
        """获取证据摘要关键词映射"""
        research_config = cls.get_research_directions()
        return research_config.get('evidence_keyword_mapping', {})
    
    @classmethod
    def get_prompts(cls) -> Dict[str, str]:
        """获取提示词配置"""
        cls._load_config()
        return cls._config.get('prompts', {})

    @classmethod
    def get_research_prompts(cls) -> Dict[str, str]:
        """获取研究类提示词配置"""
        prompts = cls.get_prompts()
        return prompts.get('research', {})

    @classmethod
    def get_writer_prompts(cls) -> Dict[str, str]:
        """获取写作类提示词配置"""
        prompts = cls.get_prompts()
        return prompts.get('writer', {})

    @classmethod
    def get_evaluator_prompts(cls) -> Dict[str, str]:
        """获取评价类提示词配置（SOP1用）"""
        prompts = cls.get_prompts()
        return prompts.get('evaluator', {})

    @classmethod
    def get_writer_evaluation_prompt_template(cls) -> str:
        """获取写作类：通用指标评价提示词模板"""
        return cls.get_writer_prompts().get('evaluation_prompt_template', '')

    @classmethod
    def get_metric_prompt_spec(cls) -> dict:
        """获取指标级提示词组合规范"""
        return cls.get_writer_prompts().get('metric_prompt_spec', {})
    
    @classmethod
    def get_architect_base_system(cls) -> str:
        """获取架构师基础系统提示词"""
        prompts = cls.get_prompts()
        return prompts.get('architect_base_system', '')
    
    @classmethod
    def get_evaluation_level(cls, total_score: float) -> str:
        """根据总分获取评价等级"""
        score_levels = cls.get_score_levels()
        for level, config in score_levels.items():
            if config['min'] <= total_score <= config['max']:
                return level
        return "未知"
    
    @classmethod
    def get_intelligent_search_config(cls) -> Dict[str, Any]:
        """获取智能检索配置"""
        cls._load_config()
        return cls._config.get('intelligent_search', {})
    
    @classmethod
    def get_evaluation_types(cls) -> Dict[str, Dict[str, Any]]:
        """获取评价类型定义"""
        cls._load_config()
        return cls._config.get('evaluation_types', {})
    
    @classmethod
    def get_section_configurations(cls) -> Dict[str, Dict[str, Any]]:
        """获取章节特定配置"""
        cls._load_config()
        return cls._config.get('section_configurations', {})
    
    @classmethod
    def get_section_config(cls, section_key: str) -> Dict[str, Any]:
        """获取特定章节的配置"""
        section_configs = cls.get_section_configurations()
        return section_configs.get(section_key, {})
    
    @classmethod
    def get_rag_keywords_generation_prompt(cls) -> str:
        """获取RAG关键词生成提示词"""
        prompts = cls.get_prompts()
        return prompts.get('rag_keywords_generation', '')
    
    @classmethod
    def get_section_prompt_generation_template(cls) -> str:
        """获取章节提示词生成模板"""
        prompts = cls.get_prompts()
        return prompts.get('section_prompt_generation', '')
    
    @classmethod
    def get_metrics_design_prompt(cls) -> str:
        """获取指标体系设计提示词"""
        prompts = cls.get_prompts()
        return prompts.get('metrics_design', '')

    # ===== 研究类提示词 =====
    @classmethod
    def get_research_prompt(cls, key: str) -> str:
        research_prompts = cls.get_research_prompts()
        return research_prompts.get(key, '')

    @classmethod
    def get_writer_prompt(cls, key: str) -> str:
        writer_prompts = cls.get_writer_prompts()
        return writer_prompts.get(key, '')

    @classmethod
    def get_evaluator_prompt(cls, key: str) -> str:
        evaluator_prompts = cls.get_evaluator_prompts()
        return evaluator_prompts.get(key, '')
    
    @classmethod
    def get_fallback_keywords(cls) -> List[Dict[str, Any]]:
        """获取备用关键词"""
        research_config = cls.get_research_directions()
        return research_config.get('fallback_keywords', [])
    
    @classmethod
    def get_design_queries(cls) -> List[str]:
        """获取Architect设计查询模板"""
        research_config = cls.get_research_directions()
        return research_config.get('design_queries', [])
    
    @classmethod
    def get_section_key_by_title(cls, section_title: str) -> str:
        """根据章节标题自动匹配section key"""
        section_configs = cls.get_section_configurations()
        
        # 遍历所有章节配置，查找标题匹配
        for section_key, config in section_configs.items():
            title_keywords = config.get('title_keywords', [])
            for keyword in title_keywords:
                if keyword in section_title:
                    return section_key
        
        # 默认返回通用配置
        return "general"
    
    @classmethod
    def reload_config(cls):
        """重新加载配置（用于热更新）"""
        cls._config = None
        cls._load_config()
        logger.info("🔄 业务配置已重新加载")