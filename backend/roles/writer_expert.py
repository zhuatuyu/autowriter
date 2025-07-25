"""
写作专家Agent - 张翰 (React模式-内置决策核心)
负责报告内容撰写和文本创作
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import json
import re

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger

from .base import BaseAgent
from backend.configs.llm_provider import llm
# 导入公共工具
from backend.tools.writing_tools import PolishContentAction, ReviewContentAction, SummarizeTextAction

# 导入新的Prompt模块
from backend.prompts import writer_expert_prompts


class WritingAction(Action):
    """
    一项私有的、核心的写作能力。
    输入：明确的写作指令，包含主题、章节、要求等。
    输出：一段完整、高质量的报告章节草稿。
    """
    name: str = "WriteContent"
    
    async def run(self, history_messages: List[Message], instruction: str = "", context_str: str = "") -> str:
        """执行内容写作 - 符合MetaGPT标准"""
        # 从history_messages中提取上下文（如果没有通过context_str提供）
        if not context_str and history_messages:
            contexts = []
            for msg in history_messages:
                if hasattr(msg, 'content') and msg.content:
                    contexts.append(msg.content)
            context_str = "\n\n".join(contexts)
        
        # 如果没有明确的instruction，尝试从最新消息中获取
        if not instruction and history_messages:
            latest_msg = history_messages[-1]
            if hasattr(latest_msg, 'content'):
                instruction = latest_msg.content[:200]  # 取前200字符作为指令
        
        prompt = writer_expert_prompts.get_section_writing_prompt(
            section_title="根据指令写作", 
            requirements=instruction, 
            context=context_str, 
            writer_name="张翰"
        )
        try:
            return await llm.acreate_text(prompt)
        except Exception as e:
            logger.error(f"内容写作失败: {e}")
            return f"写作失败: {str(e)}"


class WriterExpertAgent(BaseAgent):
    """
    ✍️ 写作专家（张翰） - 具备内置决策能力的智能内容专家
    """
    def __init__(self, agent_id: str, session_id: str, workspace_path: str, memory_manager=None):
        super().__init__(
            agent_id=agent_id,
            session_id=session_id,
            workspace_path=workspace_path,
            memory_manager=memory_manager,
            profile="写作专家",
            goal="根据指令，智能地使用各种工具，完成高质量的内容创作、分析与优化任务"
        )
        
        self.name = "张翰"
        
        # 定义自己的"工具箱"，包含私有能力和公共工具
        self.toolbox = {
            "WriteContent": {"action": WritingAction(), "desc": "用于从零开始撰写全新的报告章节或段落。适用于任务明确要求'撰写'、'编写'新内容的场景。"},
            "SummarizeText": {"action": SummarizeTextAction(), "desc": "用于对现有的大段文本进行总结、分析、整合和提炼关键信息。适用于任务要求'分析'、'总结'、'整合'、'提炼'的场景。"},
            "PolishContent": {"action": PolishContentAction(), "desc": "用于对已有的草稿进行语言润色和风格优化。适用于任务要求'润色'、'优化'、'修改'的场景。"},
            "ReviewContent": {"action": ReviewContentAction(), "desc": "用于从多个维度审核内容质量，并提供修改建议。适用于任务要求'审核'、'校对'、'评估质量'的场景。"}
        }
        
        self.drafts_dir = self.agent_workspace / "drafts"
        self.summaries_dir = self.agent_workspace / "summaries"
        self.polished_dir = self.agent_workspace / "polished"
        self.reviews_dir = self.agent_workspace / "reviews"
        for d in [self.drafts_dir, self.summaries_dir, self.polished_dir, self.reviews_dir]:
            d.mkdir(exist_ok=True)
            
        logger.info(f"✍️ 写作专家 {self.name} 初始化完成，已启用内置决策核心。")

    async def _execute_specific_task_with_messages(self, task: "Task", history_messages: List[Message]) -> Dict[str, Any]:
        """
        使用MetaGPT标准的Message历史执行任务：思考 -> 选择 -> 行动
        """
        logger.info(f"✍️ {self.name} 接收到任务: {task.description}")

        # 1. 思考 (Think): 调用LLM进行决策
        tool_name = await self._decide_tool(task.description)
        if not tool_name or tool_name not in self.toolbox:
            error_msg = f"决策失败：无法为任务 '{task.description}' 选择合适的工具。"
            logger.error(error_msg)
            return {"status": "error", "result": error_msg}

        logger.info(f"🧠 {self.name} 决策选择工具: {tool_name}")
        
        # 2. 准备上下文 (Prepare Context) - 从Message历史中提取内容
        source_content = ""
        if history_messages:
            contents = []
            for msg in history_messages:
                if hasattr(msg, 'content') and msg.content:
                    contents.append(f"### 来源: {msg.sent_from}\n\n{msg.content}")
            source_content = "\n\n---\n\n".join(contents)
                   
        if not source_content and tool_name != "WriteContent":
            return {"status": "error", "result": f"执行工具'{tool_name}'失败：未在Message历史中找到任何有效内容进行处理。"}

        # 3. 行动 (Act): 执行选定的工具
        try:
            selected_action = self.toolbox[tool_name]["action"]
            
            # 不同的工具可能需要不同的参数
            if tool_name == "WriteContent":
                # MetaGPT标准：Action.run接收history messages
                result_content = await selected_action.run(history_messages, instruction=task.description, context_str=source_content)
                output_dir = self.drafts_dir
                file_prefix = "draft"
            else: 
                # 对于其他工具，传递source_content
                result_content = await selected_action.run(history_messages, source_content)
                if tool_name == "SummarizeText":
                    output_dir = self.summaries_dir
                    file_prefix = "summary"
                elif tool_name == "PolishContent":
                    output_dir = self.polished_dir
                    file_prefix = "polished"
                else: 
                    output_dir = self.reviews_dir
                    file_prefix = "review"

            # 保存产出物
            safe_desc = "".join(c if c.isalnum() else '_' for c in task.description)[:50]
            output_file = output_dir / f"{file_prefix}_{safe_desc}_{datetime.now().strftime('%H%M%S')}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result_content)

            return {
                'status': 'completed',
                'result': {
                    "message": f"已使用工具 '{tool_name}' 完成任务 '{task.description}'",
                    "files_created": [output_file.name],
                    "content": result_content
                }
            }
        except Exception as e:
            error_msg = f"执行工具 '{tool_name}' 时发生错误: {e}"
            logger.error(error_msg, exc_info=True)
            return {"status": "error", "result": error_msg}

    async def _decide_tool(self, instruction: str) -> str:
        """调用LLM来决定使用哪个工具"""
        tools_description = "\n".join([f"- {name}: {info['desc']}" for name, info in self.toolbox.items()])
        prompt = writer_expert_prompts.get_tool_selection_prompt(instruction, tools_description, self.name)
        
        try:
            response_json_str = await llm.acreate_text(prompt)
            match = re.search(r"```json\s*([\s\S]*?)\s*```", response_json_str)
            if match:
                json_str = match.group(1)
            else:
                json_str = response_json_str
            
            decision = json.loads(json_str)
            return decision.get("tool_name")
        except Exception as e:
            logger.error(f"工具决策LLM调用失败: {e}")
            return None
            
    async def get_work_summary(self) -> str:
        """获取工作摘要"""
        try:
            draft_count = len(list(self.drafts_dir.glob("*.md")))
            polished_count = len(list(self.polished_dir.glob("*.md")))
            review_count = len(list(self.reviews_dir.glob("*.md")))
            summary_count = len(list(self.summaries_dir.glob("*.md")))
            
            summary = f"✍️ {self.name} 工作摘要:\n"
            summary += f"• 已撰写草稿: {draft_count} 份\n"
            summary += f"• 已润色文稿: {polished_count} 份\n"
            summary += f"• 已审核内容: {review_count} 次\n"
            summary += f"• 已生成摘要: {summary_count} 份\n"
            summary += f"• 当前状态: {self.status}\n"
            
            if self.current_task:
                summary += f"• 当前任务: {self.current_task}\n"
            
            return summary
            
        except Exception as e:
            return f"✍️ {self.name}: 工作摘要获取失败 - {str(e)}"