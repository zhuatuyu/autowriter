"""
写作相关工具集
存放所有与内容创作、处理、分析相关的可重用工具 (Actions)
这些工具是标准化的，可供任何有需要的Agent"租用"。
"""
from typing import List
from metagpt.actions import Action
from metagpt.schema import Message
from backend.services.llm_provider import llm
from backend.services.llm.prompts import writer_expert_prompts


class PolishContentAction(Action):
    """
    一个用于润色和优化文本内容的工具。
    输入：需要润色的文本内容。
    输出：经过专业润色和风格优化的文本。
    """
    name: str = "PolishContent"

    async def run(self, history_messages: List[Message], content: str = "", style: str = "专业报告") -> str:
        """执行内容润色 - 符合MetaGPT标准"""
        # 如果没有直接提供content，从history_messages中提取
        if not content and history_messages:
            contents = []
            for msg in history_messages:
                if hasattr(msg, 'content') and msg.content:
                    contents.append(msg.content)
            content = "\n\n".join(contents)
        
        if not content:
            return "错误：没有找到需要润色的内容"
            
        prompt = writer_expert_prompts.get_content_polish_prompt(content, style, "写作专家")
        try:
            return await llm.acreate_text(prompt)
        except Exception as e:
            return f"内容润色失败: {e}"


class ReviewContentAction(Action):
    """
    一个用于从多个维度审核内容质量的工具。
    输入：需要审核的文本内容。
    输出：一份包含评分、优缺点和具体修改建议的JSON格式审核报告。
    """
    name: str = "ReviewContent"

    async def run(self, history_messages: List[Message], content: str = "") -> str:
        """执行内容审核 - 符合MetaGPT标准"""
        # 如果没有直接提供content，从history_messages中提取
        if not content and history_messages:
            contents = []
            for msg in history_messages:
                if hasattr(msg, 'content') and msg.content:
                    contents.append(msg.content)
            content = "\n\n".join(contents)
        
        if not content:
            return '{"error": "没有找到需要审核的内容"}'
            
        prompt = writer_expert_prompts.get_quality_review_prompt(content, "写作专家")
        try:
            return await llm.acreate_text(prompt)
        except Exception as e:
            return f'{{"error": "审核失败: {e}"}}'

class SummarizeTextAction(Action):
    """
    一个用于对长文本进行总结和提炼的工具。
    输入：需要总结的文本。
    输出：一段精准、连贯、流畅的摘要文本。
    """
    name: str = "SummarizeText"
    
    async def run(self, history_messages: List[Message], text_to_summarize: str = "") -> str:
        """执行文本总结 - 符合MetaGPT标准"""
        # 如果没有直接提供text_to_summarize，从history_messages中提取
        if not text_to_summarize and history_messages:
            contents = []
            for msg in history_messages:
                if hasattr(msg, 'content') and msg.content:
                    contents.append(msg.content)
            text_to_summarize = "\n\n".join(contents)
        
        if not text_to_summarize:
            return "错误：没有找到需要总结的文本内容"
            
        # 复用我们之前创建的summary_tool的核心逻辑
        from backend.tools.summary_tool import summary_tool
        return await summary_tool.run(text_to_summarize) 