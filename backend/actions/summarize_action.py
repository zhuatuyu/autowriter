"""
MetaGPT标准的摘要Action
从现有tools中升级的摘要能力
"""
from typing import List
from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger
from backend.configs.llm_provider import llm
from backend.prompts import writer_expert_prompts


class SummarizeAction(Action):
    """
    标准的MetaGPT摘要Action
    用于对文本内容进行智能摘要
    """
    name: str = "SummarizeText"
    
    async def run(self, history_messages: List[Message], content: str = "") -> str:
        """
        执行摘要任务
        
        Args:
            history_messages: MetaGPT标准的消息历史
            content: 需要摘要的内容
            
        Returns:
            str: 摘要结果
        """
        logger.info(f"📝 SummarizeAction 开始执行")
        
        # 如果没有提供content，从history_messages中提取
        if not content and history_messages:
            contents = []
            for msg in history_messages:
                if hasattr(msg, 'content') and msg.content:
                    contents.append(msg.content)
            content = "\n\n".join(contents)
        
        if not content:
            return "错误：没有找到需要摘要的内容"
        
        # 使用现有的prompt模板
        prompt = writer_expert_prompts.get_summary_prompt(
            text_to_summarize=content,
            writer_name="写作专家"
        )
        
        try:
            result = await llm.acreate_text(prompt)
            logger.info(f"✅ SummarizeAction 完成: 生成了 {len(result)} 字符的摘要")
            return result
        except Exception as e:
            error_msg = f"SummarizeAction 执行失败: {e}"
            logger.error(error_msg)
            return f"# 摘要失败\n\n{error_msg}" 