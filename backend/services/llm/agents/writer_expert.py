"""
写作专家Agent - 张翰
负责报告内容撰写和文本创作
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import json
import re

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger

from .base import BaseAgent
from backend.services.llm_provider import llm
from backend.tools.summary_tool import summary_tool # 导入摘要工具

# 导入新的Prompt模块
from backend.services.llm.prompts import writer_expert_prompts


class ContentWritingAction(Action):
    """内容写作动作"""
    
    async def run(self, chapter: str, requirements: str, context: str = "") -> str:
        """执行内容写作"""
        prompt = writer_expert_prompts.get_section_writing_prompt(chapter, requirements, context, "张翰")
        try:
            return await llm.acreate_text(prompt)
        except Exception as e:
            logger.error(f"内容写作失败: {e}")
            return f"写作失败: {str(e)}"

class ContentPolishAction(Action):
    """内容润色动作 (新合并的能力)"""
    async def run(self, content: str, style: str = "专业报告") -> str:
        prompt = writer_expert_prompts.get_content_polish_prompt(content, style, "张翰")
        try:
            return await llm.acreate_text(prompt)
        except Exception as e:
            logger.error(f"内容润色失败: {e}")
            return content

class QualityReviewAction(Action):
    """内容质量审核动作 (新合并的能力)"""
    async def run(self, content: str) -> str:
        prompt = writer_expert_prompts.get_quality_review_prompt(content, "张翰")
        try:
            return await llm.acreate_text(prompt)
        except Exception as e:
            logger.error(f"内容审核失败: {e}")
            return json.dumps({"error": f"审核失败: {e}"})

class SummarizeAction(Action):
    """内容摘要动作 (新能力)"""
    async def run(self, text_to_summarize: str) -> str:
        # 这里可以直接调用summary_tool，也可以使用专属prompt，调用工具更符合解耦原则
        return await summary_tool.run(text_to_summarize)


class WriterExpertAgent(BaseAgent):
    """
    ✍️ 写作专家（张翰） - 虚拟办公室的内容创作者、优化师和总结者
    """
    def __init__(self, agent_id: str, session_id: str, workspace_path: str, memory_manager=None):
        super().__init__(
            agent_id=agent_id,
            session_id=session_id,
            workspace_path=workspace_path,
            memory_manager=memory_manager,
            profile="写作专家",
            goal="撰写、优化和总结高质量、结构清晰的报告内容"
        )
        
        # 初始化写作工具和模板
        self.writing_templates = self._load_writing_templates()
        
        # 设置专家信息
        self.name = "张翰"
        self.avatar = "✍️"
        self.expertise = "内容写作、润色、审核与总结"
        
        # 设置动作 (合并了总编辑的能力)
        self.set_actions([ContentWritingAction, ContentPolishAction, QualityReviewAction, SummarizeAction])
        
        # 创建写作工作目录
        self.drafts_dir = self.agent_workspace / "drafts"
        self.polished_dir = self.agent_workspace / "polished" # 原总编辑目录
        self.reviews_dir = self.agent_workspace / "reviews"
        self.summaries_dir = self.agent_workspace / "summaries" # 新增摘要目录
        
        for dir_path in [self.drafts_dir, self.polished_dir, self.reviews_dir, self.summaries_dir]:
            dir_path.mkdir(exist_ok=True)
        
        logger.info(f"✍️ 写作专家 {self.name} 初始化完成，已整合总编辑能力。")

    
    def _load_writing_templates(self) -> Dict[str, str]:
        """加载写作模板"""
        return {
            "standard_report": {
                "structure": ["引言", "现状分析", "方案设计", "效益评估", "结论建议"],
                "description": "标准项目报告模板"
            },
            "research_paper": {
                "structure": ["摘要", "引言", "相关研究", "研究方法", "实验结果", "讨论", "结论"],
                "description": "学术研究论文模板"
            }
        }
    
    async def _execute_specific_task(self, task: "Task", context: Dict[str, Any]) -> Dict[str, Any]:
        """执行具体的写作或内容处理任务"""
        logger.info(f"✍️ {self.name} 开始执行任务: {task.description}")

        # 简单的基于关键词的任务路由
        task_desc = task.description.lower()
        
        # 提取上下文中的内容
        source_content = ""
        if isinstance(context, dict):
            # 聚合所有上游任务的结果内容
            contents = []
            for key, value in context.items():
                if isinstance(value, dict) and 'result' in value:
                    res = value['result']
                    if isinstance(res, dict) and 'content' in res:
                        contents.append(res['content'])
                    elif isinstance(res, str):
                        contents.append(res)
            source_content = "\n\n---\n\n".join(contents)

        if not source_content and "撰写" not in task_desc:
             # 对于需要输入内容的任务，检查source_content
            if "润色" in task_desc or "优化" in task_desc or "审核" in task_desc or "总结" in task_desc or "摘要" in task_desc:
                 return {"status": "error", "result": "未在上下文中找到可供处理的内容"}

        if "润色" in task_desc or "优化" in task_desc:
            style_match = re.search(r"按照(.*?)风格", task_desc)
            style = style_match.group(1).strip() if style_match else "专业报告"
            return await self._polish_content({"content": source_content, "style": style})

        elif "审核" in task_desc or "校对" in task_desc:
            return await self._review_content({"content": source_content})

        elif "总结" in task_desc or "摘要" in task_desc:
            return await self._summarize_content({"content": source_content})
            
        elif "撰写" in task_desc:
            # 这里的上下文可能更多是作为参考，而不是直接处理对象
            return await self._write_content(task, source_content)
        
        else:
            # 默认当作一个写作任务处理
            logger.warning(f"无法精确匹配任务 '{task.description}'，将按默认写作任务处理。")
            return await self._write_content(task, source_content)


    async def _write_content(self, task: "Task", context_str: str) -> Dict[str, Any]:
        """撰写新内容"""
        try:
            # 简化：直接使用task.description作为写作要求
            requirements = task.description
            # 章节标题可以从task.description中提取，或使用task.id
            chapter = f"章节_{task.id}"

            self.current_task = f"正在撰写: {chapter}"
            self.progress = 10
            
            writing_action = ContentWritingAction()
            content = await writing_action.run(chapter=chapter, requirements=requirements, context=context_str)
            
            self.progress = 90
            
            draft_file = self.drafts_dir / f"draft_{chapter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(draft_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.progress = 100
            
            return {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成 '{chapter}' 的草稿撰写",
                'files_created': [draft_file.name],
                'content': content,
            }
        except Exception as e:
            logger.error(f"❌ {self.name} 内容撰写失败: {e}", exc_info=True)
            return {"status": "error", "result": f"内容撰写失败: {e}"}

    async def _polish_content(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """润色内容 (原总编辑能力)"""
        try:
            content = task.get('content', '')
            style = task.get('style', '专业报告')
            
            self.current_task = f"正在润色内容，风格：{style}"
            self.progress = 10
            
            polish_action = ContentPolishAction()
            polished_content = await polish_action.run(content, style)
            
            self.progress = 80
            
            polish_file = self.polished_dir / f"polished_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(polish_file, 'w', encoding='utf-8') as f:
                f.write(polished_content)
            
            self.progress = 100
            
            return {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成内容润色，风格调整为{style}",
                'files_created': [polish_file.name],
                'content': polished_content, # 返回润色后的内容
            }
            
        except Exception as e:
            logger.error(f"❌ {self.name} 内容润色失败: {e}", exc_info=True)
            return {"status": "error", "result": f"内容润色失败: {e}"}

    async def _review_content(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """审核内容 (原总编辑能力)"""
        try:
            content = task.get('content', '')
            
            self.current_task = "正在进行内容质量审核"
            self.progress = 10
            
            review_action = QualityReviewAction()
            review_result = await review_action.run(content)
            
            self.progress = 80
            
            review_file = self.reviews_dir / f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(review_file, 'w', encoding='utf-8') as f:
                f.write(f"# 内容审核报告\n\n{review_result}")
            
            self.progress = 100
            
            return {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': "已完成内容质量审核",
                'files_created': [review_file.name],
                'review': review_result,
            }
            
        except Exception as e:
            logger.error(f"❌ {self.name} 内容审核失败: {e}", exc_info=True)
            return {"status": "error", "result": f"内容审核失败: {e}"}

    async def _summarize_content(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """总结内容"""
        try:
            content = task.get('content', '')
            self.current_task = "正在生成内容摘要"
            self.progress = 10
            
            summarize_action = SummarizeAction()
            summary_text = await summarize_action.run(content)

            self.progress = 80

            summary_file = self.summaries_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_text)

            self.progress = 100
            
            return {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': "已完成内容摘要生成",
                'files_created': [summary_file.name],
                'content': summary_text, # 将摘要作为主要内容返回
            }

        except Exception as e:
            logger.error(f"❌ {self.name} 内容摘要失败: {e}", exc_info=True)
            return {"status": "error", "result": f"内容摘要失败: {e}"}


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