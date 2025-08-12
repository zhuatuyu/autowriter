#!/usr/bin/env python
"""
ArchitectMetric - 专注指标体系设计（SOP1）
"""
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

from backend.actions.research_action import ConductComprehensiveResearch, ResearchData
from backend.actions.metric_design_action import DesignMetricSystem


class ArchitectMetric(Role):
    name: str = "指标架构师"
    profile: str = "ArchitectMetric"
    goal: str = "基于研究简报设计指标体系并输出指标表"
    constraints: str = "仅生成指标体系，不负责章节结构"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 监听研究输出
        self.set_actions([DesignMetricSystem])
        self._watch([ConductComprehensiveResearch])
        self._project_repo = None

    async def _act(self) -> Message:
        msgs = self.rc.memory.get_by_action(ConductComprehensiveResearch)
        if not msgs:
            return Message(content="等待研究简报", cause_by=DesignMetricSystem)
        rd = msgs[-1].instruct_content if hasattr(msgs[-1], 'instruct_content') else None
        research_brief = rd.brief if isinstance(rd, ResearchData) else (msgs[-1].content or "")

        action = self.actions[0]
        metric_json = await action.run(research_brief)

        # 保存文件
        if self._project_repo:
            import json
            content = f"# 指标分析表\n\n```json\n{json.dumps(metric_json, ensure_ascii=False, indent=2)}\n```"
            await self._project_repo.docs.save(filename="metric_analysis_table.md", content=content)
            logger.info("📊 指标分析表已保存")
        return Message(content="指标体系设计完成", cause_by=DesignMetricSystem)

