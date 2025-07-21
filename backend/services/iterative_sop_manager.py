"""
迭代式SOP管理器 - 人机协同的智能写作系统
实现真正的迭代开发和动态交互
"""
import asyncio
import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from queue import Queue
import threading

# MetaGPT核心导入
from metagpt.roles import Role
from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger

from backend.tools.alibaba_search import alibaba_search_tool

class ReportPhase(Enum):
    """报告阶段"""
    INITIALIZATION = "initialization"
    REQUIREMENT_GATHERING = "requirement_gathering"
    TEMPLATE_CREATION = "template_creation"
    ITERATIVE_WRITING = "iterative_writing"
    REVIEW_REFINEMENT = "review_refinement"
    COMPLETION = "completion"

class ChapterStatus(Enum):
    """章节状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DRAFT_COMPLETED = "draft_completed"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    NEEDS_REVISION = "needs_revision"

@dataclass
class DynamicChapter:
    """动态章节定义"""
    chapter_id: str
    title: str
    description: str
    priority: int
    status: ChapterStatus
    content: str = ""
    requirements: List[str] = None
    dependencies: List[str] = None
    assigned_expert: str = ""
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []
        if self.dependencies is None:
            self.dependencies = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass 
class ProjectContext:
    """项目上下文"""
    project_name: str = ""
    project_type: str = ""
    client_requirements: List[str] = None
    uploaded_files: List[str] = None
    reference_reports: List[str] = None
    current_phase: ReportPhase = ReportPhase.INITIALIZATION
    dynamic_template: Dict[str, DynamicChapter] = None
    interaction_history: List[Dict] = None
    
    def __post_init__(self):
        if self.client_requirements is None:
            self.client_requirements = []
        if self.uploaded_files is None:
            self.uploaded_files = []
        if self.reference_reports is None:
            self.reference_reports = []
        if self.dynamic_template is None:
            self.dynamic_template = {}
        if self.interaction_history is None:
            self.interaction_history = []

class ProjectDirectorRole(Role):
    """项目总监角色 - 真正的协调者和对话者"""
    
    def __init__(self, context: ProjectContext, message_queue: Queue):
        super().__init__(
            name="项目总监",
            profile="Project Director",
            goal="协调项目进展，与用户保持持续对话，确保项目符合需求",
            constraints="必须主动与用户交流，及时调整项目方向"
        )
        self._context = context
        self._message_queue = message_queue
        self._pending_user_responses = []
    
    async def _act(self) -> Message:
        """执行总监职责"""
        try:
            # 根据当前阶段执行不同的行为
            if self._context.current_phase == ReportPhase.INITIALIZATION:
                return await self._handle_initialization()
            elif self._context.current_phase == ReportPhase.REQUIREMENT_GATHERING:
                return await self._handle_requirement_gathering()
            elif self._context.current_phase == ReportPhase.TEMPLATE_CREATION:
                return await self._handle_template_creation()
            elif self._context.current_phase == ReportPhase.ITERATIVE_WRITING:
                return await self._handle_iterative_writing()
            else:
                return await self._handle_default()
                
        except Exception as e:
            error_msg = f"项目总监执行失败：{str(e)}"
            self._send_message(error_msg, "error")
            return Message(content=error_msg, role=self.profile)
    
    async def _handle_initialization(self) -> Message:
        """处理初始化阶段"""
        welcome_msg = """👋 欢迎使用AutoWriter Enhanced！

我是您的项目总监，将全程协助您完成报告写作。

为了更好地为您服务，请告诉我：
1. 您需要写什么类型的报告？
2. 报告的主题是什么？
3. 您有什么特殊要求吗？

您也可以上传参考文件或模板，我会据此为您定制写作方案。"""
        
        self._send_message(welcome_msg, "waiting_for_response")
        self._context.current_phase = ReportPhase.REQUIREMENT_GATHERING
        
        return Message(content=welcome_msg, role=self.profile)
    
    async def _handle_requirement_gathering(self) -> Message:
        """处理需求收集阶段"""
        # 分析已收集的需求
        if len(self._context.client_requirements) < 2:
            question = "请提供更多关于报告的详细信息，比如：报告的目标读者、主要内容重点、预期长度等。"
            self._send_message(question, "waiting_for_response")
            return Message(content=question, role=self.profile)
        else:
            # 需求足够，进入模板创建阶段
            self._context.current_phase = ReportPhase.TEMPLATE_CREATION
            return await self._handle_template_creation()
    
    async def _handle_template_creation(self) -> Message:
        """处理模板创建阶段"""
        # 创建动态模板
        template = self._create_dynamic_template()
        self._context.dynamic_template = template
        
        template_summary = self._format_template_summary(template)
        
        question = f"""📋 根据您的需求，我制定了以下报告结构：

{template_summary}

请问：
1. 这个结构是否合适？
2. 需要调整哪些部分？
3. 希望从哪个章节开始写作？

