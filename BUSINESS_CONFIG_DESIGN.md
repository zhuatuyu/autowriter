# 🎯 绩效分析业务配置化方案

## 📋 配置文件结构设计

### 1. `config/performance_config.yaml` - 核心业务配置

```yaml
# =============================================================================
# 绩效分析报告业务配置文件
# 通过修改此文件可以驱动整个业务流程，无需修改代码
# =============================================================================

# 领域基本信息
domain_info:
  name: "绩效分析报告"
  description: "财政项目绩效评价报告生成系统"
  version: "1.0.0"

# =============================================================================
# 知识图谱领域配置 - 用于知识图谱构建和推理
# =============================================================================
knowledge_graph:
  # 实体类型定义
  entity_types:
    项目:
      - "项目名称"
      - "项目类型"
      - "实施地点"
      - "资金规模"
    指标体系:
      - "决策指标"
      - "过程指标"
      - "产出指标"
      - "效益指标"
    具体指标:
      - "指标名称"
      - "计算方法"
      - "目标值"
      - "权重"
    政策法规:
      - "法规名称"
      - "适用范围"
      - "发布机构"
      - "生效时间"
    最佳实践:
      - "实践名称"
      - "适用场景"
      - "实施要点"
      - "预期效果"
    问题案例:
      - "问题类型"
      - "原因分析"
      - "解决方案"
      - "改进建议"
    行业类型:
      - "基础设施"
      - "公益事业"
      - "民生保障"
      - "环境治理"
  
  # 关系类型定义
  relation_types:
    - "包含"
    - "属于"
    - "适用于"
    - "遵循"
    - "参考"
    - "导致"
    - "解决"
    - "改进"
    - "关联"
    - "影响"

# =============================================================================
# 报告结构配置 - 用于架构师设计报告结构
# =============================================================================
report_structure:
  # 标准章节配置
  sections:
    - title: "一、项目概述"
      key: "overview"
      prompt_template: |
        请围绕以下方面详细描述项目概况：
        1. 项目立项背景及目的、项目主要内容
        2. 资金投入和使用情况、项目实施情况
        3. 项目组织管理
        4. 项目绩效目标：通过知识库搜索绩效目标表复制相关内容，务必以表格形式展示项目绩效指标
      keywords:
        - "项目背景与目标"
        - "资金与预算"
        - "实施方案"
        - "效果与成效"
    
    - title: "二、综合绩效评价结论"
      key: "conclusion"
      prompt_template: |
        请基于对项目决策、过程、产出和效益四个维度的全面绩效分析，给出项目的综合评价结论。
        应包含项目总得分、评价等级，并务必以表格形式清晰展示各一级指标（决策、过程、产出、效益）的计划分值、实际得分和得分率
      keywords:
        - "效果与成效"
        - "评价指标"
        - "绩效得分"
    
    - title: "三、主要成效及经验"
      key: "achievements"
      prompt_template: |
        请详细总结项目实施过程中所取得的各项主要成效，需结合具体数据和事实进行阐述。
        同时，提炼出项目在政策执行、资金管理、部门协同、服务优化等方面可供其他地区或类似项目借鉴的成功经验和有效做法
      keywords:
        - "效果与成效"
        - "实施方案"
        - "成功案例"
    
    - title: "四、存在的问题和原因分析"
      key: "problems"
      prompt_template: |
        请根据调研（如问卷调查、访谈）和数据分析，客观、准确地指出项目在实施过程中存在的主要问题。
        对于每个识别出的问题，都应深入剖析其产生的内外部原因
      keywords:
        - "风险与挑战"
        - "问题分析"
        - "原因调查"
    
    - title: "五、改进建议"
      key: "suggestions"
      prompt_template: |
        针对在'存在的问题和原因分析'部分指出的各项主要问题，请逐条提出具体的、有针对性的、可操作的改进建议。
        建议应明确改进方向、责任主体和预期效果
      keywords:
        - "改进措施"
        - "最佳实践"
        - "政策建议"

# =============================================================================
# 研究方向配置 - 用于综合研究Action
# =============================================================================
research_directions:
  # 网络研究增强查询模板
  enhancement_queries:
    - "最佳实践案例和成功经验"
    - "常见问题和风险因素"
    - "绩效评价指标和评价方法"
    - "相关的政策法规和标准规范"
  
  # 分解研究问题的维度
  decomposition_dimensions:
    - "决策维度分析"
    - "过程维度分析" 
    - "产出维度分析"
    - "效益维度分析"
  
  # 证据收集类别
  evidence_categories:
    - category: "项目基本信息"
      keywords: ["项目名称", "项目背景", "主要目标"]
    - category: "资金预算"
      keywords: ["预算金额", "资金来源", "支出明细"]
    - category: "实施内容"
      keywords: ["实施方案", "技术措施", "管理流程"]
    - category: "绩效指标"
      keywords: ["评价指标", "成果产出", "效益分析"]

# =============================================================================
# 评价标准配置 - 用于写作专家评价和打分
# =============================================================================
evaluation_standards:
  # 评价等级定义
  score_levels:
    优秀:
      min: 90
      max: 100
      description: "项目实施非常成功，各项指标均达到或超过预期"
    良好:
      min: 80
      max: 89
      description: "项目实施比较成功，主要指标达到预期"
    一般:
      min: 70
      max: 79
      description: "项目基本完成，但部分指标有待改进"
    及格:
      min: 60
      max: 69
      description: "项目勉强完成，存在较多问题"
    较差:
      min: 0
      max: 59
      description: "项目实施效果不佳，需要重大改进"
  
  # 四个维度权重配置
  dimension_weights:
    决策: 20  # 决策维度权重
    过程: 25  # 过程维度权重
    产出: 30  # 产出维度权重
    效益: 25  # 效益维度权重

# =============================================================================
# 提示词配置 - 系统级提示词模板
# =============================================================================
prompts:
  # 架构师基础系统提示词
  architect_base_system: |
    你是绩效评价报告的架构师。你的目标是：
    1. 深入分析研究简报，提取项目核心信息
    2. 基于标准绩效评价框架设计报告结构
    3. 构建科学的指标体系，确保评价的全面性和准确性
  
  # 项目信息提取提示词
  project_info_extraction: |
    你是绩效评价报告的架构师。请从以下研究简报中提取项目的核心信息，用于后续基于标准模板的报告结构设计。
    
    研究简报：
    {research_brief}
    
    请返回JSON格式，包含以下字段：
    1. project_name: 项目全称
    2. project_type: 项目类型
    3. budget_amount: 预算金额
    4. implementation_period: 实施周期
    5. key_objectives: 主要目标列表
    6. performance_indicators: 绩效指标列表

# =============================================================================
# 智能检索配置 - 用于智能检索服务
# =============================================================================
intelligent_search:
  # 查询意图分析配置
  query_intent_mapping:
    performance: ["绩效评价", "指标体系", "效益", "风险"]
    reasoning: ["关系推理", "关联", "因果", "影响"]
    exploration: ["如何", "探索", "详细", "深入"]
    general: ["其他"]
  
  # 检索模式权重配置
  search_mode_weights:
    vector: 0.6      # 向量检索权重
    knowledge_graph: 0.4  # 知识图谱权重
```

