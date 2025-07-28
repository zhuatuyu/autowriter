"""
增强版智能项目总监Agent - 基于MetaGPT设计理念
具备深度客户沟通、智能任务规划和动态Agent编排能力
"""
from metagpt.roles.role import Role
from metagpt.schema import Message, Plan, Task
from metagpt.logs import logger
from metagpt.strategy.planner import Planner
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from backend.models.plan import Plan, Task
from metagpt.llm import LLM
import re
from pydantic import ValidationError

# 导入新的Prompt模块
from backend.actions.director_action import CreatePlan, RevisePlan, DirectAnswer


class DirectorAgent(Role):
    """
    🎯 项目总监（吴丽） - 核心规划角色
    职责：
    1. 理解用户的高层级需求。
    2. 生成结构化的、可执行的行动计划 (Plan对象)。
    3. 根据用户反馈修订行动计划。
    """
    def __init__(self, name: str = "Director", profile: str = "Director", goal: str = "...", **kwargs):
        super().__init__(name=name, profile=profile, goal=goal, actions=[CreatePlan(), RevisePlan(), DirectAnswer()], **kwargs)

    async def process_request(self, user_request: str) -> Optional[Plan]:
        """
        处理用户请求，生成初始计划
        """
        agent_capabilities = {
            "case_expert": "王磊 - 专业案例分析师，擅长搜集、分析同类项目的成功案例",
            "writer_expert": "张翰 - 内容创作专家，负责报告撰写、内容润色和优化",
            "data_analyst": "赵丽娅 - 数据分析师，负责数据分析、图表制作和量化评估"
        }
        # 使用MetaGPT原生方式执行action
        action = CreatePlan()
        result = await action.run(user_request=user_request, agent_capabilities=agent_capabilities)
        return result

    async def revise_plan(self, original_plan: Plan, user_feedback: str) -> Optional[Plan]:
        """
        根据用户反馈修订计划
        """
        agent_capabilities = {
            "case_expert": "王磊 - 专业案例分析师，擅长搜集、分析同类项目的成功案例",
            "writer_expert": "张翰 - 内容创作专家，负责报告撰写、内容润色和优化",
            "data_analyst": "赵丽娅 - 数据分析师，负责数据分析、图表制作和量化评估"
        }
        # 使用MetaGPT原生方式执行action
        action = RevisePlan()
        result = await action.run(original_plan=original_plan, user_feedback=user_feedback, agent_capabilities=agent_capabilities)
        return result



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
        # 使用MetaGPT原生方式执行action
        action = DirectAnswer()
        result = await action.run(user_message=user_message, intent=intent)
        return result