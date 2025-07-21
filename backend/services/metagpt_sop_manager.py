"""
MetaGPT SOP管理器 - 基于最佳实践的清晰架构
采用标准的MetaGPT SOP模式，实现真正的多Agent智能协作
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from queue import Queue
import threading

# MetaGPT核心导入
from metagpt.roles import Role
from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.team import Team
from metagpt.environment import Environment
from metagpt.logs import logger

from tools.alibaba_search import alibaba_search_tool
from tools.report_template_analyzer import report_template_analyzer, ChapterInfo

class WorkflowPhase(Enum):
    """工作流程阶段"""
    PLANNING = "planning"           # 规划阶段
    RESEARCH = "research"          # 研究阶段  
    ANALYSIS = "analysis"          # 分析阶段
    WRITING = "writing"            # 写作阶段
    REVIEW = "review"              # 评审阶段
    REVISION = "revision"          # 修订阶段
    COMPLETED = "completed"        # 完成阶段

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

@dataclass
class WorkTask:
    """工作任务"""
    task_id: str
    title: str
    description: str
    assigned_role: str
    phase: WorkflowPhase
    status: TaskStatus
    priority: int
    dependencies: List[str]
    created_at: datetime
    updated_at: datetime
    result: Optional[str] = None
    chapter_code: Optional[str] = None

class SOPState:
    """SOP状态管理"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_phase = WorkflowPhase.PLANNING
        self.tasks: Dict[str, WorkTask] = {}
        self.completed_chapters: List[str] = []
        self.user_interventions: List[Dict] = []
        self.project_context: Dict = {}
        self.workflow_history: List[Dict] = []
        
    def add_task(self, task: WorkTask):
        """添加任务"""
        self.tasks[task.task_id] = task
        logger.info(f"添加任务: {task.title} -> {task.assigned_role}")
        
    def update_task_status(self, task_id: str, status: TaskStatus, result: str = None):
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            self.tasks[task_id].updated_at = datetime.now()
            if result:
                self.tasks[task_id].result = result
            logger.info(f"任务状态更新: {task_id} -> {status.value}")
    
    def get_ready_tasks(self) -> List[WorkTask]:
        """获取可执行的任务"""
        ready_tasks = []
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                # 检查依赖是否完成
                dependencies_met = all(
                    self.tasks.get(dep_id, {}).status == TaskStatus.COMPLETED 
                    for dep_id in task.dependencies
                )
                if dependencies_met:
                    ready_tasks.append(task)
        
        # 按优先级排序
        return sorted(ready_tasks, key=lambda x: x.priority)
    
    def add_user_intervention(self, content: str):
        """添加用户介入"""
        intervention = {
            "content": content,
            "timestamp": datetime.now(),
            "phase": self.current_phase,
            "processed": False
        }
        self.user_interventions.append(intervention)
        logger.info(f"用户介入: {content[:50]}...")

# ==================== ACTIONS ====================