### 2. `backend/config/performance_config.py` - 配置管理类

```python
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
    def reload_config(cls):
        """重新加载配置（用于热更新）"""
        cls._config = None
        cls._load_config()
        logger.info("🔄 业务配置已重新加载")
```

## 🚀 实施步骤方案

我建议按以下顺序逐步实施，**每个步骤都需要您的同意才能开始**：

### **第一步：创建配置基础设施**
1. 创建 `config/performance_config.yaml` 配置文件
2. 创建 `backend/config/performance_config.py` 配置管理类
3. 验证配置加载机制

### **第二步：按模块重构（需逐个确认）**
1. **knowledge_graph.py** - 替换硬编码的实体和关系类型
2. **architect_action.py** - 替换硬编码的报告结构和提示词
3. **research_action.py** - 替换硬编码的研究方向配置
4. **writer_action.py** - 替换硬编码的评价标准
5. **其他相关文件** - 统一配置访问方式

### **第三步：验证和优化**
1. 运行完整测试验证功能不变
2. 提供配置文件文档和示例
3. 可选：实现配置热重载机制

## 🎯 方案优势

1. **业务驱动**：修改配置即可调整业务规则，无需改代码
2. **统一管理**：所有业务配置集中在一个文件中
3. **易于维护**：配置文件版本控制，变更可追溯
4. **灵活扩展**：可以为不同领域创建不同配置文件
5. **MetaGPT兼容**：与现有config2.yaml风格保持一致

请您确认这个方案是否符合您的预期？如果同意，我们可以开始第一步的实施。