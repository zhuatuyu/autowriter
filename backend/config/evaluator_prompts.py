#!/usr/bin/env python
"""
指标评价（SOP1）相关常量（替代 YAML 配置，供 metric_evaluator_action 使用）
"""

EVALUATOR_BASE_SYSTEM = (
    "你是绩效指标统一评价专家。你的目标是：\n"
    "1. 基于检索到的事实依据，对每个指标进行客观评价与计分\n"
    "2. 严格遵循指标的评价类型与计分方法\n"
    "3. 仅输出结构化 JSON，保证 score/opinion 可被程序解析；禁止输出包裹键（如 result/evaluation/data 等）和数组"
)

EVALUATION_PROMPT_TEMPLATE = (
    "【格式硬性约束 - 仅输出JSON】\n"
    "- 你必须仅输出一个 JSON 对象，且键严格为：score 与 opinion。不得包含任何其他键。\n"
    "- score: 必须是数值(0-100)；不得加引号、不得带百分号、不得为字符串。\n"
    "- opinion: 必须是字符串。按下文的'评价意见撰写要求'组织内容。\n"
    "- 严禁：数组/列表；外层包裹键（如 result/evaluation/data 等）；示例说明；多段JSON；任何额外字符。\n"
    "- 禁止输出任何Markdown、代码块围栏（```）或前后缀文本。\n"
    "- 若事实依据不足，也必须输出合法JSON，并在 opinion 中说明依据不足的原因。\n\n"
    "请基于以下事实依据，对指标进行\"{evaluation_type}\"方式的专业评价与计分。\n\n"
    "【评价要点】\n{evaluation_points}\n\n"
    "【事实依据（RAG检索）】\n{facts}\n\n"
    "【评分方法】\n{scoring_method}\n\n"
    "【类型说明】\n{type_description}\n\n"
    "【评分指导】\n{scoring_guidance}\n\n"
    "【评价意见撰写要求】\n{opinion_requirements}\n\n"
    "请严格按照\"{evaluation_type}\"的规则执行，返回唯一JSON对象（示例格式）：\n"
    "{{\n  \"score\": 80.0,\n  \"opinion\": \"……不包含最终结论性措辞，仅呈现评价依据与过程。\"\n}}\n\n"
    "【再次强调 - 仅输出JSON】\n- 最终回复只允许包含上述 JSON 对象；不得包含除 JSON 外的任何字符（包括包裹键、数组、说明文本、Markdown、代码块围栏）。"
)

# 指标级提示词组合规范（中文序号枚举）
METRIC_PROMPT_SPEC = {
    "default": {
        "points_intro": "评价要点：",
        "point_bullet": "① ",
        "scoring_method_intro": "评分方法：",
        "max_points": 10,
    },
    "by_evaluation_type": {
        "element_count": {
            "points_intro": "评价要素：",
            "point_bullet": "① ",
            "scoring_method_intro": "计分规则：",
        },
        "formula": {
            "points_intro": "计算要求：",
            "point_bullet": "① ",
            "scoring_method_intro": "计算方法：",
        },
        "condition": {
            "points_intro": "判断条件：",
            "point_bullet": "① ",
            "scoring_method_intro": "判定标准：",
        },
        "qual_quant": {
            "points_intro": "评价要求：",
            "point_bullet": "① ",
            "scoring_method_intro": "权重与合成方法：",
        },
        "deduction": {
            "points_intro": "扣分标准：",
            "point_bullet": "① ",
            "scoring_method_intro": "扣分方法：",
        },
        "likert": {
            "points_intro": "调查要求：",
            "point_bullet": "① ",
            "scoring_method_intro": "得分计算方法：",
        },
    },
}


