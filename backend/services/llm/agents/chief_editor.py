from .base import BaseAgent

class ChiefEditorAgent(BaseAgent):
    """总编辑Agent"""
    def __init__(self, agent_id: str, session_id: str, workspace_path: str):
        super().__init__(agent_id, session_id, workspace_path)
        self.name = "钱敏"
        self.role = "总编辑"
        self.avatar = "👔" 