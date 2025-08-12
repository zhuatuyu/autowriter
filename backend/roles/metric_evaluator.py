#!/usr/bin/env python
"""
MetricEvaluator - 统一评价并回写指标表（SOP1）
"""
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

from backend.actions.metric_evaluator_action import EvaluateMetrics
from backend.actions.research_action import ConductComprehensiveResearch
from backend.actions.metric_design_action import DesignMetricSystem


class MetricEvaluator(Role):
    name: str = "指标评价专家"
    profile: str = "MetricEvaluator"
    goal: str = "根据指标体系进行统一评价并回写"
    constraints: str = "严格输出score/opinion并写回md"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([EvaluateMetrics])
        self._watch([DesignMetricSystem])
        self._project_repo = None

    async def _act(self) -> Message:
        msgs = self.rc.memory.get_by_action(DesignMetricSystem)
        if not msgs:
            return Message(content="等待指标体系", cause_by=EvaluateMetrics)

        # 从最近的ArchitectMetric行为中读取 md 或 直接拿数据并回写
        metric_json_text = "{}"
        try:
            if self._project_repo:
                import re
                md_path = self._project_repo.docs.workdir / "metric_analysis_table.md"
                if md_path.exists():
                    text = md_path.read_text(encoding="utf-8")
                    m = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL)
                    if m:
                        metric_json_text = m.group(1)
        except Exception as e:
            logger.warning(f"读取指标表失败: {e}")

        evaluate = self.actions[0]
        # 从ProductManager的研究数据中获取项目向量库路径（若可用）
        vector_store_path = None
        try:
            pm_msgs = self.rc.memory.get_by_action(ConductComprehensiveResearch)
            if pm_msgs and hasattr(pm_msgs[-1], 'instruct_content'):
                rd = pm_msgs[-1].instruct_content
                if hasattr(rd, 'vector_store_path'):
                    vector_store_path = rd.vector_store_path
            # 兜底：从项目仓库推断路径
            if not vector_store_path and self._project_repo:
                vector_store_path = str(self._project_repo.workdir / "vector_storage" / "project_docs")
        except Exception:
            pass
        # 评分并写回
        await evaluate.run(
            metric_table_json=metric_json_text,
            vector_store_path=vector_store_path,
            metric_table_md_path=str(self._project_repo.docs.workdir / "metric_analysis_table.md") if self._project_repo else None,
        )
        return Message(content="指标评分与回写完成", cause_by=EvaluateMetrics)

