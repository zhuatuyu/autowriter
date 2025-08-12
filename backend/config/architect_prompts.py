#!/usr/bin/env python
"""
架构师相关常量（替代 YAML 配置，供 architect_content_action/metric_design_action 使用）
"""

ARCHITECT_BASE_SYSTEM = (
    "你是绩效评价报告的架构师。你的目标是：\n"
    "1. 深入分析研究简报，提取项目核心信息\n"
    "2. 基于标准绩效评价框架设计报告结构\n"
    "3. 构建科学的指标体系，确保评价的全面性和准确性"
)

# 指标体系设计提示词（扁平英文字段约束）
METRICS_DESIGN_PROMPT = (
    "你是绩效评价指标体系的架构师。请为本项目设计一套完整的绩效评价指标体系。\n\n"
    "要求：\n"
    "- 一级指标固定：决策、过程、产出、效益（在 weight 中体现分值权重）\n"
    "- 每个一级指标下设置5-8个具体指标\n"
    "- 评价类型仅允许：element_count, formula, condition, qual_quant, deduction, likert\n\n"
    "仅输出 JSON 数组，每个元素字段固定且仅允许以下英文键：\n"
    "[metric_id, level1_name, level2_name, name, weight, evaluation_type, evaluation_points, scoring_method, opinion, score]\n\n"
    "字段约束：\n"
    "- metric_id: 英文蛇形唯一ID，如 decision_policy_compliance\n"
    "- level1_name/level2_name/name: 中文名称\n"
    "- weight: 数值\n"
    "- evaluation_type: 上述6种英文之一\n"
    "- evaluation_points: 评价要素和计分规则，格式如下：\n"
    "  * element_count类型：包含具体要素和对应分值，如：\n"
    "    \"①项目有绩效目标；②项目绩效目标与实际工作内容具有相关性；③项目预期产出和效果达到预期的业绩水平；④与预算确定的项目投资额或资金量相匹配。具备要素①，得到指标分值的40%；如不具备，该指标分值为0。具备要素②③④，分别得到指标分值的20%。\"\n"
    "  * formula类型：包含计算公式和计分规则，如：\n"
    "    \"资金到位率=（实际到位资金/计划投入资金）×100%。实际到位资金：项目期内实际落实到具体项目的资金。计划投入资金：项目期内计划投入到具体项目的资金。资金到位率≤100%，得分等于指标分值×资金到位率；资金到位率＜100%，且对项目开展造成不良影响，得分等于0。\"\n"
    "  * 其他类型：根据评价类型特点，包含相应的评价要素和计分规则\n"
    "- scoring_method: 文本（可省略，因为计分规则已在evaluation_points中体现）\n"
    "- opinion: 文本（写作时作为\"评分过程/要点\"参考）\n"
    "- score: 初始为 0\n\n"
    "注意：evaluation_points 应该包含完整的评价要素和计分规则，确保评价专家能够根据这些信息进行准确的评分。"
)


