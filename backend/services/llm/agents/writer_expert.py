from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from .base import BaseAgent
from backend.services.llm_provider import llm

class WriterExpertAgent(BaseAgent):
    """写作专家Agent"""

    def __init__(self, agent_id: str, session_id: str, workspace_path: str):
        super().__init__(agent_id, session_id, workspace_path)
        self.name = "张翰"
        self.role = "写作专家"
        self.avatar = "✍️"

    def _get_writing_prompt(self, chapter: str, requirements: str, context: str = "") -> str:
        """动态构建写作Prompt"""
        return f"""
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

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行写作任务，调用LLM生成内容"""
        try:
            self.status = 'working'
            chapter = task.get('chapter', '未知章节')
            requirements = task.get('requirements', '无特定要求')
            context = task.get('context', '无')
            
            self.current_task = f"正在撰写：{chapter}"
            
            # 使用LLM生成内容
            prompt = self._get_writing_prompt(chapter, requirements, context)
            draft_content = await llm.acreate_text(prompt)
            
            # 保存草稿
            draft_file = self.agent_workspace / f'{chapter.replace(" ", "_").replace(":", "_")}.md'
            with open(draft_file, 'w', encoding='utf-8') as f:
                f.write(draft_content)
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成《{chapter}》的初稿撰写。",
                'files_created': [draft_file.name],
            }
            
            self.status = 'completed'
            await self._save_result(result)
            return result
            
        except Exception as e:
            self.status = 'error'
            return {'status': 'error', 'error': str(e)} 