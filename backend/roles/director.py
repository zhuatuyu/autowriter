"""
增强版智能项目总监Agent - 基于MetaGPT设计理念
具备深度客户沟通、智能任务规划和动态Agent编排能力
"""
from metagpt.roles.role import Role, RoleContext
from metagpt.schema import Message
from metagpt.logs import logger
from metagpt.actions.add_requirement import UserRequirement

from backend.models.plan import Plan, Task
from backend.actions.director_action import CreatePlan, RevisePlan, DirectAnswer


class DirectorAgent(Role):
    """
    🎯 项目总监 - 核心规划角色 (重构后)
    职责:
    1. 监听用户需求 (UserRequirement)。
    2. 生成结构化的行动计划 (Plan)。
    3. 将计划发布到环境中，启动项目。
    """
    def __init__(self, name: str = "Director", profile: str = "Director", goal: str = "...", **kwargs):
        super().__init__(name=name, profile=profile, goal=goal, **kwargs)
        # 设定角色只关注 UserRequirement 类型的消息
        self._watch([UserRequirement])
        self.agent_capabilities = {
            "case_expert": "王磊 - 专业案例分析师，擅长搜集、分析同类项目的成功案例",
            "writer_expert": "张翰 - 内容创作专家，负责报告撰写、内容润色和优化",
            "data_analyst": "赵丽娅 - 数据分析师，负责数据分析、图表制作和量化评估"
        }

    async def _think(self) -> bool:
        """思考要做什么，设置下一步的动作"""
        # 如果看到了新消息，就准备创建计划
        if self.rc.news:
            # 目前简化处理，只处理最新的一个用户需求
            latest_request = self.rc.news[0]
            logger.info(f"{self.profile}: 收到新需求，准备制定计划: {latest_request.content[:100]}...")
            # 设置下一步要执行的动作是 CreatePlan
            self.rc.todo = CreatePlan(user_request=latest_request.content, agent_capabilities=self.agent_capabilities)
            return True
        return False

    async def _act(self) -> Message:
        """执行计划，并把Plan作为消息发布出去"""
        todo = self.rc.todo
        if not isinstance(todo, (CreatePlan, RevisePlan)):
            logger.warning(f"{self.profile}: 未找到待办事项或类型不正确，跳过执行。")
            return None

        # 执行动作（创建或修订计划）
        if isinstance(todo, CreatePlan):
            # 从最新消息中获取用户请求
            latest_msg = self.rc.memory.get(k=1)[0] if self.rc.memory.get() else None
            user_request = latest_msg.content if latest_msg else "未知请求"
            plan_result = await todo.run(user_request=user_request, agent_capabilities=self.agent_capabilities)
        else:
            # RevisePlan的情况，需要更多参数
            plan_result = await todo.run()

        if not plan_result:
            logger.error(f"{self.profile}: 计划生成失败")
            return None

        # 将生成的Plan对象封装在Message中并发布
        # cause_by 设置为自身的类型，以便其他角色可以订阅
        msg = Message(
            content=plan_result.model_dump_json(), # 将Plan对象序列化为JSON字符串
            role=self.profile,
            cause_by=type(self) # 使用 DirectorAgent 类作为 cause_by
        )
        logger.info(f"{self.profile}: 已生成计划并发布。")
        return msg



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
        格式化计划以便在前端展示 (这个方法仍然需要，但由Orchestrator调用)
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

    async def direct_answer(self, user_message: str, intent: str) -> str:
        """
        直接回答用户的简单问题 (保留此方法以兼容现有调用)
        """
        # 使用MetaGPT原生方式执行action
        action = DirectAnswer()
        result = await action.run(user_message=user_message, intent=intent)
        return result