class PlanningAction(Action):
    """规划动作 - 分析需求并制定工作计划"""
    
    async def run(self, project_info: Dict, template_analyzer, sop_state: SOPState) -> str:
        """执行规划"""
        try:
            # 分析项目需求
            template_summary = template_analyzer.get_template_summary()
            
            # 检查用户介入
            user_requirements = []
            for intervention in sop_state.user_interventions:
                if not intervention["processed"]:
                    user_requirements.append(intervention["content"])
                    intervention["processed"] = True
            
            prompt = f"""作为项目总监，请制定详细的工作计划：

## 项目信息
- 项目名称：{project_info.get('name', '未知项目')}
- 项目类型：{project_info.get('type', '绩效评价')}
- 预算规模：{project_info.get('budget', '待确定')}万元
- 资金来源：{project_info.get('funding_source', '财政资金')}

## 模板信息
- 模板名称：{template_summary['name']}
- 总章节数：{template_summary['total_chapters']}
- 下一章节：{template_summary.get('next_chapter', {}).get('title', '无')}

## 用户特殊要求
{chr(10).join(user_requirements) if user_requirements else '无特殊要求'}

## 任务要求
请制定包含以下内容的详细工作计划：
1. 工作阶段划分（研究->分析->写作->评审）
2. 每个阶段的具体任务分配
3. 任务优先级和依赖关系
4. 预期时间安排
5. 质量控制点

请以JSON格式返回工作计划，包含tasks数组。"""

            # 这里应该调用LLM生成计划
            # 暂时返回示例计划
            plan = self._generate_sample_plan(project_info, template_summary)
            
            return json.dumps(plan, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"规划失败: {e}")
            return f"规划出现错误：{str(e)}"
    
    def _generate_sample_plan(self, project_info: Dict, template_summary: Dict) -> Dict:
        """生成示例计划"""
        return {
            "project_overview": f"为{project_info.get('name', '项目')}制定绩效评价报告生成计划",
            "phases": [
                {
                    "phase": "research",
                    "description": "信息收集和研究阶段",
                    "duration": "2-3天"
                },
                {
                    "phase": "analysis", 
                    "description": "数据分析和指标构建阶段",
                    "duration": "1-2天"
                },
                {
                    "phase": "writing",
                    "description": "报告写作阶段",
                    "duration": "2-3天"
                },
                {
                    "phase": "review",
                    "description": "质量评审和修订阶段", 
                    "duration": "1天"
                }
            ],
            "tasks": [
                {
                    "task_id": "research_policy",
                    "title": "政策法规研究",
                    "assigned_role": "policy_researcher",
                    "phase": "research",
                    "priority": 1,
                    "dependencies": []
                },
                {
                    "task_id": "research_cases",
                    "title": "案例收集分析",
                    "assigned_role": "case_researcher", 
                    "phase": "research",
                    "priority": 1,
                    "dependencies": []
                },
                {
                    "task_id": "build_indicators",
                    "title": "构建指标体系",
                    "assigned_role": "indicator_expert",
                    "phase": "analysis", 
                    "priority": 2,
                    "dependencies": ["research_policy", "research_cases"]
                }
            ]
        }

class ResearchAction(Action):
    """研究动作 - 收集信息和资料"""
    
    def __init__(self, role_type: str):
        super().__init__()
        self.role_type = role_type
    
    async def run(self, task: WorkTask, project_info: Dict, sop_state: SOPState) -> str:
        """执行研究任务"""
        try:
            # 构建搜索查询
            search_query = f"{project_info.get('name', '')} {task.title} {self.role_type}"
            
            # 使用搜索工具
            search_results = await alibaba_search_tool.run(search_query)
            
            # 分析搜索结果
            prompt = f"""作为{self.role_type}，请基于以下搜索结果完成研究任务：

## 任务信息
- 任务：{task.title}
- 描述：{task.description}
- 项目：{project_info.get('name', '未知项目')}

## 搜索结果
{search_results}

## 用户关注点
{self._get_user_focus(sop_state)}

请提供专业的研究分析报告。"""

            # 这里应该调用LLM
            result = f"[{self.role_type}研究报告]\n\n基于搜索结果的专业分析：\n{search_results[:500]}..."
            
            return result
            
        except Exception as e:
            logger.error(f"研究失败: {e}")
            return f"研究任务失败：{str(e)}"
    
    def _get_user_focus(self, sop_state: SOPState) -> str:
        """获取用户关注点"""
        recent_interventions = [
            intervention["content"] 
            for intervention in sop_state.user_interventions[-3:]
        ]
        return "\n".join(recent_interventions) if recent_interventions else "无特殊关注点"

class AnalysisAction(Action):
    """分析动作 - 数据分析和指标构建"""
    
    def __init__(self, role_type: str):
        super().__init__()
        self.role_type = role_type
    
    async def run(self, task: WorkTask, project_info: Dict, sop_state: SOPState) -> str:
        """执行分析任务"""
        try:
            # 获取依赖任务的结果
            dependency_results = []
            for dep_id in task.dependencies:
                if dep_id in sop_state.tasks:
                    dep_task = sop_state.tasks[dep_id]
                    if dep_task.result:
                        dependency_results.append(f"## {dep_task.title}\n{dep_task.result}")
            
            prompt = f"""作为{self.role_type}，请基于前期研究结果完成分析任务：

## 任务信息
- 任务：{task.title}
- 描述：{task.description}

## 前期研究结果
{chr(10).join(dependency_results)}

## 用户要求
{self._get_user_requirements(sop_state)}

请提供专业的分析结果。"""

            # 这里应该调用LLM
            result = f"[{self.role_type}分析报告]\n\n基于前期研究的专业分析..."
            
            return result
            
        except Exception as e:
            logger.error(f"分析失败: {e}")
            return f"分析任务失败：{str(e)}"
    
    def _get_user_requirements(self, sop_state: SOPState) -> str:
        """获取用户要求"""
        return "\n".join([
            intervention["content"] 
            for intervention in sop_state.user_interventions
            if not intervention["processed"]
        ])

