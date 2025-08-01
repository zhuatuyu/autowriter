"""
架构师（李明） - 报告结构设计专家
完全符合MetaGPT原生架构的Architect角色
"""
from metagpt.actions.design_api import WriteDesign
from metagpt.actions.write_prd import WritePRD
from metagpt.roles.di.role_zero import RoleZero
from metagpt.logs import logger


class ArchitectAgent(RoleZero):
    """
    架构师（李明） - 报告结构设计专家
    完全模仿MetaGPT的architect.py实现，继承RoleZero
    负责设计报告结构和框架
    """
    name: str = "李明"
    profile: str = "Architect"
    goal: str = "设计报告结构和框架，确保报告逻辑清晰、结构合理"
    constraints: str = "确保报告结构简单明了，符合绩效评价报告的标准格式"
    
    # RoleZero特有配置 - 完全按照MetaGPT标准设置
    instruction: str = """Use WriteDesign tool to design report structure"""
    max_react_loop: int = 1
    tools: list[str] = ["Editor:write,read,similarity_search", "RoleZero"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # NOTE: The following init setting will only be effective when self.use_fixed_sop is changed to True
        self.enable_memory = False
        self.set_actions([WriteDesign])
        self._watch([WritePRD])

    def _update_tool_execution(self):
        """更新工具执行映射"""
        wd = WriteDesign()
        self.tool_execution_map.update(
            {
                "WriteDesign.run": wd.run,
                "WriteDesign": wd.run,  # alias
            }
        ) 