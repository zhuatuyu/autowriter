"""
智能项目总监Agent
负责项目协调、需求分析和任务分配
"""
import asyncio
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger

from .base import BaseAgent
from backend.services.llm_provider import llm

class ProjectPlanningAction(Action):
    """项目规划动作"""
    
    async def run(self, user_requirements: str) -> str:
        """生成项目规划"""
        prompt = f"""
基于用户需求生成详细的项目规划YAML模板：

用户需求：
{user_requirements}

请生成包含以下结构的YAML：
- report_title: 报告标题
- report_type: 报告类型
- chapters: 章节列表，每个章节包含title, description, experts, status

只返回YAML内容，不要包含其他说明。
"""
        try:
            response = await llm.acreate_text(prompt)
            return response.strip().replace("```yaml", "").replace("```", "").strip()
        except Exception as e:
            logger.error(f"项目规划生成失败: {e}")
            return ""


class TaskCoordinationAction(Action):
    """任务协调动作"""
    
    async def run(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """协调任务分配"""
        return {
            'status': 'coordinated',
            'assigned_agents': task_info.get('experts', []),
            'priority': task_info.get('priority', 'normal')
        }


class IntelligentDirectorAgent(BaseAgent):
    """智能项目总监Agent - 负责动态规划、协调和决策"""
    
    def __init__(self, session_id: str, workspace_path: str):
        agent_id = 'director'
        super().__init__(
            agent_id=agent_id,
            session_id=session_id,
            workspace_path=workspace_path,
            goal="协调AI团队完成高质量报告写作，确保项目顺利进行",
            constraints="基于用户需求制定合理计划，确保任务分配得当"
        )
        
        # 设置profile（避免重复传递）
        self.profile = "智能项目总监"
        
        # 设置总监信息
        self.name = '智能项目总监'
        self.avatar = '🎯'
        self.expertise = "项目管理与协调"
        
        # 设置动作
        self.set_actions([ProjectPlanningAction, TaskCoordinationAction])
        
        # 项目文件路径
        self.template_path = self.agent_workspace / "dynamic_template.yaml"
        self.draft_path = self.agent_workspace / "drafts"
        self.draft_path.mkdir(exist_ok=True)
        self.report_data = None
        
        logger.info(f"🎯 智能项目总监初始化完成")

    def _get_system_prompt(self) -> str:
        """动态构建系统提示词"""
        return """
你是AutoWriter Enhanced系统的智能项目总监，一个世界级的项目经理和需求分析师。

## 你的职责：
1.  **主动沟通与需求挖掘**：你是与用户沟通的唯一接口。你必须主动、清晰地向用户提问，以完全理解他们的需求。不要满足于模糊的指令。
2.  **动态规划 (MVP)**：基于用户需求，制定一个“最小可行”的报告框架（YAML格式）。这个框架应包含报告标题、类型和核心章节。
3.  **层级化任务分解**：将每个章节分解为一系列具体的、可执行的子任务。每个子任务都必须明确指出需要哪位专家、需要什么输入、预期产出是什么。
4.  **智能任务分配**：根据子任务的性质，精确地将其分配给最合适的专家（文档专家、案例专家等）。
5.  **进度监控与质量把控**：持续跟踪任务进度，并在每个关键节点审核工作成果，确保最终报告的质量。
6.  **持久化记忆**：你必须能够加载和理解项目历史（如旧的模板和产出），在现有工作的基础上继续推进。

## 沟通风格：
- 专业、主动、循循善诱。像一个真正的咨询顾问那样与用户对话。
- 清晰明确地传达你的计划和下一步行动。
"""

    async def _generate_dynamic_template_prompt(self, user_message: str) -> str:
        """为生成动态模板动态构建提示词"""
        # 在未来，这里可以整合更多上下文信息，如历史对话、已知项目信息等
        return f"""
用户初步需求如下:
---
{user_message}
---
基于以上初步需求，请为一份绩效评价报告设计一个详细的YAML格式的写作大纲。
这个大纲将作为我们与用户进一步讨论的基础。
要求包含 report_title, report_type, 以及一个 chapters 列表。
每个 chapter 需要有:
- title: 章节标题
- description: 对章节内容的简要描述
- experts: 建议参与该章节的专家角色列表 (从 'document_expert', 'case_expert', 'data_analyst', 'writer_expert' 中选择)
- status: 初始状态为 'pending'
- draft_content: 初始为空字符串

请只返回YAML内容，不要包含任何其他解释性文字或代码块标记。
"""

    async def _send_message(self, content: str, status: str, websocket_manager):
        """通过WebSocket发送消息的辅助函数"""
        if websocket_manager:
            await websocket_manager.broadcast_agent_message(
                session_id=self.session_id,
                agent_type='intelligent_director',
                agent_name=self.name,
                content=content,
                status=status
            )

    async def handle_request(self, user_message: str, team: dict, websocket_manager=None):
        """处理用户请求的核心入口，包含完整的动态规划和执行流程"""
        try:
            self.status = 'working'
            await self._send_message("👋 您好！我是您的项目总监。正在分析您的需求...", "thinking", websocket_manager)

            # 步骤 1: 生成动态模板
            await self._generate_dynamic_template(user_message, websocket_manager)
            
            # 步骤 2: 加载模板并与用户确认
            self.report_data = self._load_template()
            template_overview = self._format_template_for_display(self.report_data)
            await self._send_message(f"您的报告计划已生成：\n{template_overview}\n\n**如果满意，请回复“开始写作”**", "waiting_for_input", websocket_manager)
            
            # 此处简化流程，默认用户会同意。未来这里会等待用户的WebSocket消息。
            # 实际场景下，如果用户回复“开始写作”，下面的流程才继续。

        except Exception as e:
            error_message = f"❌ 在规划阶段发生错误: {e}"
            print(error_message)
            self.status = 'error'
            await self._send_message(error_message, "error", websocket_manager)

    async def _generate_dynamic_template(self, user_message: str, websocket_manager):
        """使用LLM生成动态YAML模板"""
        await self._send_message("🧠 正在进行智能规划...", "working", websocket_manager)
        prompt = await self._generate_dynamic_template_prompt(user_message)
        response = await llm.acreate_text(prompt)
        yaml_content = response.strip().replace("```yaml", "").replace("```", "").strip()
        self.report_data = yaml.safe_load(yaml_content)
        for i, chapter in enumerate(self.report_data.get('chapters', [])):
            chapter['id'] = f"ch_{i+1:02d}"
        self._save_template()
        await self._send_message("✅ 动态报告模板已生成！", "completed", websocket_manager)

    def _load_template(self):
        """加载YAML模板"""
        if self.template_path.exists():
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return None

    def _save_template(self):
        """保存模板数据到YAML"""
        if self.report_data:
            with open(self.template_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.report_data, f, allow_unicode=True, sort_keys=False)

    def _format_template_for_display(self, template_data: dict) -> str:
        """格式化模板以便于展示"""
        if not template_data: return "模板数据为空。"
        title = template_data.get('report_title', '未知标题')
        chapters = template_data.get('chapters', [])
        display_text = f"**报告标题**: {title}\n\n**核心章节**:\n"
        for i, ch in enumerate(chapters):
            experts = ", ".join(ch.get('experts', []))
            display_text += f"  - **第{i+1}章: {ch['title']}** (需: {experts})\n"
        return display_text
    
    async def get_work_summary(self) -> str:
        """获取工作摘要"""
        try:
            summary = f"🎯 {self.name} 工作摘要:\n"
            
            if self.report_data:
                title = self.report_data.get('report_title', '未知项目')
                chapters = len(self.report_data.get('chapters', []))
                summary += f"• 当前项目: {title}\n"
                summary += f"• 规划章节: {chapters} 个\n"
            else:
                summary += f"• 当前项目: 暂无活跃项目\n"
            
            summary += f"• 当前状态: {self.status}\n"
            
            if self.current_task:
                summary += f"• 当前任务: {self.current_task}\n"
            
            return summary
            
        except Exception as e:
            return f"🎯 {self.name}: 工作摘要获取失败 - {str(e)}"

    async def _execute_specific_task(self, task: Dict[str, Any], context: str) -> Dict[str, Any]:
        """执行具体的项目管理任务"""
        try:
            task_type = task.get('type', 'handle_request')
            
            if task_type == 'handle_request':
                return await self._handle_user_request(task)
            elif task_type == 'generate_plan':
                return await self._generate_project_plan(task)
            elif task_type == 'coordinate_team':
                return await self._coordinate_team_tasks(task)
            else:
                return await self._handle_user_request(task)
                
        except Exception as e:
            logger.error(f"❌ {self.name} 执行任务失败: {e}")
            return {
                'agent_id': self.agent_id,
                'status': 'error',
                'result': f'任务执行失败: {str(e)}',
                'error': str(e)
            }

    async def _handle_user_request(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理用户请求"""
        try:
            user_message = task.get('message', '')
            self.current_task = f"处理用户需求: {user_message[:50]}..."
            
            # 生成项目规划
            planning_action = ProjectPlanningAction()
            yaml_content = await planning_action.run(user_message)
            
            if yaml_content:
                self.report_data = yaml.safe_load(yaml_content)
                self._save_template()
                
                result = {
                    'agent_id': self.agent_id,
                    'status': 'completed',
                    'result': f"已为您生成项目规划：{self.report_data.get('report_title', '报告')}",
                    'project_plan': self.report_data,
                    'template_file': str(self.template_path),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                result = {
                    'agent_id': self.agent_id,
                    'status': 'error',
                    'result': "项目规划生成失败",
                    'timestamp': datetime.now().isoformat()
                }
                
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 处理用户请求失败: {e}")
            return {'status': 'error', 'result': str(e)}

    async def _generate_project_plan(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """生成项目计划的专用任务"""
        return await self._handle_user_request(task)

    async def _coordinate_team_tasks(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """协调团队任务"""
        # 在这里实现任务协调逻辑
        return {'status': 'completed', 'result': '团队任务已协调'}
   