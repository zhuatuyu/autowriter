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
from backend.roles.base import BaseAgent
from backend.models.plan import Plan, Task
from metagpt.llm import LLM
import re
from pydantic import ValidationError

# 导入新的Prompt模块
from backend.prompts import director_prompts


class DirectorAgent(BaseAgent):
    """
    🎯 项目总监（吴丽） - 核心规划角色
    职责：
    1. 理解用户的高层级需求。
    2. 生成结构化的、可执行的行动计划 (Plan对象)。
    3. 根据用户反馈修订行动计划。
    """
    def __init__(self, agent_id: str = "director", session_id: str = None, workspace_path: str = None, memory_manager=None):
        super().__init__(
            agent_id=agent_id,
            session_id=session_id,
            workspace_path=workspace_path,
            memory_manager=memory_manager,
            role="智能项目总监",
            profile="吴丽",
            goal="将用户需求转化为清晰、可执行的多智能体协作计划",
        )
        self.llm = LLM()

    async def process_request(self, user_request: str) -> Optional[Plan]:
        """
        处理用户请求，生成初始计划
        """
        # 构建agent能力描述
        agent_capabilities = {
            "case_expert": "王磊 - 专业案例分析师，擅长搜集、分析同类项目的成功案例",
            "document_expert": "李心悦 - 文档管理专家，负责文档上传、解析和管理",
            "writer_expert": "张翰 - 内容创作专家，负责报告撰写、内容润色和优化",
            "data_analyst": "赵丽娅 - 数据分析师，负责数据分析、图表制作和量化评估"
        }
        
        # 格式化历史记录（简化实现，这里暂时为空）
        formatted_history = ""
        
        prompt = director_prompts.get_plan_generation_prompt(formatted_history, user_request, agent_capabilities)
        plan_json_str = await self.llm.aask(prompt)
        return self._parse_and_validate_plan(plan_json_str)

    async def revise_plan(self, original_plan: Plan, user_feedback: str) -> Optional[Plan]:
        """
        根据用户反馈修订计划
        """
        # 构建agent能力描述（与process_request保持一致）
        agent_capabilities = {
            "case_expert": "王磊 - 专业案例分析师，擅长搜集、分析同类项目的成功案例",
            "document_expert": "李心悦 - 文档管理专家，负责文档上传、解析和管理",
            "writer_expert": "张翰 - 内容创作专家，负责报告撰写、内容润色和优化",
            "data_analyst": "赵丽娅 - 数据分析师，负责数据分析、图表制作和量化评估"
        }
        
        # 格式化历史记录（简化实现，这里暂时为空）
        formatted_history = ""
        
        prompt = director_prompts.get_plan_revision_prompt(formatted_history, original_plan, user_feedback, agent_capabilities)
        plan_json_str = await self.llm.aask(prompt)
        return self._parse_and_validate_plan(plan_json_str)

    def _parse_and_validate_plan(self, plan_json_str: str) -> Optional[Plan]:
        """
        解析并验证LLM生成的计划JSON
        """
        try:
            # 从LLM可能返回的markdown代码块中提取纯JSON
            match = re.search(r"```json\n(.*?)\n```", plan_json_str, re.DOTALL)
            if match:
                plan_json_str = match.group(1)

            plan_data = json.loads(plan_json_str)
            
            # 使用Pydantic模型进行验证
            plan = Plan(**plan_data)
            logger.info(f"✅ 计划解析成功，共 {len(plan.tasks)} 个任务。")
            return plan
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"❌ 解析或验证计划失败: {e}\n原始JSON字符串:\n{plan_json_str}")
            return None

    def _format_plan_for_display(self, plan: Plan) -> str:
        """
        格式化计划以便在前端展示 (这个方法仍然需要，但由Orchestrator调用)
        """
        response = f"**我已经为您制定了如下行动计划，请您审阅：**\n\n"
        response += f"**🎯 最终目标:** {plan.goal}\n\n"
        response += "**📝 步骤如下:**\n"
        
        # 简化的agent名称映射
        agent_name_map = {
            "case_expert": "王磊(案例专家)",
            "writer_expert": "张翰(写作专家)", 
            "document_expert": "李心悦(文档专家)",
            "data_analyst": "赵丽娅(数据分析师)"
        }

        for i, task in enumerate(plan.tasks, 1):
            agent_name = agent_name_map.get(task.agent, task.agent)
            response += f"{i}. @{agent_name} {task.description}\n"
        return response

    async def direct_answer(self, user_message: str, intent: str) -> str:
        """
        直接回答用户的简单问题 (保留此方法以兼容现有调用)
        """
        prompt = f"""
        你是一个智能项目总监，用户向你提出了一个简单的问题。请简洁、友好地回答。
        
        用户问题: {user_message}
        问题类型: {intent}
        
        请直接回答，不要过于复杂。
        """
        
        response = await self.llm.aask(prompt)
        return response.strip()