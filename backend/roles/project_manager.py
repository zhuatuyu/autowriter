#!/usr/bin/env python
"""
项目经理角色 - 任务规划和调度
"""
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

from backend.actions.pm_action import CreateTaskPlan, TaskPlan
from backend.actions.architect_action import ReportStructure, DesignReportStructure as ArchitectAction


class ProjectManager(Role):
    """
    项目经理 - 纯粹的任务调度者 (SOP第三阶段)
    """
    name: str = "项目经理"
    profile: str = "Project Manager"
    goal: str = "将报告结构分解为具体的写作任务"
    constraints: str = "必须确保任务分解合理，便于WriterExpert执行"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 设置要执行的Action
        self.set_actions([CreateTaskPlan])
        
        # 监听Architect的报告结构
        self._watch([ArchitectAction])

    async def _act(self) -> Message:
        """
        执行ProjectManager的核心逻辑 - SOP第三阶段
        """
        todo = self.rc.todo
        
        if isinstance(todo, CreateTaskPlan):
            # 从记忆中获取报告结构
            structure_msgs = self.rc.memory.get_by_action(ArchitectAction)
            
            if not structure_msgs:
                logger.error("未找到报告结构数据")
                return Message(content="未找到报告结构数据", role=self.profile)
            
            # 获取最新的报告结构
            structure_msg = structure_msgs[-1]
            if not hasattr(structure_msg, 'instruct_content') or not structure_msg.instruct_content:
                logger.error("报告结构数据格式不正确")
                return Message(content="报告结构数据格式不正确", role=self.profile)
            
            # 解析instruct_content中的ReportStructure数据
            try:
                # instruct_content是动态生成的Pydantic对象，需要转换为ReportStructure
                if hasattr(structure_msg.instruct_content, 'title'):
                    # 直接使用动态对象的属性构造ReportStructure
                    report_structure = ReportStructure(
                        title=structure_msg.instruct_content.title,
                        sections=structure_msg.instruct_content.sections
                    )
                else:
                    logger.error("instruct_content格式不正确，缺少title属性")
                    return Message(content="报告结构数据格式不正确", role=self.profile)
            except Exception as e:
                logger.error(f"解析报告结构失败: {e}")
                return Message(content="解析报告结构失败", role=self.profile)
            logger.info(f"ProjectManager开始创建任务计划，基于结构: {report_structure.title}")
            
            # 执行任务计划创建
            task_plan = await todo.run(report_structure)
            
            # 创建包含TaskPlan的消息，供WriterExpert使用
            msg = Message(
                content=f"任务计划创建完成，共{len(task_plan.tasks)}个任务",
                role=self.profile,
                cause_by=type(todo),
                instruct_content=task_plan
            )
            
            logger.info(f"ProjectManager完成任务规划，任务数量: {len(task_plan.tasks)}")
            return msg
        
        return Message(content="ProjectManager: 无待办任务", role=self.profile)