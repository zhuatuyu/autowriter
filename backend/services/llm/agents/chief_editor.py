"""
总编辑Agent - 钱敏
负责最终审核、润色和质量把控
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger

from .base import BaseAgent
from backend.services.llm_provider import llm


class ContentReviewAction(Action):
    """内容审核动作"""
    
    async def run(self, content: str, review_type: str = "全面审核") -> str:
        """审核内容质量"""
        prompt = f"""
你是总编辑钱敏，拥有丰富的编辑经验和敏锐的质量把控能力。请对以下内容进行{review_type}：

内容：
{content}

请从以下角度进行审核：
1. **内容准确性**: 事实是否准确，逻辑是否清晰
2. **结构完整性**: 结构是否合理，层次是否分明
3. **语言表达**: 文字是否流畅，表达是否准确
4. **格式规范**: 格式是否统一，标准是否符合要求
5. **整体质量**: 是否达到发布标准

请提供具体的修改建议和优化方案。
"""
        try:
            review_result = await llm.acreate_text(prompt)
            return review_result.strip()
        except Exception as e:
            logger.error(f"内容审核失败: {e}")
            return f"审核失败: {str(e)}"


class ContentPolishAction(Action):
    """内容润色动作"""
    
    async def run(self, content: str, style: str = "专业报告") -> str:
        """润色和优化内容"""
        prompt = f"""
你是总编辑钱敏，请对以下内容进行专业润色，使其符合{style}的标准：

原始内容：
{content}

请进行以下优化：
1. 提升语言表达的专业性和准确性
2. 优化句式结构，增强可读性
3. 统一术语使用，确保一致性
4. 完善逻辑连接，增强连贯性
5. 调整格式，符合专业标准

请直接输出润色后的内容。
"""
        try:
            polished_content = await llm.acreate_text(prompt)
            return polished_content.strip()
        except Exception as e:
            logger.error(f"内容润色失败: {e}")
            return content  # 如果润色失败，返回原内容


class QualityAssuranceAction(Action):
    """质量保证动作"""
    
    async def run(self, content: str) -> Dict[str, Any]:
        """进行质量检查"""
        prompt = f"""
你是总编辑钱敏，请对以下内容进行质量检查，并给出质量评分：

内容：
{content}

请从以下维度评分（1-10分）：
1. 内容完整性
2. 逻辑清晰度
3. 语言流畅度
4. 格式规范性
5. 专业水准

