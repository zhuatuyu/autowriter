#!/usr/bin/env python
"""
项目经理角色 - 任务规划和调度
"""
from pydantic import BaseModel
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

from backend.actions.project_manager_action import CreateTaskPlan, TaskPlan
from backend.actions.architect_content_action import ReportStructure, DesignReportStructureOnly as ArchitectAction


class ReportStructureProxy(BaseModel):
    title: str
    sections: list[dict]


class ProjectManager(Role):
    """
    项目经理 - 纯粹的任务调度者 (SOP第三阶段)
    """
    name: str = "项目经理"
    profile: str = "Project Manager"
    goal: str = "将报告结构分解为具体的写作任务"
    constraints: str = "必须确保任务分解合理，便于WriterExpert执行"

    def __init__(self, **kwargs):
        super().__init__()
        
        # 设置要执行的Action
        self.set_actions([CreateTaskPlan])
        
        # 监听Architect的报告结构输出
        self._watch([ArchitectAction])

    async def _act(self) -> Message:
        """
        执行ProjectManager的核心逻辑 - SOP第三阶段
        """
        todo = self.rc.todo
        
        if isinstance(todo, CreateTaskPlan):
            # 从记忆中获取报告结构消息
            structure_msgs = self.rc.memory.get_by_action(ArchitectAction)
            if not structure_msgs:
                logger.error("未找到报告结构数据")
                return Message(content="未找到报告结构数据", role=self.profile)
            structure_msg = structure_msgs[-1]
            logger.info(f"📋 接收到架构师消息: {structure_msg.content}")

            # 读取 Pydantic instruct_content
            instruct_content = structure_msg.instruct_content
            structure_file_path = getattr(instruct_content, "structure_file_path", "") if instruct_content else ""
            if not structure_file_path:
                logger.error("缺少结构文件路径 structure_file_path")
                return Message(content="缺少结构文件路径", role=self.profile)

            # 读取并解析 report_structure.md -> 构造 ReportStructure 代理
            try:
                from pathlib import Path
                import re
                text = Path(structure_file_path).read_text(encoding="utf-8")
                blocks = re.split(r"^###\s+\d+\.\s+", text, flags=re.MULTILINE)
                titles = re.findall(r"^###\s+\d+\.\s+(.*)$", text, flags=re.MULTILINE)
                sections = []
                for idx, title in enumerate(titles, 1):
                    guidance = blocks[idx] if idx < len(blocks) else ""
                    sections.append({
                        "section_title": title.strip(),
                        "description_prompt": guidance.strip(),
                    })
                rs_proxy = ReportStructureProxy(title="绩效评价报告", sections=sections)
                logger.info(f"✅ 解析 report_structure.md 成功，章节数: {len(sections)}")
            except Exception as e:
                logger.error(f"解析 report_structure.md 失败: {e}")
                return Message(content=f"解析报告结构失败: {e}", role=self.profile)

            # 构造成真实 ReportStructure（使用原模型字段）
            try:
                from backend.actions.architect_content_action import Section
                rs = ReportStructure(title=rs_proxy.title, sections=[
                    Section(section_title=s["section_title"], description_prompt=s["description_prompt"]) for s in rs_proxy.sections
                ])
            except Exception as e:
                logger.error(f"构造 ReportStructure 失败: {e}")
                return Message(content=f"构造报告结构失败: {e}", role=self.profile)

            # 执行任务计划创建
            task_plan = await todo.run(rs)
            msg = Message(
                content=f"任务计划创建完成，共{len(task_plan.tasks)}个任务",
                role=self.profile,
                cause_by=type(todo),
                instruct_content=task_plan
            )
            logger.info(f"ProjectManager完成任务规划，任务数量: {len(task_plan.tasks)}")
            return msg
        
        return Message(content="ProjectManager: 无待办任务", role=self.profile)