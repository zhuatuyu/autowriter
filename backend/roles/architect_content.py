#!/usr/bin/env python
"""
ArchitectContent - 专注章节结构设计（SOP2）
"""
from pydantic import BaseModel
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

from backend.actions.research_action import ConductComprehensiveResearch, ResearchData
from backend.actions.architect_content_action import DesignReportStructureOnly as ArchitectAction


class StructurePath(BaseModel):
    structure_file_path: str


class ArchitectContent(Role):
    name: str = "章节架构师"
    profile: str = "ArchitectContent"
    goal: str = "基于研究简报设计章节结构（跳过指标表）"
    constraints: str = "不生成指标表"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([ArchitectAction])
        self._watch([ConductComprehensiveResearch])
        self._project_repo = None

    async def _act(self) -> Message:
        msgs = self.rc.memory.get_by_action(ConductComprehensiveResearch)
        if not msgs:
            return Message(content="等待研究简报", cause_by=ArchitectAction)
        rd = msgs[-1].instruct_content if hasattr(msgs[-1], 'instruct_content') else None
        research_brief = rd.brief if isinstance(rd, ResearchData) else (msgs[-1].content or "")

        todo = self.rc.todo
        # 仅结构设计Action
        report_structure = await todo.run(research_brief)

        # 保存结构到单一文件（详细版）
        structure_file_path = None
        if self._project_repo:
            try:
                # 生成带有每个章节详细写作指导的结构文件
                content = "# 报告结构设计\n\n## 章节结构\n\n"
                for i, s in enumerate(report_structure.sections, 1):
                    content += f"### {i}. {s.section_title}\n\n"
                    # 将章节写作指导原样写入（包含写作要点、RAG策略、质量要求等）
                    content += f"{s.description_prompt}\n\n"
                # 保存结构文件
                await self._project_repo.docs.save(filename="report_structure.md", content=content)
                structure_file_path = str(self._project_repo.docs.workdir / "report_structure.md")
                logger.info(f"🧩 报告结构已保存: {structure_file_path}")
            except Exception as e:
                logger.warning(f"保存结构失败: {e}")

        # 仅传递路径（Pydantic模型），避免复杂对象的序列化问题；由下游角色自行读取与解析
        msg_content = f"章节结构生成完成，已保存到: {structure_file_path or '未知路径'}"
        return Message(
            content=msg_content,
            cause_by=ArchitectAction,
            instruct_content=StructurePath(structure_file_path=structure_file_path or "")
        )

