#!/usr/bin/env python
"""
SectionWriter - 章节写作专家（SOP2）
"""
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger
from datetime import datetime

from backend.actions.section_writer_action import WriteSection
from backend.actions.project_manager_action import CreateTaskPlan, TaskPlan, Task
from backend.actions.architect_content_action import DesignReportStructureOnly as ArchitectAction


class SectionWriter(Role):
    name: str = "章节写作专家"
    profile: str = "SectionWriter"
    goal: str = "按结构生成章节并聚合为最终报告"
    constraints: str = "严格遵循结构顺序，不包含指标表"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([WriteSection])
        self._watch([CreateTaskPlan, ArchitectAction])
        self._project_repo = None

    async def _act(self) -> Message:
        task_plan_msgs = self.rc.memory.get_by_action(CreateTaskPlan)
        arch_msgs = self.rc.memory.get_by_action(ArchitectAction)
        
        if not task_plan_msgs:
            logger.warning("SectionWriter: 等待任务计划...")
            return Message(content="等待任务计划", cause_by=WriteSection)
        
        if not arch_msgs:
            logger.warning("SectionWriter: 等待架构师结构...")
            return Message(content="等待架构师结构", cause_by=WriteSection)

        # 获取任务计划
        task_plan = task_plan_msgs[-1].instruct_content
        if not task_plan:
            logger.error("SectionWriter: 任务计划为空")
            return Message(content="任务计划为空", cause_by=WriteSection)
        
        # 获取架构师结构信息
        arch_output = arch_msgs[-1].instruct_content
        logger.info(f"SectionWriter: 接收到架构师结构信息: {type(arch_output)}")
        
        # 章节写作不再注入指标表或触发检索：仅消费研究简报与网络案例摘录

        # 写作
        sections = []
        write_action = WriteSection()
        # 注入 ProjectRepo，供写作Action读取 docs/resources（研究简报与网络案例）
        write_action._project_repo = self._project_repo
        vector_store_path = None  # 不使用RAG
        tasks = getattr(task_plan, 'tasks', []) if task_plan else []
        
        logger.info(f"SectionWriter: 开始写作 {len(tasks)} 个章节")
        
        for i, task in enumerate(tasks):
            task_obj = task if hasattr(task, 'section_title') else Task(
                task_id=i,
                section_title=task.get('section_title', f'章节{i+1}'),
                instruction=task.get('instruction', task.get('description', '分析内容')),
            )
            
            logger.info(f"📝 写作章节 {i+1}: {getattr(task_obj, 'section_title', '未知标题')}")
            
            sec = await write_action.run(task=task_obj)
            sections.append(sec)
            logger.info(f"✅ 章节 {i+1} 写作完成")

        # 聚合保存
        try:
            final_report = "\n\n".join(sections)
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            fname = f"final_report_{ts}.md"
            await self._project_repo.docs.save(filename=fname, content=final_report)
            logger.info(f"📝 最终报告已保存: {self._project_repo.docs.workdir / fname}")
        except Exception as e:
            logger.error(f"保存最终报告失败: {e}")

        return Message(content="章节写作完成", cause_by=WriteSection)

