"""
数据模型定义
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

class WorkflowPhase(Enum):
    ANALYSIS = "analysis"
    REPORTING = "reporting"
    WRITING = "writing"
    REVIEW = "review"
    PAUSED = "paused"
    COMPLETED = "completed"

class AgentType(Enum):
    CHIEF_EDITOR = "chief_editor"
    DATA_ANALYST = "data_analyst"
    POLICY_RESEARCHER = "policy_researcher"
    CASE_RESEARCHER = "case_researcher"
    INDICATOR_BUILDER = "indicator_builder"
    WRITER = "writer"
    REVIEWER = "reviewer"

@dataclass
class AgentMessage:
    message_id: str
    session_id: str
    agent_type: AgentType
    agent_name: str
    content: str
    timestamp: datetime
    status: str = "sent"  # sent, thinking, completed
    metadata: Dict = field(default_factory=dict)

@dataclass
class AgentReport:
    report_id: str
    session_id: str
    agent_type: AgentType
    analysis_content: Dict
    findings: List[str]
    recommendations: List[str]
    confidence_score: float
    data_sources: List[str]
    created_at: datetime

@dataclass
class ChapterDraft:
    draft_id: str
    session_id: str
    chapter_code: str
    content: str
    version: int
    writing_instruction: Dict
    source_materials: List[str]
    quality_score: float
    feedback: List[Dict]
    status: str  # draft, under_review, approved, needs_revision
    created_at: datetime

@dataclass
class ClientIntervention:
    intervention_id: str
    session_id: str
    intervention_type: str  # material_upload, feedback, pause_request, resume_request
    content: str
    attached_files: List[str]
    impact_on_workflow: Dict
    agent_responses: List[Dict]
    timestamp: datetime

@dataclass
class WorkflowCheckpoint:
    checkpoint_id: str
    session_id: str
    phase: WorkflowPhase
    agent_states: Dict
    work_progress: Dict
    temporary_data: Dict
    can_resume_from: bool
    created_at: datetime

@dataclass
class WorkSession:
    session_id: str
    project_info: Dict
    current_phase: str
    current_chapter: str
    agent_reports: Dict
    editor_decisions: List[Dict]
    writing_drafts: Dict
    quality_scores: Dict
    client_interventions: List[Dict]
    checkpoints: List[Dict]
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "project_info": self.project_info,
            "current_phase": self.current_phase,
            "current_chapter": self.current_chapter,
            "agent_reports": self.agent_reports,
            "editor_decisions": self.editor_decisions,
            "writing_drafts": self.writing_drafts,
            "quality_scores": self.quality_scores,
            "client_interventions": self.client_interventions,
            "checkpoints": self.checkpoints,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

@dataclass
class ReportStructure:
    """报告结构模型"""
    title: str
    chapters: List[Dict]
    metadata: Dict
    created_at: datetime
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "chapters": self.chapters,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }