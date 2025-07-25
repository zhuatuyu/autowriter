"""
WriterExpertAgent's Prompts
存放写作专家(WriterExpertAgent)所有与LLM交互的提示词模板。
"""

def get_content_creation_prompt(topic: str, outline: str, writer_name: str) -> str:
    """获取用于内容创作的Prompt"""
    return f"""
你是写作专家{writer_name}，请根据以下主题和大纲创作专业内容。

## 创作要求
主题：{topic}
大纲：{outline}

## 创作要求
请创作符合以下要求的内容：
1. 结构清晰，层次分明
2. 语言专业，表达准确
3. 逻辑连贯，论证有力
4. 内容丰富，信息充实
5. 符合学术或专业标准

## 输出格式
请直接输出创作的内容，使用Markdown格式，包含：
- 清晰的标题结构
- 段落分明的内容
- 适当的引用和说明
- 专业的语言表达

请直接输出创作的内容。
"""

def get_content_polish_prompt(content: str, style: str, writer_name: str) -> str:
    """获取用于内容润色和优化的Prompt (原ChiefEditor能力)"""
    return f"""
你是写作专家{writer_name}，同时也是一位经验丰富的总编辑。请对以下内容进行专业润色，使其符合'{style}'的标准。

## 原始内容
---
{content}
---

## 润色要求
请进行以下优化：
1.  **提升专业性**: 提升语言表达的专业度和准确性。
2.  **增强可读性**: 优化句式结构，使其更流畅、易于理解。
3.  **确保一致性**: 统一术语和关键概念的使用。
4.  **强化逻辑**: 完善逻辑连接，使论证更有力、更连贯。
5.  **调整格式**: 优化Markdown格式，使其符合专业报告的排版标准。

## 输出要求
请直接输出润色后的完整内容，不要添加额外的解释或评论。
"""

def get_quality_review_prompt(content: str, writer_name: str) -> str:
    """获取用于质量审核的Prompt (原ChiefEditor能力)"""
    return f"""
你是写作专家{writer_name}，同时也是一位经验丰富的总编辑。请对以下内容进行最终的质量审核。

## 待审内容
---
{content}
---

## 审核要求
请从以下角度进行审核，并提供具体的修改建议：
1.  **内容准确性**: 事实、数据是否准确无误？逻辑是否清晰、不存在矛盾？
2.  **结构完整性**: 结构是否合理？层次是否分明？是否完整覆盖了主题？
3.  **语言表达**: 文字是否流畅、专业？是否存在语病或表达不当之处？
4.  **格式规范**: 格式是否统一？引用、图表等是否符合标准？
5.  **整体质量**: 内容是否达到可交付的专业标准？

## 输出格式
请以JSON格式返回审核结果：
```json
{{
  "overall_score": 8.5,
  "strengths": "逻辑清晰，论据充分。",
  "weaknesses": "部分章节的语言表达略显口语化，第三章的格式需要调整。",
  "suggestions": [
    "建议将第三章第二节的段落进行拆分，增加可读性。",
    "建议统一全文中'数字化采购'和'电子化采购'的术语使用。"
  ]
}}
```
"""


def get_summary_prompt(text_to_summarize: str, writer_name: str) -> str:
    """获取用于生成摘要的Prompt"""
    return f"""
你是写作专家{writer_name}，请将以下文本内容，精准地总结成一段连贯、流畅的摘要。

## 要求
1.  **核心内容**: 必须包含文本最关键的主题、发现和结论。
2.  **关键信息**: 提取文本中的关键数据、实体或重要观点。
3.  **语言精练**: 使用简洁、专业、中立的语言。
4.  **保持中立**: 不要添加原文没有的观点或评价。
5.  **格式**: 直接输出摘要文本，无需任何标题或前言。

## 待总结的文本
---
{text_to_summarize}
---

请立即生成摘要。
"""


def get_section_writing_prompt(section_title: str, requirements: str, context: str, writer_name: str) -> str:
    """获取用于章节写作的Prompt"""
    return f"""
你是写作专家{writer_name}，请根据要求撰写特定章节。

## 章节信息
章节标题：{section_title}
写作要求：{requirements}
上下文信息：{context}

## 写作要求
请撰写符合以下要求的内容：
1. 紧扣章节主题
2. 满足写作要求
3. 与上下文保持一致
4. 语言专业规范
5. 结构清晰合理

## 输出格式
请直接输出章节内容，使用Markdown格式。
""" 

def get_tool_selection_prompt(instruction: str, tools_description: str, writer_name: str) -> str:
    """获取用于从工具箱中选择最合适工具的Prompt"""
    return f"""
作为写作专家{writer_name}，我收到了一个任务指令，需要从我的工具箱中选择最合适的工具来完成。

## 我的任务指令
---
{instruction}
---

## 我的工具箱
我拥有以下工具，每个工具都有其特定的用途：
---
{tools_description}
---

## 决策任务
请分析我的任务指令，并从我的工具箱中，选择一个且仅一个最匹配的工具来执行。

## 输出格式
请严格按照以下格式返回你选择的工具的名称（tool_name），不要包含任何其他解释或多余的文字。
```json
{{
  "tool_name": "这里填写你选择的工具的名称"
}}
```
""" 