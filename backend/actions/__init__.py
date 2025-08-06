"""
Actions模块
符合MetaGPT标准的各种智能体动作
"""

from .writer_action import WriteSection, IntegrateReport, EvaluateMetrics
# 新的核心Action
from .research_action import PrepareDocuments, ConductComprehensiveResearch, ResearchData, Documents
from .architect_action import DesignReportStructure, ReportStructure, MetricAnalysisTable
from .pm_action import CreateTaskPlan, TaskPlan, Task

__all__ = [
    # 写作专家Action
    "WriteSection",
    "IntegrateReport",
    "EvaluateMetrics",
    # 新的核心Action和数据模型
    "PrepareDocuments",
    "ConductComprehensiveResearch",
    "ResearchData",
    "Documents",
    "DesignReportStructure",
    "ReportStructure", 
    "MetricAnalysisTable",
    "CreateTaskPlan",
    "TaskPlan",
    "Task",
]
