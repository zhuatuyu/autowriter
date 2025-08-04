#!/usr/bin/env python
"""
项目经理Action集合 - 任务规划和调度
"""
from typing import List
from pydantic import BaseModel, Field
from metagpt.actions import Action
from metagpt.logs import logger

from .architect_action import ReportStructure


class Task(BaseModel):
    """写作任务的结构化模型"""
    task_id: int
    section_title: str
    instruction: str  # 写作指令，即原description_prompt
    metric_ids: List[str] = Field(default_factory=list)  # 关联的指标ID


class TaskPlan(BaseModel):
    """任务计划的结构化模型"""
    tasks: List[Task]


class CreateTaskPlan(Action):
    """
    创建任务计划Action - ProjectManager的核心能力
    将报告结构分解为具体的写作任务
    """
    
    async def run(self, report_structure: ReportStructure) -> TaskPlan:
        """
        将报告结构分解为任务列表
        """
        logger.info(f"开始创建任务计划，报告: {report_structure.title}")
        
        tasks = []
        for i, section in enumerate(report_structure.sections):
            task = Task(
                task_id=i,
                section_title=section.section_title,
                instruction=section.description_prompt,
                metric_ids=section.metric_ids
            )
            tasks.append(task)
            logger.info(f"创建任务 {i}: {section.section_title}")
        
        task_plan = TaskPlan(tasks=tasks)
        logger.info(f"任务计划创建完成，共 {len(tasks)} 个任务")
        
        return task_plan