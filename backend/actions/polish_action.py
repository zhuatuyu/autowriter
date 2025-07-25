"""
MetaGPT标准的润色Action
从现有tools中升级的内容润色能力
"""
from typing import List
from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger
from backend.configs.llm_provider import llm
from backend.prompts import writer_expert_prompts


class PolishAction(Action):
    """
    标准的MetaGPT润色Action
    用于对文本内容进行专业润色和优化
    """
    name: str = "PolishContent"
    
    async def run(self, history_messages: List[Message], content: str = "", style: str = "专业报告") -> str:
        """
        执行润色任务
        
        Args:
            history_messages: MetaGPT标准的消息历史
            content: 需要润色的内容
            style: 润色风格
            
        Returns:
            str: 润色后的内容
        """
        logger.info(f"✨ PolishAction 开始执行，风格: {style}")
        
        # 如果没有提供content，从history_messages中提取
        if not content and history_messages:
            contents = []
            for msg in history_messages:
                if hasattr(msg, 'content') and msg.content:
                    contents.append(msg.content)
            content = "\n\n".join(contents)
        
        if not content:
            return "错误：没有找到需要润色的内容"
        
        # 使用现有的prompt模板
        prompt = writer_expert_prompts.get_content_polish_prompt(
            content=content,
            style=style,
            writer_name="写作专家"
        )
        
        try:
            result = await llm.acreate_text(prompt)
            logger.info(f"✅ PolishAction 完成: 润色了 {len(content)} -> {len(result)} 字符")
            return result
        except Exception as e:
            error_msg = f"PolishAction 执行失败: {e}"
            logger.error(error_msg)
            return f"# 润色失败\n\n{error_msg}" 