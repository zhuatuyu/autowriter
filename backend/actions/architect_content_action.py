#!/usr/bin/env python
"""
DesignReportStructureOnly - 仅负责章节结构设计（SOP2专用）
"""
from typing import List, Tuple
from pydantic import BaseModel, Field
from metagpt.actions import Action
from metagpt.logs import logger

from backend.tools.project_info import get_project_info_text
from backend.config.writer_prompts import (
    SECTION_PROMPT_GENERATION_TEMPLATE as ENV_SECTION_PROMPT_GENERATION_TEMPLATE,
    REPORT_SECTIONS as ENV_REPORT_SECTIONS,
    GET_SECTION_CONFIG as ENV_GET_SECTION_CONFIG,
    GET_SECTION_KEY_BY_TITLE as ENV_GET_SECTION_KEY_BY_TITLE,
)


class Section(BaseModel):
    section_title: str = Field(..., description="章节标题")
    description_prompt: str = Field(..., description="写作指导")


class ReportStructure(BaseModel):
    title: str = Field(..., description="报告标题")
    sections: List[Section] = Field(..., description="章节列表")


class DesignReportStructureOnly(Action):
    async def run(self, research_brief_text: str, project_info: dict | None = None) -> ReportStructure:
        logger.info("🧩 仅生成报告章节结构（SOP2）")
        # 标题来自项目配置文本
        project_text = get_project_info_text()
        title = "绩效评价报告"
        if project_text:
            # 简单提取项目名（容错）
            for line in project_text.splitlines():
                if "项目名称:" in line:
                    title = line.split("项目名称:", 1)[-1].strip() + "绩效评价报告"
                    break

        # 生成章节内容
        sections_cfg = ENV_REPORT_SECTIONS
        sections: List[Section] = []
        for sec in sections_cfg:
            base_prompt = sec.get("prompt_template", "请根据研究简报撰写本章节")
            section_title = sec.get("title", "章节")
            # 从章节配置获取RAG指导（不做RAG检索，仅拼装模板）
            section_key = ENV_GET_SECTION_KEY_BY_TITLE(section_title)
            section_specific_cfg = ENV_GET_SECTION_CONFIG(section_key) or {}
            rag_instructions = section_specific_cfg.get("rag_instructions", "")

            description = ENV_SECTION_PROMPT_GENERATION_TEMPLATE.format(
                base_prompt=base_prompt,
                rag_instructions=rag_instructions,
            )
            sections.append(Section(section_title=section_title, description_prompt=description))

        return ReportStructure(title=title, sections=sections)

