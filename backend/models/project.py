from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class Project(BaseModel):
    """项目模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    project_type: str = "other"  # technical_doc, business_report, academic_paper, other
    status: str = "active"  # active, completed, archived
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    workspace_path: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }