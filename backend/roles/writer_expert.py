#!/usr/bin/env python
"""
写作专家角色 - 内容生成和整合
"""
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

from backend.actions.writer_action import WriteSection, IntegrateReport
from backend.actions.pm_action import TaskPlan, Task
from backend.actions.research_action import ResearchData
from backend.actions.architect_action import MetricAnalysisTable


class WriterExpert(Role):
    """
    写作专家 - 专注的内容创作者
    """
    name: str = "写作专家"
    profile: str = "Writer Expert"
    goal: str = "基于任务计划和研究数据生成高质量的报告内容"
    constraints: str = "必须充分利用RAG检索和指标数据，确保内容的准确性和专业性"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_actions([WriteSection, IntegrateReport])
        self._watch([TaskPlan, ResearchData, MetricAnalysisTable])

    async def _act(self) -> Message:
        """
        执行WriterExpert的核心逻辑
        """
        # 检查是否有所有必需的数据
        task_plan_msgs = self.rc.memory.get_by_action(TaskPlan)
        research_data_msgs = self.rc.memory.get_by_action(ResearchData)
        metric_table_msgs = self.rc.memory.get_by_action(MetricAnalysisTable)
        
        if not all([task_plan_msgs, research_data_msgs, metric_table_msgs]):
            logger.warning("等待所有必需数据...")
            return Message(content="等待数据中...", cause_by=WriteSection)
        
        try:
            # 解析所有数据
            task_plan = TaskPlan.model_validate_json(task_plan_msgs[-1].content)
            research_data = ResearchData.model_validate_json(research_data_msgs[-1].content)
            metric_table = MetricAnalysisTable.model_validate_json(metric_table_msgs[-1].content)
            
            logger.info(f"开始写作报告，共 {len(task_plan.tasks)} 个章节")
            
            # 为每个任务生成章节内容
            sections = []
            write_action = WriteSection()
            
            for task in task_plan.tasks:
                section_content = await write_action.run(
                    task=task,
                    vector_store_path=research_data.vector_store_path,
                    metric_table_json=metric_table.data_json
                )
                sections.append(section_content)
                logger.info(f"完成章节: {task.section_title}")
            
            # 整合最终报告
            integrate_action = IntegrateReport()
            final_report = await integrate_action.run(
                sections=sections,
                report_title="绩效分析报告"  # 可以从task_plan中获取
            )
            
            return Message(
                content=final_report,
                cause_by=IntegrateReport
            )
            
        except Exception as e:
            logger.error(f"写作报告失败: {e}")
            return Message(content=f"错误：{str(e)}", cause_by=WriteSection)