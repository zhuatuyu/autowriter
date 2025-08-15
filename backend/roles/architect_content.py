#!/usr/bin/env python
"""
ArchitectContent - 专注章节结构设计（SOP2）
"""
import json
from pydantic import BaseModel
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

from backend.actions.research_action import ConductComprehensiveResearch, ResearchData
from backend.actions.architect_content_action import DesignReportStructureOnly as ArchitectAction
from metagpt.actions import UserRequirement
from backend.config.writer_prompts import SECTION_CONFIGURATIONS, REPORT_SECTIONS


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
        # 既可在收到研究消息后触发，也可在仅有用户需求时触发（回退从本地简报读取）
        self._watch([ConductComprehensiveResearch, UserRequirement])
        self._project_repo = None

    async def _act(self) -> Message:
        # 从消息读取研究简报；若消息缺失，回退到本地文件读取（仅路径传递，不传大对象）
        msgs = self.rc.memory.get_by_action(ConductComprehensiveResearch)
        research_brief = ""
        if msgs:
            rd = msgs[-1].instruct_content if hasattr(msgs[-1], 'instruct_content') else None
            research_brief = rd.brief if isinstance(rd, ResearchData) else (msgs[-1].content or "")
        elif self._project_repo:
            try:
                brief_path = self._project_repo.docs.workdir / "research_brief.md"
                if brief_path.exists():
                    research_brief = brief_path.read_text(encoding="utf-8")
            except Exception:
                pass

        todo = self.rc.todo or (self.actions[0] if self.actions else None)
        if not todo:
            return Message(content="ArchitectContent: 无可执行Action", cause_by=ArchitectAction)
        # 仅结构设计Action
        report_structure = await todo.run(research_brief)

        # 保存结构到单一JSON文件（结构化版本）
        structure_file_path = None
        if self._project_repo:
            try:
                # 构建JSON格式的章节结构
                sections_data = []
                for i, section in enumerate(report_structure.sections, 1):
                    # 获取章节配置
                    section_key = self._get_section_key_by_title(section.section_title)
                    section_config = SECTION_CONFIGURATIONS.get(section_key, {})
                    
                    section_data = {
                        "section_id": i,
                        "section_title": section.section_title,
                        "chapter_code": str(i),
                        "writing_sequence_order": i * 10,  # 10, 20, 30...
                        "is_indicator_driven": False,
                        "description_prompt": section.description_prompt,
                        "rag_instructions": section_config.get("rag_instructions", ""),
                        "fact_requirements": {
                            "data_sources": ["研究简报六键", "网络案例摘录", "指标体系与评分摘要"],
                            "no_external_retrieval": True,
                            "traceability_required": True,
                            "fallback_instruction": "如缺失信息，标注 '信息待补充'，避免臆测",
                            "consistency_requirement": "确保表述与事实一致，避免过度延展"
                        }
                    }
                    sections_data.append(section_data)
                
                # 构建完整的报告结构JSON
                report_structure_json = {
                    "report_title": "绩效分析报告",
                    "version": "1.0",
                    "generated_at": report_structure.generated_at if hasattr(report_structure, 'generated_at') else "",
                    "total_sections": len(sections_data),
                    "sections": sections_data
                }
                
                # 保存JSON文件
                await self._project_repo.docs.save(
                    filename="report_structure.json", 
                    content=json.dumps(report_structure_json, ensure_ascii=False, indent=2)
                )
                structure_file_path = str(self._project_repo.docs.workdir / "report_structure.json")
                logger.info(f"🧩 报告结构已保存为JSON: {structure_file_path}")
            except Exception as e:
                logger.warning(f"保存JSON结构失败: {e}")

        # 仅传递路径（可序列化 dict），避免复杂对象的序列化问题；由下游角色自行读取与解析
        msg_content = f"章节结构生成完成，已保存到: {structure_file_path or '未知路径'}"
        # 由于上游序列化器在 instruct_content 上存在兼容性问题，这里仅通过 content 文本提示路径
        # 下游 SectionWriter 将按固定路径从 workspace/docs 读取JSON结构文件，避免跨消息序列化风险
        return Message(content=msg_content, cause_by=ArchitectAction)

    def _get_section_key_by_title(self, section_title: str) -> str:
        """根据章节标题获取对应的配置键"""
        title = section_title or ""
        for key, cfg in SECTION_CONFIGURATIONS.items():
            for kw in cfg.get("title_keywords", []):
                if kw in title:
                    return key
        return "general"

