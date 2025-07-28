"""
WriterExpert's Actions
"""
from metagpt.actions import Action
from metagpt.llm import LLM
from metagpt.provider.base_llm import BaseLLM
from typing import List
from metagpt.schema import Message


class WriteContent(Action):
    """
    Action to write content based on instructions.
    """
    name: str = "WriteContent"

    async def run(self, instruction: str, context_str: str = "") -> str:

        
        prompt = f"""# 指令：内容创作

**角色**: 你是资深内容创作者 **张翰**。

**任务**: 根据以下要求，基于提供的上下文，撰写一段高质量、专业、结构清晰的 **根据指令写作** 章节内容。

## 写作要求
{instruction}

## 上下文参考
{context_str}

请直接开始撰写内容，确保逻辑连贯，语言流畅。
"""
        return await self.llm.aask(prompt)


class SummarizeText(Action):
    """
    Action to summarize text.
    """
    name: str = "SummarizeText"

    async def run(self, source_content: str) -> str:
        prompt = f"""# 指令：文本总结

请将以下文本内容进行总结，提炼核心观点和关键信息。要求总结内容简洁、准确、全面。

**待总结文本**:
---
{source_content}
---

请输出总结结果。
"""
        return await self.llm.aask(prompt)


class PolishContent(Action):
    """
    Action to polish content.
    """
    name: str = "PolishContent"

    async def run(self, source_content: str) -> str:
        prompt = f"""# 指令：内容润色

请对以下文本进行润色，使其语言更流畅、表达更专业、更具说服力。可以调整语序、更换词汇、优化句式，但不要改变原文的核心意思。

**待润色文本**:
---
{source_content}
---

请输出润色后的结果。
"""
        return await self.llm.aask(prompt)


class ReviewContent(Action):
    """
    Action to review content.
    """
    name: str = "ReviewContent"

    async def run(self, source_content: str) -> str:
        prompt = f"""# 指令：内容审核

请从以下几个维度，对提供的文本内容进行审核，并给出具体的修改建议：
1.  **事实准确性**: 内容是否存在事实错误或误导性信息？
2.  **逻辑连贯性**: 内容的逻辑是否清晰、连贯，论证是否有力？
3.  **语言表达**: 语言是否流畅、专业，是否存在语法错误或不当用词？
4.  **完整性**: 内容是否完整地回应了主题，有无遗漏关键信息？

**待审核文本**:
---
{source_content}
---

请以列表形式，输出你的审核意见和修改建议。
"""
        return await self.llm.aask(prompt)