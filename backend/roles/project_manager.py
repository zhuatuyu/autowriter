#!/usr/bin/env python
"""
项目经理角色 - 任务规划和调度
"""
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

from backend.actions.pm_action import CreateTaskPlan, TaskPlan
from backend.actions.architect_action import ReportStructure, DesignReportStructure as ArchitectAction, ArchitectOutput


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
                instruct_content = structure_msg.instruct_content
                
                # 按照原生MetaGPT模式解析ArchitectOutput
                if isinstance(instruct_content, ArchitectOutput):
                    # 直接从ArchitectOutput对象获取
                    report_structure = instruct_content.report_structure
                    logger.info(f"✅ 从ArchitectOutput获取ReportStructure: {report_structure.title}")
                elif hasattr(instruct_content, 'report_structure'):
                    # 处理动态生成的对象（MetaGPT可能会转换Pydantic对象）
                    report_structure = ReportStructure(
                        title=instruct_content.report_structure.title,
                        sections=instruct_content.report_structure.sections
                    )
                    logger.info(f"✅ 从动态对象获取ReportStructure: {report_structure.title}")
                elif hasattr(instruct_content, 'title'):
                    # 向后兼容：直接的ReportStructure对象
                    report_structure = ReportStructure(
                        title=instruct_content.title,
                        sections=instruct_content.sections
                    )
                    logger.info(f"✅ 从直接对象解析ReportStructure: {report_structure.title}")
                elif isinstance(instruct_content, dict) and 'title' in instruct_content:
                    # 向后兼容：字典格式的ReportStructure
                    report_structure = ReportStructure(
                        title=instruct_content['title'],
                        sections=instruct_content['sections']
                    )
                    logger.info(f"✅ 从字典解析ReportStructure: {report_structure.title}")
                else:
                    logger.error(f"instruct_content格式不正确，内容: {str(instruct_content)[:200]}...")
                    logger.error(f"instruct_content类型: {type(instruct_content)}")
                    logger.error(f"instruct_content是否为字典: {isinstance(instruct_content, dict)}")
                    if isinstance(instruct_content, dict):
                        logger.error(f"instruct_content键列表: {list(instruct_content.keys())}")
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