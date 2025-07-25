"""
MetaGPT标准的写作Action
从WriterExpert中抽离的核心写作能力
"""
from typing import List
from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger
from backend.configs.llm_provider import llm
from backend.prompts import writer_expert_prompts


class WriteContentAction(Action):
    """
    标准的MetaGPT写作Action
    用于创建各种类型的文档内容
    """
    name: str = "WriteContent"
    
    async def run(self, history_messages: List[Message], instruction: str = "", context_str: str = "") -> str:
        """
        执行写作任务
        
        Args:
            history_messages: MetaGPT标准的消息历史
            instruction: 写作指令
            context_str: 上下文信息
            
        Returns:
            str: 生成的内容
        """
        logger.info(f"🖋️ WriteContentAction 开始执行: {instruction}")
        
        # 如果没有提供context_str，从history_messages中提取
        if not context_str and history_messages:
            contents = []
            for msg in history_messages:
                if hasattr(msg, 'content') and msg.content:
                    contents.append(f"### 来源: {getattr(msg, 'sent_from', '未知')}\n\n{msg.content}")
            context_str = "\n\n---\n\n".join(contents)
        
        # 使用现有的prompt模板
        prompt = writer_expert_prompts.get_content_creation_prompt(
            topic=instruction,
            outline=context_str,
            writer_name="写作专家"
        )
        
        try:
            result = await llm.acreate_text(prompt)
            logger.info(f"✅ WriteContentAction 完成: 生成了 {len(result)} 字符的内容")
            return result
        except Exception as e:
            error_msg = f"WriteContentAction 执行失败: {e}"
            logger.error(error_msg)
            return f"# 写作失败\n\n{error_msg}" 