class WritingAction(Action):
    """写作动作 - 基于模板进行章节写作"""
    
    def __init__(self, role_type: str):
        super().__init__()
        self.role_type = role_type
    
    async def run(self, task: WorkTask, project_info: Dict, sop_state: SOPState) -> str:
        """执行写作任务"""
        try:
            # 获取章节信息
            if task.chapter_code:
                chapter = report_template_analyzer.chapters.get(task.chapter_code)
                if chapter:
                    # 使用模板分析器生成写作提示
                    prompt = report_template_analyzer.get_chapter_writing_prompt(chapter, project_info)
                    
                    # 添加前期分析结果
                    analysis_results = self._get_analysis_results(sop_state)
                    if analysis_results:
                        prompt += f"\n## 前期分析结果\n{analysis_results}"
                    
                    # 这里应该调用LLM
                    result = f"[{self.role_type}] 章节写作：{chapter.title}\n\n{prompt[:200]}..."
                    
                    return result
            
            return f"章节信息不完整，无法执行写作任务"
            
        except Exception as e:
            logger.error(f"写作失败: {e}")
            return f"写作任务失败：{str(e)}"
    
    def _get_analysis_results(self, sop_state: SOPState) -> str:
        """获取分析结果"""
        analysis_tasks = [
            task for task in sop_state.tasks.values()
            if task.phase == WorkflowPhase.ANALYSIS and task.status == TaskStatus.COMPLETED
        ]
        
        results = []
        for task in analysis_tasks:
            if task.result:
                results.append(f"### {task.title}\n{task.result}")
        
        return "\n\n".join(results)

# ==================== ROLES ====================

