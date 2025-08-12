"""
Actions模块
符合MetaGPT标准的各种智能体动作
"""

from .section_writer_action import WriteSection  # 章节写作（SOP2）
from .metric_evaluator_action import EvaluateMetrics  # 指标评价（SOP1）
# 新的核心Action
from .research_action import PrepareDocuments, ConductComprehensiveResearch, ResearchData, Documents
from .architect_content_action import DesignReportStructureOnly as DesignReportStructure, ReportStructure
from .project_manager_action import CreateTaskPlan, TaskPlan, Task  # PM动作

__all__ = [
    # 写作专家Action
    "WriteSection",
    "EvaluateMetrics",
    # 新的核心Action和数据模型
    "PrepareDocuments",
    "ConductComprehensiveResearch",
    "ResearchData",
    "Documents",
    "DesignReportStructure",
    "ReportStructure", 
    "CreateTaskPlan",
    "TaskPlan",
    "Task",
]
