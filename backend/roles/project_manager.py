"""
🎯 项目总监Agent - 完全模仿MetaGPT ProjectManager的RoleZero实现
负责项目规划和任务分配，采用RoleZero的动态思考和行动模式
"""
from metagpt.roles.di.role_zero import RoleZero
from metagpt.schema import Message
from metagpt.logs import logger
from metagpt.actions.add_requirement import UserRequirement
from metagpt.actions.project_management import WriteTasks
from metagpt.utils.common import any_to_str

# 为了兼容性，保留Plan和相关Action的导入
from backend.models.plan import Plan, Task
from backend.actions.director_action import CreatePlan, RevisePlan


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
        
        # 关键：按照MetaGPT标准设置
        self.enable_memory = False  # 禁用内存
        self.set_actions([WriteTasks])  # 使用MetaGPT原生的WriteTasks
        self._watch([UserRequirement])  # 监听用户需求
        
        # 团队能力配置
        self.agent_capabilities = {
            "case_expert": "王磊 - 专业案例分析师，擅长搜集、分析同类项目的成功案例",
            "writer_expert": "张翰 - 内容创作专家，负责报告撰写、内容润色和优化",
            "data_analyst": "赵丽娅 - 数据分析师，负责数据分析、图表制作和量化评估"
        }

    def _update_tool_execution(self):
        """更新工具执行映射，RoleZero的标准方法"""
        wt = WriteTasks()
        self.tool_execution_map.update({
            "WriteTasks.run": wt.run,
            "WriteTasks": wt.run,  # alias
        })

    async def process_request(self, user_message: str) -> Plan:
        """
        兼容性方法：处理用户请求并生成计划
        这个方法是为了兼容现有的orchestrator调用而保留的
        """
        try:
            # 直接使用CreatePlan动作来生成计划
            create_plan_action = CreatePlan()
            plan = await create_plan_action.run(
                user_request=user_message, 
                agent_capabilities=self.agent_capabilities
            )
            logger.info(f"{self.profile}: 成功生成计划")
            return plan
        except Exception as e:
            logger.error(f"{self.profile}: 生成计划失败: {e}")
            return None

    async def revise_plan(self, original_plan: Plan, user_feedback: str) -> Plan:
        """
        兼容性方法：修订现有计划
        这个方法是为了兼容现有的orchestrator调用而保留的
        """
        try:
            # 直接使用RevisePlan动作来修订计划
            revise_plan_action = RevisePlan()
            revised_plan = await revise_plan_action.run(
                original_plan=original_plan,
                user_feedback=user_feedback,
                agent_capabilities=self.agent_capabilities
            )
            logger.info(f"{self.profile}: 成功修订计划")
            return revised_plan
        except Exception as e:
            logger.error(f"{self.profile}: 修订计划失败: {e}")
            return None

    def _format_plan_for_display(self, plan: Plan) -> str:
        """
        格式化计划以便在前端展示 (这个方法仍然需要，但由ProjectManager调用)
        """
        if not plan:
            return "❌ 计划生成失败"
        
        response = f"**🎯 项目目标:** {plan.goal}\n\n"
        response += "**📋 执行计划:**\n"
        
        for i, task in enumerate(plan.tasks, 1):
            # 获取负责人名称
            agent_name = self.agent_capabilities.get(task.agent, task.agent)
            response += f"{i}. **{task.description}**\n"
            response += f"   👤 负责人: {agent_name}\n"
            if task.dependencies:
                deps = ", ".join([f"步骤{int(dep.split('_')[1])}" for dep in task.dependencies])
                response += f"   📎 依赖: {deps}\n"
            response += "\n"
        
        response += "---\n"
        response += "**请问您是否同意此计划？** 您可以直接回复\"同意\"开始执行，或者提出您的修改意见。"
        return response