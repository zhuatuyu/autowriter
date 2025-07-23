"""
写作专家Agent - 张翰
负责报告内容撰写和文本创作
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger

from .base import BaseAgent
from backend.services.llm_provider import llm


class ContentWritingAction(Action):
    """内容写作动作"""
    
    async def run(self, chapter: str, requirements: str, context: str = "") -> str:
        """执行内容写作"""
        prompt = f"""
你是一位顶级的报告写作专家（张翰），擅长将零散的信息整合成结构清晰、文笔流畅的专业报告章节。

## 任务
撰写报告的 **{chapter}** 章节。

## 要求
{requirements}

## 可用材料/上下文
{context}

---
请严格按照要求，仅输出该章节的Markdown格式的正文内容。
"""
        try:
            content = await llm.acreate_text(prompt)
            return content.strip()
        except Exception as e:
            logger.error(f"内容写作失败: {e}")
            return f"写作失败: {str(e)}"


class ContentReviewAction(Action):
    """内容审核动作"""
    
    async def run(self, content: str, requirements: str) -> str:
        """审核和优化内容"""
        prompt = f"""
你是写作专家张翰，请审核以下内容并进行优化：

原始内容：
{content}

要求：
{requirements}

请优化内容的结构、逻辑和表达，确保符合专业报告的标准。
"""
        try:
            optimized_content = await llm.acreate_text(prompt)
            return optimized_content.strip()
        except Exception as e:
            logger.error(f"内容审核失败: {e}")
            return content  # 如果审核失败，返回原内容


class WriterExpertAgent(BaseAgent):
    """
    ✍️ 写作专家（张翰） - 虚拟办公室的内容创作者
    """
    def __init__(self, agent_id: str, session_id: str, workspace_path: str, memory_manager=None):
        super().__init__(
            agent_id=agent_id,
            session_id=session_id,
            workspace_path=workspace_path,
            memory_manager=memory_manager,
            profile="写作专家",
            goal="撰写高质量、结构清晰的报告内容"
        )
        
        # 初始化写作工具和模板
        self.writing_templates = self._load_writing_templates()
        
        # 设置专家信息
        self.name = "张翰"
        self.avatar = "✍️"
        self.expertise = "内容写作与编辑"
        
        # 设置动作
        self.set_actions([ContentWritingAction, ContentReviewAction])
        
        # 创建写作工作目录
        self.drafts_dir = self.agent_workspace / "drafts"
        self.reviews_dir = self.agent_workspace / "reviews"
        self.drafts_dir.mkdir(exist_ok=True)
        self.reviews_dir.mkdir(exist_ok=True)
        
        logger.info(f"✍️ 写作专家 {self.name} 初始化完成")
    
    def _load_writing_templates(self) -> Dict[str, str]:
        """加载写作模板"""
        return {
            "executive_summary": """
# 执行摘要

## 项目概述
{project_overview}

## 主要成果
{key_achievements}

## 关键指标
{key_metrics}

## 结论与建议
{conclusions}
""",
            "introduction": """
# 引言

## 背景
{background}

## 目标
{objectives}

## 方法
{methodology}
""",
            "analysis": """
# 分析章节

## 数据概述
{data_overview}

## 关键发现
{key_findings}

## 趋势分析
{trend_analysis}
""",
            "conclusion": """
# 结论

## 主要成果
{main_results}

## 经验总结
{lessons_learned}

