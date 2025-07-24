"""
Summary Tool
提供一个可复用的文本摘要工具，供所有智能体使用。
"""
from backend.services.llm_provider import llm
from metagpt.logs import logger

class SummaryTool:
    def __init__(self):
        # llm_provider 实例已经包含了默认和摘要专用的模型
        self.llm_provider = llm

    def _get_summary_prompt(self, text_content: str, max_length: int = 2000) -> str:
        """获取用于生成摘要的Prompt"""
        return f"""
# 指令：生成文本摘要

请你将以下文本内容，精准地总结成一段不超过 {max_length} 个字符的摘要。

## 要求
1.  **核心内容**: 必须包含文本最关键的主题、发现和结论。
2.  **关键信息**: 提取文本中的关键数据、实体或重要观点。
3.  **语言精练**: 使用简洁、专业、中立的语言。
4.  **保持中立**: 不要添加原文没有的观点或评价。
5.  **格式**: 直接输出摘要文本，无需任何标题或前言。

## 原始文本
---
{text_content[:8000]} 
---

请立即生成摘要。
"""

    async def run(self, text_content: str, max_length: int = 500) -> str:
        """
        执行文本摘要
        :param text_content: 需要摘要的文本内容
        :param max_length: 摘要的最大长度
        :return: 生成的摘要文本
        """
        if not text_content or not text_content.strip():
            logger.warning("文本内容为空，无法生成摘要。")
            return "原文内容为空，无法生成摘要。"

        prompt = self._get_summary_prompt(text_content, max_length)
        
        try:
            # 明确指定使用摘要专用LLM
            summary = await self.llm_provider.acreate_text(prompt, use_summary_llm=True)
            return summary.strip()
        except Exception as e:
            logger.error(f"调用LLM生成摘要时失败: {e}", exc_info=True)
            # 提供一个简单的截断作为备用方案
            return f"摘要生成失败。原文前200字符预览：{text_content[:200]}..."

# 创建一个全局工具实例，方便调用
summary_tool = SummaryTool() 