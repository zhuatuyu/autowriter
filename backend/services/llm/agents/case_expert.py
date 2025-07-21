from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from .base import BaseAgent
from backend.tools.alibaba_search import alibaba_search_tool

class CaseExpertAgent(BaseAgent):
    """案例专家Agent"""

    def __init__(self, agent_id: str, session_id: str, workspace_path: str):
        super().__init__(agent_id, session_id, workspace_path)
        self.name = "王磊"
        self.role = "案例专家"
        self.avatar = "🔍"

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行案例搜索任务"""
        try:
            self.status = 'working'
            keywords = task.get('keywords', ['绩效评价', '相关案例'])
            query = " ".join(keywords)
            self.current_task = f"正在搜索案例: {query}"

            # 使用工具进行搜索
            search_results = await alibaba_search_tool.run(query)
            
            # 将结果保存到文件
            result_file = self.agent_workspace / f'search_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(f"# 案例搜索结果: {query}\n\n{search_results}")
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成关于 '{query}' 的案例搜索。",
                'files_created': [result_file.name],
            }
            
            self.status = 'completed'
            await self._save_result(result)
            return result
            
        except Exception as e:
            self.status = 'error'
            return {'status': 'error', 'error': str(e)} 