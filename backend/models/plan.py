"""
Plan 和 Task 数据模型
定义了AI Agent团队工作流的核心结构
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

class Task(BaseModel):
    """
    表示一个独立的、可执行的任务单元
    """
    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    description: str = Field(..., description="任务的详细描述，清晰地说明需要做什么")
    agent: Optional[str] = Field(None, description="负责执行此任务的Agent的ID，由Director指定")
    owner_agent_id: Optional[str] = Field(None, description="（已弃用，请使用agent）负责执行此任务的Agent的ID")
    status: str = Field("pending", description="任务状态: pending, in_progress, completed, error")
    dependencies: List[str] = Field([], description="此任务依赖的其他任务ID列表")
    result: Optional[Any] = Field(None, description="任务执行后的结果")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class Plan(BaseModel):
    """
    表示一个完整的、由多个任务构成的行动计划
    """
    id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    goal: str = Field(..., description="整个计划的最终目标，由用户原始需求转化而来")
    tasks: List[Task] = Field([], description="构成计划的有序任务列表")
    status: str = Field("pending", description="计划状态: pending, in_progress, completed, error")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    def get_next_task(self) -> Optional[Task]:
        """获取下一个待处理的任务"""
        for task in self.tasks:
            if task.status == "pending":
                # 检查依赖是否完成
                if not task.dependencies:
                    return task
                
                all_deps_completed = True
                for dep_id in task.dependencies:
                    dep_task = self.get_task_by_id(dep_id)
                    if not dep_task or dep_task.status != "completed":
                        all_deps_completed = False
                        break
                
                if all_deps_completed:
                    return task
        return None

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """根据ID查找任务"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def is_completed(self) -> bool:
        """检查整个计划是否已完成"""
        return all(task.status == "completed" for task in self.tasks) 