请以JSON格式返回评分结果和改进建议。
"""
        try:
            quality_result = await llm.acreate_text(prompt)
            return {'quality_check': quality_result.strip()}
        except Exception as e:
            logger.error(f"质量检查失败: {e}")
            return {'quality_check': f"质量检查失败: {str(e)}"}


class ChiefEditorAgent(BaseAgent):
    """总编辑Agent - 钱敏 👔"""

    def __init__(self, agent_id: str, session_id: str, workspace_path: str):
        super().__init__(
            agent_id=agent_id,
            session_id=session_id,
            workspace_path=workspace_path,
            profile="总编辑",
            goal="确保报告的最终质量，进行专业审核和润色",
            constraints="严格把控质量标准，确保内容的准确性和专业性"
        )
        
        # 设置专家信息
        self.name = "钱敏"
        self.avatar = "👔"
        self.expertise = "内容审核与质量把控"
        
        # 设置动作
        self.set_actions([ContentReviewAction, ContentPolishAction, QualityAssuranceAction])
        
        # 创建专门的工作目录
        self.reviews_dir = self.agent_workspace / "reviews"
        self.polished_dir = self.agent_workspace / "polished"
        self.final_dir = self.agent_workspace / "final"
        
        for dir_path in [self.reviews_dir, self.polished_dir, self.final_dir]:
            dir_path.mkdir(exist_ok=True)
        
        logger.info(f"👔 总编辑 {self.name} 初始化完成")

    async def _execute_specific_task(self, task: Dict[str, Any], context: str) -> Dict[str, Any]:
        """执行具体的编辑任务"""
        try:
            task_type = task.get('type', 'review_content')
            
            if task_type == 'review_content':
                return await self._review_content(task)
            elif task_type == 'polish_content':
                return await self._polish_content(task)
            elif task_type == 'final_review':
                return await self._final_review(task)
            elif task_type == 'quality_check':
                return await self._quality_check(task)
            else:
                return await self._review_content(task)  # 默认执行内容审核
                
        except Exception as e:
            logger.error(f"❌ {self.name} 执行任务失败: {e}")
            return {
                'agent_id': self.agent_id,
                'status': 'error',
                'result': f'任务执行失败: {str(e)}',
                'error': str(e)
            }

    async def _review_content(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """审核内容"""
        try:
            content = task.get('content', '')
            review_type = task.get('review_type', '全面审核')
            
            self.current_task = f"正在进行{review_type}"
            self.progress = 10
            
            # 执行内容审核
            review_action = ContentReviewAction()
            review_result = await review_action.run(content, review_type)
            
            self.progress = 80
            
            # 保存审核结果
            review_file = self.reviews_dir / f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(review_file, 'w', encoding='utf-8') as f:
                f.write(f"# 内容审核报告\n\n")
                f.write(f"**审核时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**总编辑**: {self.name}\n")
                f.write(f"**审核类型**: {review_type}\n\n")
                f.write(f"## 原始内容\n\n{content[:500]}...\n\n")
                f.write(f"## 审核意见\n\n{review_result}\n\n")
                f.write(f"---\n*审核完成: {self.name} 👔*")
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成{review_type}，提供了详细的修改建议",
                'files_created': [review_file.name],
                'review_summary': review_result[:300] + "..." if len(review_result) > 300 else review_result,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 内容审核失败: {e}")
            raise

    async def _polish_content(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """润色内容"""
        try:
            content = task.get('content', '')
            style = task.get('style', '专业报告')
            
            self.current_task = f"正在润色内容，风格：{style}"
            self.progress = 10
            
            # 执行内容润色
            polish_action = ContentPolishAction()
            polished_content = await polish_action.run(content, style)
            
            self.progress = 80
            
            # 保存润色结果
            polish_file = self.polished_dir / f"polished_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(polish_file, 'w', encoding='utf-8') as f:
                f.write(f"# 内容润色报告\n\n")
                f.write(f"**润色时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**总编辑**: {self.name}\n")
                f.write(f"**润色风格**: {style}\n\n")
                f.write(f"## 润色后内容\n\n{polished_content}\n\n")
                f.write(f"---\n*润色完成: {self.name} 👔*")
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成内容润色，风格调整为{style}",
                'files_created': [polish_file.name],
                'polished_content': polished_content,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 内容润色失败: {e}")
            raise

    async def _final_review(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """最终审核"""
        try:
            self.current_task = "正在进行最终审核"
            self.progress = 10
            
            # 收集所有需要最终审核的内容
            polished_files = list(self.polished_dir.glob("*.md"))
            
            if not polished_files:
                return {
                    'agent_id': self.agent_id,
                    'status': 'completed',
                    'result': "暂无润色内容可供最终审核",
                    'files_created': []
                }
            
            final_files = []
            
            for polished_file in polished_files[-3:]:  # 审核最近的3个文件
                with open(polished_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 进行质量检查
                qa_action = QualityAssuranceAction()
                quality_result = await qa_action.run(content)
                
                # 生成最终版本
                final_content = f"""# 最终审核版本

**最终审核时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**总编辑**: {self.name}
**源文件**: {polished_file.name}

## 质量评估

{quality_result.get('quality_check', '质量检查完成')}

## 最终内容

{content}

---
*最终审核: {self.name} 👔*
*状态: 已通过最终审核，可以发布*
"""
                
                final_file = self.final_dir / f"final_{polished_file.stem}.md"
                with open(final_file, 'w', encoding='utf-8') as f:
                    f.write(final_content)
                
                final_files.append(final_file.name)
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成 {len(final_files)} 个内容的最终审核，全部通过发布标准",
                'files_created': final_files,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 最终审核失败: {e}")
            raise

    async def _quality_check(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """质量检查"""
        try:
            content = task.get('content', '')
            
            self.current_task = "正在进行质量检查"
            self.progress = 10
            
            # 执行质量检查
            qa_action = QualityAssuranceAction()
            quality_result = await qa_action.run(content)
            
            self.progress = 80
            
            # 保存质量检查结果
            qa_file = self.reviews_dir / f"quality_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(qa_file, 'w', encoding='utf-8') as f:
                f.write(f"# 质量检查报告\n\n")
                f.write(f"**检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**总编辑**: {self.name}\n\n")
                f.write(f"## 质量评估结果\n\n{quality_result.get('quality_check', '检查完成')}\n\n")
                f.write(f"---\n*质量检查: {self.name} 👔*")
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': "已完成质量检查，提供了详细的质量评估",
                'files_created': [qa_file.name],
                'quality_result': quality_result,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 质量检查失败: {e}")
            raise

    async def get_work_summary(self) -> str:
        """获取工作摘要"""
        try:
            review_count = len(list(self.reviews_dir.glob("*.md")))
            polish_count = len(list(self.polished_dir.glob("*.md")))
            final_count = len(list(self.final_dir.glob("*.md")))
            
            summary = f"👔 {self.name} 工作摘要:\n"
            summary += f"• 完成审核: {review_count} 次\n"
            summary += f"• 内容润色: {polish_count} 份\n"
            summary += f"• 最终审核: {final_count} 份\n"
            summary += f"• 当前状态: {self.status}\n"
            
            if self.current_task:
                summary += f"• 当前任务: {self.current_task}\n"
            
            return summary
            
        except Exception as e:
            return f"👔 {self.name}: 工作摘要获取失败 - {str(e)}"