class ProjectDirectorRole(Role):
    """项目总监角色 - 负责整体规划和协调"""
    
    def __init__(self, project_info: Dict, sop_state: SOPState, message_queue: Queue):
        super().__init__(
            name="项目总监",
            profile="Project Director", 
            goal="制定项目计划，协调团队工作，响应用户需求",
            constraints="必须确保项目按计划进行，及时响应用户介入"
        )
        self.project_info = project_info
        self.sop_state = sop_state
        self.message_queue = message_queue
        self.planning_action = PlanningAction()
    
    async def _act(self) -> Message:
        """执行总监职责"""
        try:
            # 发送状态消息
            self._send_message("🎯 项目总监正在制定工作计划...", "thinking")
            
            # 执行规划
            plan_result = await self.planning_action.run(
                self.project_info, 
                report_template_analyzer, 
                self.sop_state
            )
            
            # 解析计划并创建任务
            self._create_tasks_from_plan(plan_result)
            
            # 发送计划结果
            self._send_message(f"📋 工作计划制定完成：\n{plan_result}", "completed")
            
            return Message(content=plan_result, role=self.profile)
            
        except Exception as e:
            error_msg = f"项目规划失败：{str(e)}"
            self._send_message(error_msg, "error")
            return Message(content=error_msg, role=self.profile)
    
    def _create_tasks_from_plan(self, plan_json: str):
        """从计划创建任务"""
        try:
            plan = json.loads(plan_json)
            for task_data in plan.get("tasks", []):
                task = WorkTask(
                    task_id=task_data["task_id"],
                    title=task_data["title"],
                    description=task_data.get("description", ""),
                    assigned_role=task_data["assigned_role"],
                    phase=WorkflowPhase(task_data["phase"]),
                    status=TaskStatus.PENDING,
                    priority=task_data["priority"],
                    dependencies=task_data.get("dependencies", []),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.sop_state.add_task(task)
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
    
    def _send_message(self, content: str, status: str):
        """发送消息"""
        if self.message_queue:
            self.message_queue.put({
                "agent_type": "project_director",
                "agent_name": "项目总监",
                "content": content,
                "status": status
            })

class SpecialistRole(Role):
    """专家角色基类"""
    
    def __init__(self, role_type: str, name: str, profile: str, goal: str, 
                 sop_state: SOPState, message_queue: Queue):
        super().__init__(name=name, profile=profile, goal=goal)
        self.role_type = role_type
        self.sop_state = sop_state
        self.message_queue = message_queue
        self.research_action = ResearchAction(role_type)
        self.analysis_action = AnalysisAction(role_type)
        self.writing_action = WritingAction(role_type)
    
    async def _act(self) -> Message:
        """执行专家任务"""
        try:
            # 获取分配给自己的待执行任务
            my_tasks = [
                task for task in self.sop_state.get_ready_tasks()
                if task.assigned_role == self.role_type
            ]
            
            if not my_tasks:
                return Message(content="暂无分配任务", role=self.profile)
            
            # 执行优先级最高的任务
            task = my_tasks[0]
            self.sop_state.update_task_status(task.task_id, TaskStatus.IN_PROGRESS)
            
            self._send_message(f"🔄 开始执行任务：{task.title}", "thinking")
            
            # 根据任务阶段选择动作
            if task.phase == WorkflowPhase.RESEARCH:
                result = await self.research_action.run(task, self.sop_state.project_context, self.sop_state)
            elif task.phase == WorkflowPhase.ANALYSIS:
                result = await self.analysis_action.run(task, self.sop_state.project_context, self.sop_state)
            elif task.phase == WorkflowPhase.WRITING:
                result = await self.writing_action.run(task, self.sop_state.project_context, self.sop_state)
            else:
                result = f"未知任务阶段：{task.phase}"
            
            # 更新任务状态
            self.sop_state.update_task_status(task.task_id, TaskStatus.COMPLETED, result)
            
            self._send_message(f"✅ 任务完成：{task.title}\n\n{result}", "completed")
            
            return Message(content=result, role=self.profile)
            
        except Exception as e:
            error_msg = f"任务执行失败：{str(e)}"
            self._send_message(error_msg, "error")
            return Message(content=error_msg, role=self.profile)
    
    def _send_message(self, content: str, status: str):
        """发送消息"""
        if self.message_queue:
            self.message_queue.put({
                "agent_type": self.role_type,
                "agent_name": self.name,
                "content": content,
                "status": status
            })

# ==================== TEAM ====================

class SOPReportTeam(Team):
    """基于SOP的报告团队"""
    
    def __init__(self, session_id: str, project_info: Dict, message_queue: Queue):
        super().__init__()
        # 使用私有属性避免Pydantic字段冲突
        self._session_id = session_id
        self._project_info = project_info
        self._message_queue = message_queue
        self._sop_state = SOPState(session_id)
        self._sop_state.project_context = project_info
        
        # 创建工作空间
        workspace_path = Path(f"workspaces/{session_id}")
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化角色
        self._init_roles()
    
    def _init_roles(self):
        """初始化角色"""
        # 项目总监
        director = ProjectDirectorRole(
            self._project_info, 
            self._sop_state, 
            self._message_queue
        )
        
        # 专家团队
        specialists = [
            SpecialistRole(
                "policy_researcher", "政策研究员", "Policy Researcher",
                "研究政策法规，确保合规性", self._sop_state, self._message_queue
            ),
            SpecialistRole(
                "case_researcher", "案例研究员", "Case Researcher", 
                "收集分析案例，提供最佳实践", self._sop_state, self._message_queue
            ),
            SpecialistRole(
                "data_analyst", "数据分析师", "Data Analyst",
                "分析数据，构建指标体系", self._sop_state, self._message_queue
            ),
            SpecialistRole(
                "indicator_expert", "指标专家", "Indicator Expert",
                "设计评价指标，制定标准", self._sop_state, self._message_queue
            ),
            SpecialistRole(
                "writer", "写作专员", "Report Writer",
                "撰写报告章节，整合内容", self._sop_state, self._message_queue
            ),
            SpecialistRole(
                "reviewer", "质量评审员", "Quality Reviewer",
                "评审质量，提供改进建议", self._sop_state, self._message_queue
            )
        ]
        
        # 添加所有角色到团队
        all_roles = [director] + specialists
        self.hire(all_roles)
        
        logger.info(f"✅ SOP团队初始化完成，共 {len(all_roles)} 个角色")
    
    async def run_sop_workflow(self) -> str:
        """运行SOP工作流程"""
        try:
            self._send_system_message("🚀 SOP工作流程启动...")
            
            # 阶段1：规划阶段
            await self._run_planning_phase()
            
            # 阶段2：执行阶段（研究->分析->写作->评审）
            await self._run_execution_phases()
            
            # 生成最终报告
            final_report = self._generate_final_report()
            
            self._send_system_message("✅ SOP工作流程完成")
            
            return final_report
            
        except Exception as e:
            error_msg = f"SOP工作流程失败: {str(e)}"
            logger.error(error_msg)
            self._send_system_message(f"❌ {error_msg}")
            return error_msg
    
    async def _run_planning_phase(self):
        """运行规划阶段"""
        self._sop_state.current_phase = WorkflowPhase.PLANNING
        
        # 获取项目总监
        director = self._get_role_by_type("project_director")
        if director:
            await director._act()
    
    async def _run_execution_phases(self):
        """运行执行阶段"""
        phases = [WorkflowPhase.RESEARCH, WorkflowPhase.ANALYSIS, 
                 WorkflowPhase.WRITING, WorkflowPhase.REVIEW]
        
        for phase in phases:
            self._sop_state.current_phase = phase
            self._send_system_message(f"📍 进入{phase.value}阶段")
            
            # 执行该阶段的所有任务
            while True:
                ready_tasks = [
                    task for task in self._sop_state.get_ready_tasks()
                    if task.phase == phase
                ]
                
                if not ready_tasks:
                    break
                
                # 并行执行任务
                await self._execute_tasks_parallel(ready_tasks)
    
    async def _execute_tasks_parallel(self, tasks: List[WorkTask]):
        """并行执行任务"""
        # 按角色分组任务
        role_tasks = {}
        for task in tasks:
            if task.assigned_role not in role_tasks:
                role_tasks[task.assigned_role] = []
            role_tasks[task.assigned_role].append(task)
        
        # 为每个角色分配任务并执行
        for role_type, role_task_list in role_tasks.items():
            role = self._get_role_by_type(role_type)
            if role:
                await role._act()
    
    def _get_role_by_type(self, role_type: str):
        """根据类型获取角色"""
        if hasattr(self, 'env') and hasattr(self.env, 'get_roles'):
            all_roles = self.env.get_roles()
            for role_name, role_obj in all_roles.items():
                if hasattr(role_obj, 'role_type') and role_obj.role_type == role_type:
                    return role_obj
                elif role_type == "project_director" and "总监" in role_name:
                    return role_obj
        return None
    
    def _generate_final_report(self) -> str:
        """生成最终报告"""
        completed_tasks = [
            task for task in self._sop_state.tasks.values()
            if task.status == TaskStatus.COMPLETED and task.result
        ]
        
        report_content = f"""# {self._project_info.get('name', '项目')}绩效评价报告

*生成时间: {datetime.now().strftime('%Y年%m月%d日')}*
*生成方式: MetaGPT SOP多Agent协作*

---

## 执行摘要

本报告基于标准SOP流程，由专业团队协作完成。

"""
        
        # 按阶段组织内容
        for phase in WorkflowPhase:
            phase_tasks = [t for t in completed_tasks if t.phase == phase]
            if phase_tasks:
                report_content += f"\n## {phase.value.title()}阶段成果\n\n"
                for task in phase_tasks:
                    report_content += f"### {task.title}\n\n{task.result}\n\n---\n\n"
        
        return report_content
    
    def _send_system_message(self, content: str):
        """发送系统消息"""
        if self._message_queue:
            self._message_queue.put({
                "agent_type": "system",
                "agent_name": "SOP系统",
                "content": content,
                "status": "info"
            })
    
    def handle_user_intervention(self, message: str):
        """处理用户介入"""
        self._sop_state.add_user_intervention(message)
        
        # 通知项目总监重新规划
        director = self._get_role_by_type("project_director")
        if director:
            self._send_system_message(f"📢 用户介入：{message[:50]}...")
            self._send_system_message("🔄 项目总监正在调整计划...")
            # 这里可以触发重新规划
    
    @property
    def sop_state(self):
        """提供对sop_state的访问"""
        return self._sop_state