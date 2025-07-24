"""
ChiefEditorAgent's Prompts
存放总编辑(ChiefEditorAgent)所有与LLM交互的提示词模板。
"""

def get_content_review_prompt(content: str, review_type: str, editor_name: str) -> str:
    """获取用于内容审核的Prompt"""
    return f"""
你是总编辑{editor_name}，拥有丰富的编辑经验和敏锐的质量把控能力。请对以下内容进行{review_type}：

## 内容
{content}

## 审核要求
请从以下角度进行审核：
1. **内容准确性**: 事实是否准确，逻辑是否清晰
2. **结构完整性**: 结构是否合理，层次是否分明
3. **语言表达**: 文字是否流畅，表达是否准确
4. **格式规范**: 格式是否统一，标准是否符合要求
5. **整体质量**: 是否达到发布标准

## 输出要求
请提供具体的修改建议和优化方案，包括：
- 主要问题点
- 修改建议
- 优化方案
- 质量评分

请直接输出审核结果。
"""

def get_content_polish_prompt(content: str, style: str, editor_name: str) -> str:
    """获取用于内容润色的Prompt"""
    return f"""
你是总编辑{editor_name}，请对以下内容进行专业润色，使其符合{style}的标准：

## 原始内容
{content}

## 润色要求
请进行以下优化：
1. 提升语言表达的专业性和准确性
2. 优化句式结构，增强可读性
3. 统一术语使用，确保一致性
4. 完善逻辑连接，增强连贯性
5. 调整格式，符合专业标准

## 输出要求
请直接输出润色后的内容，保持原有的核心信息和结构。
"""

def get_quality_assurance_prompt(content: str, editor_name: str) -> str:
    """获取用于质量检查的Prompt"""
    return f"""
你是总编辑{editor_name}，请对以下内容进行质量检查，并给出质量评分：

## 内容
{content}

## 检查维度
请从以下维度评分（1-10分）：
1. 内容完整性
2. 逻辑清晰度
3. 语言流畅度
4. 格式规范性
5. 专业水准

## 输出要求
请以JSON格式返回评分结果和改进建议：
```json
{{
  "scores": {{
    "content_completeness": 8,
    "logical_clarity": 7,
    "language_fluency": 9,
    "format_standardization": 8,
    "professional_level": 8
  }},
  "overall_score": 8.0,
  "improvement_suggestions": [
    "建议1",
    "建议2"
  ]
}}
```
""" 