确认后我们就可以开始迭代写作了！"""
        
        self._send_message(question, "waiting_for_response")
        
        return Message(content=question, role=self.profile)
    
    async def _handle_iterative_writing(self) -> Message:
        """处理迭代写作阶段"""
        # 找到下一个需要写作的章节
        next_chapter = self._get_next_chapter_to_write()
        
        if next_chapter:
            # 分配给合适的专家
            expert_type = self._assign_expert(next_chapter)
            
            msg = f"📝 开始写作《{next_chapter.title}》，已分配给{expert_type}..."
            self._send_message(msg, "writing")
            
            return Message(content=msg, role=self.profile)
        else:
            # 所有章节完成
            self._context.current_phase = ReportPhase.COMPLETION
            completion_msg = "🎉 恭喜！报告的所有章节都已完成。正在进行最终整理..."
            self._send_message(completion_msg, "completed")
            
            return Message(content=completion_msg, role=self.profile)
    
    async def _handle_default(self) -> Message:
        """默认处理"""
        msg = "项目总监待命中，等待进一步指示..."
        return Message(content=msg, role=self.profile)
    
    def _create_dynamic_template(self) -> Dict[str, DynamicChapter]:
        """创建动态模板"""
        template = {}
        
        # 根据项目类型和需求创建模板
        if "绩效评价" in self._context.project_type:
            chapters = [
                ("1", "项目概述", "介绍项目基本情况和背景", 1),
                ("2", "评价方法", "说明评价方法和指标体系", 2),
                ("3", "评价结果", "展示评价结果和数据分析", 3),
                ("4", "结论建议", "提出结论和改进建议", 4)
            ]
        else:
            # 通用结构
            chapters = [
                ("1", "概述", "项目背景和目标", 1),
                ("2", "主要内容", "核心内容分析", 2),
                ("3", "总结", "结论和建议", 3)
            ]
        
        for chapter_id, title, desc, priority in chapters:
            template[chapter_id] = DynamicChapter(
                chapter_id=chapter_id,
                title=title,
                description=desc,
                priority=priority,
                status=ChapterStatus.NOT_STARTED
            )
        
        return template
    
    def _format_template_summary(self, template: Dict[str, DynamicChapter]) -> str:
        """格式化模板摘要"""
        summary = ""
        for chapter in sorted(template.values(), key=lambda x: x.priority):
            status_icon = "⭕" if chapter.status == ChapterStatus.NOT_STARTED else "✅"
            summary += f"{status_icon} {chapter.chapter_id}. {chapter.title} - {chapter.description}\n"
        return summary
    
    def _get_next_chapter_to_write(self) -> Optional[DynamicChapter]:
        """获取下一个需要写作的章节"""
        for chapter in sorted(self._context.dynamic_template.values(), key=lambda x: x.priority):
            if chapter.status == ChapterStatus.NOT_STARTED:
                return chapter
        return None
    
    def _assign_expert(self, chapter: DynamicChapter) -> str:
        """分配专家"""
        # 根据章节内容分配合适的专家
        title_lower = chapter.title.lower()
        
        if any(keyword in title_lower for keyword in ["概述", "背景", "介绍"]):
            return "项目分析师"
        elif any(keyword in title_lower for keyword in ["方法", "指标", "评价"]):
            return "方法专家"
        elif any(keyword in title_lower for keyword in ["结果", "数据", "分析"]):
            return "数据分析师"
        elif any(keyword in title_lower for keyword in ["结论", "建议", "总结"]):
            return "报告专家"
        else:
            return "通用专家"
    
    def _send_message(self, content: str, status: str):
        """发送消息"""
        if self._message_queue:
            self._message_queue.put({
                "agent_type": "project_director",
                "agent_name": "项目总监",
                "content": content,
                "status": status,
                "requires_user_input": status == "waiting_for_response"
            })
    
    def handle_user_response(self, user_input: str):
        """处理用户回复"""
        # 记录用户回复
        self._context.interaction_history.append({
            "timestamp": datetime.now(),
            "type": "user_response",
            "content": user_input
        })
        
        # 根据当前阶段处理用户输入
        if self._context.current_phase == ReportPhase.REQUIREMENT_GATHERING:
            self._context.client_requirements.append(user_input)
        elif self._context.current_phase == ReportPhase.TEMPLATE_CREATION:
            # 处理模板确认或修改请求
            if "确认" in user_input or "开始" in user_input:
                self._context.current_phase = ReportPhase.ITERATIVE_WRITING
        
        logger.info(f"项目总监收到用户回复: {user_input[:50]}...")

class IterativeReportTeam:
    """迭代式报告团队"""
    
    def __init__(self, session_id: str, message_queue: Queue):
        self._session_id = session_id
        self._message_queue = message_queue
        
        # 初始化项目上下文
        self._context = ProjectContext()
        
        # 创建项目总监
        self._director = ProjectDirectorRole(self._context, message_queue)
        
        # 创建工作空间
        workspace_path = Path(f"workspaces/{session_id}")
        workspace_path.mkdir(parents=True, exist_ok=True)
    
    async def start_conversation(self) -> str:
        """开始对话"""
        try:
            # 项目总监开始工作
            result = await self._director._act()
            return result.content
        except Exception as e:
            logger.error(f"对话启动失败: {e}")
            return f"对话启动失败: {str(e)}"
    
    def handle_user_input(self, user_input: str):
        """处理用户输入"""
        self._director.handle_user_response(user_input)
    
    async def continue_workflow(self) -> str:
        """继续工作流程"""
        try:
            result = await self._director._act()
            return result.content
        except Exception as e:
            logger.error(f"工作流程继续失败: {e}")
            return f"工作流程继续失败: {str(e)}"
    
    def get_project_status(self) -> Dict:
        """获取项目状态"""
        return {
            "session_id": self._session_id,
            "current_phase": self._context.current_phase.value,
            "project_name": self._context.project_name,
            "project_type": self._context.project_type,
            "requirements_count": len(self._context.client_requirements),
            "chapters_count": len(self._context.dynamic_template),
            "completed_chapters": len([
                c for c in self._context.dynamic_template.values() 
                if c.status == ChapterStatus.COMPLETED
            ]),
            "interaction_count": len(self._context.interaction_history)
        }

# 全局实例
iterative_teams: Dict[str, IterativeReportTeam] = {}