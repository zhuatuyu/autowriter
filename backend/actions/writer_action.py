"""
WriterExpert's Actions
"""
from metagpt.actions import Action
from metagpt.llm import LLM
from metagpt.provider.base_llm import BaseLLM
from typing import List
from metagpt.schema import Message
from metagpt.utils.project_repo import ProjectRepo


class WriteContent(Action):
    """
    Action to write content based on topic and summary.
    """
    name: str = "WriteContent"

    async def run(self, topic: str, summary: str, project_repo: ProjectRepo = None) -> str:
        prompt = f"""# 指令：内容创作

**角色**: 你是资深内容创作者 **张翰**。

**任务**: 根据以下主题和总结，撰写一段高质量、专业、结构清晰的报告内容。

## 主题
{topic}

## 内容总结
{summary}

请基于以上信息，撰写详细的报告内容，确保逻辑连贯，语言流畅，结构清晰。
"""
        content = await self.llm.aask(prompt)
        
        # 如果提供了project_repo，保存内容到文件
        if project_repo:
            filename = f"写作报告_{topic.replace(' ', '_')}.md"
            save_path = project_repo.workdir / "reports" / filename
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
        return content


class SummarizeText(Action):
    """
    Action to summarize text.
    """
    name: str = "SummarizeText"

    async def run(self, content: str) -> str:
        prompt = f"""# 指令：文本总结

请将以下文本内容进行总结，提炼核心观点和关键信息。要求总结内容简洁、准确、全面。

**待总结文本**:
---
{content}
---

请输出总结结果。
"""
        return await self.llm.aask(prompt)


class PolishContent(Action):
    """
    Action to polish content.
    """
    name: str = "PolishContent"

    async def run(self, content: str, project_repo: ProjectRepo = None) -> str:
        prompt = f"""# 指令：内容润色

请对以下文本进行润色，使其语言更流畅、表达更专业、更具说服力。可以调整语序、更换词汇、优化句式，但不要改变原文的核心意思。

**待润色文本**:
---
{content}
---

请输出润色后的结果。
"""
        polished_content = await self.llm.aask(prompt)
        
        # 如果提供了project_repo，保存润色后的内容
        if project_repo:
            filename = f"润色内容_{hash(content) % 10000}.md"
            save_path = project_repo.workdir / "reports" / filename
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(polished_content)
            
        return polished_content


class ReviewContent(Action):
    """
    Action to review content.
    """
    name: str = "ReviewContent"

    async def run(self, content: str, project_repo: ProjectRepo = None) -> str:
        prompt = f"""# 指令：内容审核与最终完善

请从以下几个维度，对提供的文本内容进行审核，并输出最终完善的版本：
1.  **事实准确性**: 内容是否存在事实错误或误导性信息？
2.  **逻辑连贯性**: 内容的逻辑是否清晰、连贯，论证是否有力？
3.  **语言表达**: 语言是否流畅、专业，是否存在语法错误或不当用词？
4.  **完整性**: 内容是否完整地回应了主题，有无遗漏关键信息？

**待审核文本**:
---
{content}
---

请直接输出经过审核和完善后的最终版本内容。
"""
        final_content = await self.llm.aask(prompt)
        
        # 如果提供了project_repo，保存最终内容
        if project_repo:
            filename = f"最终报告_{hash(content) % 10000}.md"
            save_path = project_repo.workdir / "reports" / filename
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
        return final_content