## 未来展望
{future_outlook}
"""
        }
    
    async def _execute_specific_task(self, task: Dict[str, Any], context: str) -> Dict[str, Any]:
        """执行具体的写作任务"""
        try:
            task_type = task.get('type', 'write_content')
            
            if task_type == 'write_content':
                return await self._write_content(task)
            elif task_type == 'review_content':
                return await self._review_content(task)
            elif task_type == 'optimize_content':
                return await self._optimize_content(task)
            else:
                return await self._write_content(task)  # 默认执行内容写作
                
        except Exception as e:
            logger.error(f"❌ {self.name} 执行任务失败: {e}")
            return {
                'agent_id': self.agent_id,
                'status': 'error',
                'result': f'任务执行失败: {str(e)}',
                'error': str(e)
            }

    async def _write_content(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """撰写内容"""
        try:
            chapter = task.get('chapter', '未知章节')
            requirements = task.get('requirements', '无特定要求')
            context = task.get('context', '无')
            
            self.current_task = f"正在撰写：{chapter}"
            self.progress = 10
            
            # 执行写作动作
            writing_action = ContentWritingAction()
            draft_content = await writing_action.run(chapter, requirements, context)
            
            self.progress = 70
            
            # 保存草稿
            draft_file = self.drafts_dir / f'{chapter.replace(" ", "_").replace(":", "_")}_{datetime.now().strftime("%H%M%S")}.md'
            with open(draft_file, 'w', encoding='utf-8') as f:
                f.write(f"# {chapter}\n\n")
                f.write(f"**撰写时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**撰写专家**: {self.name}\n\n")
                f.write(draft_content)
                f.write(f"\n\n---\n*初稿完成: {self.name} ✍️*")
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成《{chapter}》的撰写，共 {len(draft_content)} 字符",
                'files_created': [draft_file.name],
                'content_preview': draft_content[:200] + "..." if len(draft_content) > 200 else draft_content,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 内容撰写失败: {e}")
            raise

    async def _review_content(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """审核内容"""
        try:
            content = task.get('content', '')
            requirements = task.get('requirements', '标准审核')
            
            self.current_task = "正在审核内容质量"
            self.progress = 10
            
            # 执行审核动作
            review_action = ContentReviewAction()
            optimized_content = await review_action.run(content, requirements)
            
            self.progress = 80
            
            # 保存审核结果
            review_file = self.reviews_dir / f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(review_file, 'w', encoding='utf-8') as f:
                f.write(f"# 内容审核报告\n\n")
                f.write(f"**审核时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**审核专家**: {self.name}\n\n")
                f.write(f"## 原始内容\n\n{content}\n\n")
                f.write(f"## 优化后内容\n\n{optimized_content}\n\n")
                f.write(f"---\n*审核完成: {self.name} ✍️*")
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成内容审核和优化",
                'files_created': [review_file.name],
                'optimized_content': optimized_content,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 内容审核失败: {e}")
            raise

    async def _optimize_content(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """优化内容"""
        try:
            self.current_task = "正在优化内容结构和表达"
            
            # 读取草稿文件进行优化
            draft_files = list(self.drafts_dir.glob("*.md"))
            if not draft_files:
                return {
                    'agent_id': self.agent_id,
                    'status': 'completed',
                    'result': "暂无草稿文件可供优化",
                    'files_created': []
                }
            
            optimized_files = []
            for draft_file in draft_files[-3:]:  # 优化最近的3个文件
                with open(draft_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 执行优化
                review_action = ContentReviewAction()
                optimized_content = await review_action.run(content, "优化结构和表达")
                
                # 保存优化结果
                optimized_file = self.reviews_dir / f"optimized_{draft_file.stem}.md"
                with open(optimized_file, 'w', encoding='utf-8') as f:
                    f.write(optimized_content)
                
                optimized_files.append(optimized_file.name)
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已优化 {len(optimized_files)} 个内容文件",
                'files_created': optimized_files,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 内容优化失败: {e}")
            raise

    async def get_work_summary(self) -> str:
        """获取工作摘要"""
        try:
            draft_count = len(list(self.drafts_dir.glob("*.md")))
            review_count = len(list(self.reviews_dir.glob("*.md")))
            
            summary = f"✍️ {self.name} 工作摘要:\n"
            summary += f"• 已撰写草稿: {draft_count} 份\n"
            summary += f"• 完成审核: {review_count} 份\n"
            summary += f"• 当前状态: {self.status}\n"
            
            if self.current_task:
                summary += f"• 当前任务: {self.current_task}\n"
            
            return summary
            
        except Exception as e:
            return f"✍️ {self.name}: 工作摘要获取失败 - {str(e)}" 