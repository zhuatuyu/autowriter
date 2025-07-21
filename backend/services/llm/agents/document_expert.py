from datetime import datetime
from pathlib import Path
from typing import Dict, List

import docx
from .base import BaseAgent
from backend.services.llm_provider import llm
from backend.tools.mineru_api_tool import mineru_tool

class DocumentExpertAgent(BaseAgent):
    """文档专家Agent - 专业的文档管理、解析和结构化"""

    def __init__(self, agent_id: str, session_id: str, workspace_path: str):
        super().__init__(agent_id, session_id, workspace_path)
        self.name = "李心悦"
        self.role = "文档专家"
        self.avatar = "📚"
        
        self.upload_path = self.agent_workspace / "uploads"
        self.processed_path = self.agent_workspace / "processed"
        self.upload_path.mkdir(exist_ok=True)
        self.processed_path.mkdir(exist_ok=True)

    def _get_summarize_prompt(self, filename: str, content: str) -> str:
        """动态构建用于总结内容的Prompt"""
        return f"""
你是一个专业的分析师，你的任务是从以下Markdown文档中，为项目总监提炼出核心摘要。

文档来源: '{filename}'
文档内容（节选）:
---
{content[:4000]}
---

请用一句话总结这份文档的核心内容、主要观点或关键数据。摘要必须简洁、精炼，直击要点。
例如："该文件详细阐述了项目的三个阶段性目标及对应的预算分配。"
"""

    async def execute_task(self, task: Dict) -> Dict:
        """
        执行文档处理任务。
        主要逻辑：扫描uploads文件夹，使用Mineru API处理新文件，生成结构化Markdown并总结。
        """
        # ... [此处将保留 execute_task 的核心逻辑] ...
        # ... 它将调用 mineru_tool.process_file 和 _summarize_content ...
        pass # 只是一个示例

    async def _summarize_content(self, filename: str, content: str) -> str:
        """使用LLM对Markdown内容进行总结和关键信息提炼"""
        prompt = self._get_summarize_prompt(filename, content)
        summary = await llm.acreate_text(prompt)
        return summary.strip()

    # ... [其他辅助方法，如 _report_completion, _send_message] ... 