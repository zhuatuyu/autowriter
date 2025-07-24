"""
增强版智能项目总监Agent - 基于MetaGPT设计理念
具备深度客户沟通、智能任务规划和动态Agent编排能力
"""
from metagpt.roles import Role
from metagpt.schema import Message, Plan, Task
from metagpt.logs import logger
from metagpt.strategy.planner import Planner
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from backend.services.llm.agents.base import BaseAgent
from backend.models.plan import Plan, Task
from metagpt.llm import LLM
import re

# 导入新的Prompt模块
from backend.services.llm.prompts import director_prompts


class DirectorAgent(BaseAgent):
    """
    🎯 智能项目总监 - 虚拟办公室的核心管理者
    
    新版职责:
    1. 深度客户沟通，理解用户战略意图
    2. 将用户需求转化为结构化的Plan和Tasks
    3. 不负责具体执行，只负责规划"What"
    """
    
    def __init__(self, session_id: str, workspace_path: str, memory_manager=None):
        super().__init__(
            agent_id="director",
            session_id=session_id,
            workspace_path=workspace_path,
            memory_manager=memory_manager,
            profile="智能项目总监",
            goal="与客户深度沟通，制定项目行动计划"
        )
        self.llm = LLM()
        self.role = "项目管理和客户沟通专家"
        self.agent_capabilities = self._initialize_capabilities()

    def _initialize_capabilities(self):
        """初始化Agent能力映射, 用于辅助LLM生成规划"""
        return {
            "document_expert": {
                "name": "文档专家李心悦",
                "responsibilities": ["处理用户上传的文档", "格式转换", "内容摘要", "文档检索", "从文档中提取信息", "管理历史文档"]
            },
            "case_expert": {
                "name": "案例专家王磊", 
                "responsibilities": ["根据主题搜索网络案例", "分析行业最佳实践", "提供外部参考资料"]
            },
            "data_analyst": {
                "name": "数据分析师赵丽娅",
                "responsibilities": ["从数据源提取数据", "进行统计分析", "生成数据图表", "计算和解读指标"]
            },
            "writer_expert": {
                "name": "写作专家张翰",
                "responsibilities": ["撰写报告的特定章节", "润色文本", "优化内容结构", "根据大纲创作内容"]
            },
            "chief_editor": {
                "name": "总编辑钱敏",
                "responsibilities": ["审核报告整体质量", "把控内容一致性", "校验格式规范", "进行最终定稿"]
            },
            "director": {
                "name": "智能项目总监",
                "responsibilities": ["回答用户关于项目管理、报告撰写技巧等专业问题", "提供咨询建议", "澄清用户需求"]
            }
        }
    
    async def process_request(self, user_message: str) -> Plan:
        """
        处理用户请求，生成一个行动计划 (Plan)
        """
        # 1. 记录用户消息
        self._record_user_message(user_message)

        # 2. 调用LLM生成规划
        plan = await self._generate_plan(user_message)
        
        # 3. 记录自己的思考过程和规划
        self._record_assistant_plan(plan)
        
        return plan

    def _record_user_message(self, user_message: str):
        """记录用户消息到统一记忆"""
        if hasattr(self, '_memory_adapter') and self._memory_adapter:
            self._memory_adapter.add_simple_message(content=user_message, role="user", cause_by="user_input")

    def _record_assistant_plan(self, plan: Plan):
        """记录助手的规划到统一记忆"""
        if hasattr(self, '_memory_adapter') and self._memory_adapter:
            plan_summary = f"已为您的需求制定了计划：'{plan.goal}'，包含 {len(plan.tasks)} 个步骤。"
            self._memory_adapter.add_simple_message(
                content=plan_summary,
                role=self.profile,
                cause_by="assistant_planning"
            )

    async def _generate_plan(self, user_message: str) -> Plan:
        """
        使用LLM将用户需求转化为结构化的Plan对象
        """
        context_summary = self._memory_adapter.get_conversation_history(limit=10)
        formatted_history = "\n".join([f"{msg.get('role')}: {msg.get('content')}" for msg in context_summary])

        # 使用新的Prompt模块
        prompt = director_prompts.get_plan_generation_prompt(
            formatted_history=formatted_history,
            user_message=user_message,
            agent_capabilities=self.agent_capabilities
        )
        
        response_json_str = await self.llm.aask(prompt)
        
        try:
            # 提取```json ... ```块中的内容
            match = re.search(r"```json\s*([\s\S]*?)\s*```", response_json_str)
            if match:
                json_str = match.group(1)
            else:
                json_str = response_json_str

            plan_dict = json.loads(json_str)
            
            # 使用Pydantic模型进行验证和转换
            plan = Plan(
                goal=plan_dict.get("goal", user_message),
                tasks=[Task(**task_data) for task_data in plan_dict.get("tasks", [])]
            )
            return plan
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"无法解析LLM返回的Plan JSON: {e}\n原始返回: {response_json_str}")
            # 创建一个回退计划
            return Plan(
                goal=f"处理用户请求: {user_message}",
                tasks=[Task(id="task_1", description=f"直接回应用户关于'{user_message}'的请求")]
            )

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    async def revise_plan(self, original_plan: Plan, user_feedback: str) -> Plan:
        """
        根据用户的反馈修订计划
        """
        logger.info(f"🎯 根据用户反馈修订计划: {user_feedback}")
        context_summary = self._memory_adapter.get_conversation_history(limit=10)
        formatted_history = "\n".join([f"{msg.get('role')}: {msg.get('content')}" for msg in context_summary])

        # 使用新的Prompt模块
        prompt = director_prompts.get_plan_revision_prompt(
            formatted_history=formatted_history,
            original_plan=original_plan,
            user_feedback=user_feedback,
            agent_capabilities=self.agent_capabilities
        )
        
        response_json_str = await self.llm.aask(prompt)
        
        try:
            match = re.search(r"```json\s*([\s\S]*?)\s*```", response_json_str)
            if match:
                json_str = match.group(1)
            else:
                json_str = response_json_str

            plan_dict = json.loads(json_str)
            
            plan = Plan(
                goal=plan_dict.get("goal", original_plan.goal),
                tasks=[Task(**task_data) for task_data in plan_dict.get("tasks", [])]
            )
            # 记录修订后的计划
            self._record_assistant_plan(plan)
            return plan
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"无法解析LLM返回的修订版Plan JSON: {e}\n原始返回: {response_json_str}")
            # 如果修订失败，返回原始计划
            return original_plan

    async def direct_answer(self, user_message: str, intent: str) -> str:
        """
        直接回答用户的非规划类问题
        """
        logger.info(f"🎯 直接回答用户问题, 意图: {intent}, 内容: {user_message}")
        
        # 1. 准备上下文
        history = self._memory_adapter.get_conversation_history(limit=10)
        formatted_history = "\n".join([f"{msg.get('role')}: {msg.get('content')}" for msg in history])
        
        # 2. 根据不同意图，构建不同的prompt
        team_summary = None
        if intent == 'status_inquiry':
            team_summary = self._memory_adapter.get_team_summary()
            
        # 使用新的Prompt模块
        prompt = director_prompts.get_direct_answer_prompt(
            formatted_history=formatted_history,
            user_message=user_message,
            intent=intent,
            team_summary=team_summary
        )
            
        # 3. 调用LLM生成答案
        answer = await self.llm.aask(prompt)
        
        # 4. 记录交互
        self._record_user_message(user_message)
        self._memory_adapter.add_simple_message(content=answer, role=self.profile, cause_by=f"direct_answer_{intent}")
        
        return answer.strip()