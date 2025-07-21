from .base import BaseAgent

class DataAnalystAgent(BaseAgent):
    """数据分析师Agent"""
    def __init__(self, agent_id: str, session_id: str, workspace_path: str):
        super().__init__(agent_id, session_id, workspace_path)
        self.name = "赵丽娅"
        self.role = "数据分析师"
        self.avatar = "📊" 