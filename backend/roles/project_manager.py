"""
ProjectManager智能体 - 项目管理器
完全模仿MetaGPT的project_manager.py实现，继承RoleZero
使用MetaGPT原生的WriteTasks Action来处理任务分配
"""
from metagpt.actions import WriteTasks
from metagpt.actions.design_api import WriteDesign
from metagpt.roles.di.role_zero import RoleZero


class ProjectManagerAgent(RoleZero):
    """
    ProjectManager智能体 - 项目管理器
    完全模仿MetaGPT的project_manager.py实现，继承RoleZero
    使用MetaGPT原生的WriteTasks Action来处理任务分配
    """
    name: str = "吴丽"
    profile: str = "Project_Manager"
    goal: str = "制定项目计划并协调团队执行"
    constraints: str = "确保计划的可行性和团队协作的高效性"
    
    # RoleZero特有配置 - 完全按照MetaGPT标准设置
    instruction: str = """Use WriteTasks tool to write a project task list"""
    max_react_loop: int = 1  # 按照MetaGPT原生设置
    tools: list[str] = ["Editor:write,read,similarity_search", "RoleZero", "WriteTasks"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # NOTE: The following init setting will only be effective when self.use_fixed_sop is changed to True
        self.enable_memory = False
        self.set_actions([WriteTasks])
        self._watch([WriteDesign])

    def _update_tool_execution(self):
        wt = WriteTasks()
        self.tool_execution_map.update(
            {
                "WriteTasks.run": wt.run,
                "WriteTasks": wt.run,  # alias
            }
        )