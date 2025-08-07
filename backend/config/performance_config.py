import yaml
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class PerformanceConfig:
    """绩效分析业务配置管理类"""
    
    _config = None
    _config_path = "config/performance_config.yaml"
    
    @classmethod
    def _load_config(cls):
        """加载配置文件"""
        if cls._config is None:
            try:
                config_file = Path(cls._config_path)
                if not config_file.exists():
                    raise FileNotFoundError(f"配置文件不存在: {cls._config_path}")
                
                with open(config_file, 'r', encoding='utf-8') as f:
                    cls._config = yaml.safe_load(f)
                
                logger.info(f"✅ 业务配置加载成功: {cls._config_path}")
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
        return cls._config.get('evaluation_standards', {})
    
    @classmethod
    def get_score_levels(cls) -> Dict[str, Dict[str, Any]]:
        """获取评分等级定义"""
        eval_config = cls.get_evaluation_standards()
        return eval_config.get('score_levels', {})
    
    @classmethod
    def get_dimension_weights(cls) -> Dict[str, int]:
        """获取维度权重配置"""
        eval_config = cls.get_evaluation_standards()
        return eval_config.get('dimension_weights', {})
    
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
    def get_architect_base_system(cls) -> str:
        """获取架构师基础系统提示词"""
        prompts = cls.get_prompts()
        return prompts.get('architect_base_system', '')
    
    @classmethod
    def get_project_info_extraction_prompt(cls) -> str:
        """获取项目信息提取提示词"""
        prompts = cls.get_prompts()
        return prompts.get('project_info_extraction', '')
    
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