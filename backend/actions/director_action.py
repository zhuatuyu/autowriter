"""
DirectorAgent's Actions
"""
from metagpt.actions import Action
from metagpt.llm import LLM
from metagpt.provider.base_llm import BaseLLM
from typing import Dict, List, Optional, Any
import json
import re
# from backend.models.plan import Plan
from pydantic import ValidationError
from metagpt.logs import logger


class CreatePlan(Action):
    """
    Action to create a plan based on user request.
    """
    name: str = "CreatePlan"

    async def run(self, user_request: str, agent_capabilities: dict) -> Optional[Plan]:
        prompt = self._get_prompt(user_request, agent_capabilities)
        plan_json_str = await self.llm.aask(prompt)
        return self._parse_and_validate_plan(plan_json_str)

    def _get_prompt(self, user_request: str, agent_capabilities: dict) -> str:
        return f"""
# 指令：作为智能项目总监，为用户请求制定一份详尽的、可执行的SOP（Standard Operating Procedure）计划。

## 核心原则
1.  **SOP思维**: 你的输出不是一个简单的任务列表，而是一个完整的、端到端的操作流程。每个步骤都应该是一个独立的、可执行的、原子化的任务。
2.  **明确委派**: 必须为每个任务（Task）精确指定一个最合适的`agent`。
3.  **细粒度拆分**: 将复杂的用户请求拆解成多个逻辑上独立的子任务。例如，一个“研究并报告”的需求，应至少拆分为“搜索”、“总结”、“撰写”等步骤。
4.  **闭环流程**: 确保流程是完整的。例如，有“搜索”任务，就必须有后续的“总结”或“整合”任务；有“撰写”任务，就应该考虑后续的“润色”或“审核”任务。
5.  **依赖管理**: 在任务的`dependencies`字段中明确列出依赖的任务ID。例如，如果task_2需要task_1的结果，则task_2的dependencies应为["task_1"]。在任务的`description`中也应明确提及依赖关系，例如："总结task_1的搜索结果"。
6.  **具体化**: 对于搜索任务，`description`必须是一个具体的查询语句，而不是泛化的描述。例如，"搜索关于Python编程的最新趋势" 比 "搜索最新趋势" 更具体。

## 可用的专家智能体团队
```json
{json.dumps(agent_capabilities, indent=2, ensure_ascii=False)}
```

## 用户最新请求
---
{user_request}
---

## 你的任务
请严格按照以下JSON格式，为用户的最新请求制定一份SOP计划。

```json
{{
  "goal": "这里填写整个计划的最终目标，必须与用户请求紧密相关。",
  "tasks": [
    {{
      "id": "task_1",
      "description": "这里填写第一个原子任务的具体、可执行的描述。例如：'搜索\"数字化城市管理政府购买服务项目的成功案例\"'",
      "agent": "这里精确指定负责此任务的agent_id，例如：'case_expert'",
      "dependencies": []
    }},
    {{
      "id": "task_2",
      "description": "这里填写第二个原子任务。例如：'总结task_1的搜索结果，提炼关键信息'",
      "agent": "这里精确指定负责此任务的agent_id，例如：'writer_expert'",
      "dependencies": ["task_1"]
    }},
    {{
      "id": "task_3",
      "description": "这里填写第三个原子任务。例如：'根据task_2的总结，撰写报告的\"案例分析\"章节'",
      "agent": "writer_expert",
      "dependencies": ["task_2"]
    }}
  ]
}}
```

请立即生成SOP计划JSON。
"""

    def _parse_and_validate_plan(self, plan_json_str: str) -> Optional[Plan]:
        try:
            match = re.search(r"```json\n(.*?)\n```", plan_json_str, re.DOTALL)
            if match:
                plan_json_str = match.group(1)

            plan_data = json.loads(plan_json_str)
            plan = Plan(**plan_data)
            logger.info(f"✅ 计划解析成功，共 {len(plan.tasks)} 个任务。")
            return plan
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"❌ 解析或验证计划失败: {e}\n原始JSON字符串:\n{plan_json_str}")
            return None


class RevisePlan(Action):
    """
    Action to revise a plan based on user feedback.
    """
    name: str = "RevisePlan"

    async def run(self, original_plan: Plan, user_feedback: str, agent_capabilities: dict) -> Optional[Plan]:
        prompt = self._get_prompt(original_plan, user_feedback, agent_capabilities)
        plan_json_str = await self.llm.aask(prompt)
        return self._parse_and_validate_plan(plan_json_str)

    def _get_prompt(self, original_plan: Plan, user_feedback: str, agent_capabilities: dict) -> str:
        return f"""
# 指令：作为智能项目总监，根据用户的反馈修订现有的SOP计划。

## 核心原则
1.  **理解反馈**: 仔细分析用户的反馈，精准定位需要修改的计划部分。
2.  **保持SOP结构**: 修订后的输出必须保持完整的SOP结构，不能只输出修改部分。
3.  **保留有效部分**: 只修改用户要求变更的部分，其余未提及的任务应保持原样。
4.  **严格的字段要求**: 每个任务（Task）都必须包含 `id`, `description`, `agent`, 和 `dependencies` 四个字段，缺一不可。dependencies应正确反映任务间的依赖关系。
5.  **重新编排ID**: 如果你删除或新增了任务，请确保所有任务的 `id` 是从 `task_1` 开始连续编号的。

## 可用的专家智能体团队
```json
{json.dumps(agent_capabilities, indent=2, ensure_ascii=False)}
```

## 待修订的原始计划
```json
{original_plan.model_dump_json(indent=2)}
```

## 用户的修订意见
---
{user_feedback}
---

## 你的任务
请严格按照以下JSON格式，生成一份**完整**的、修订后的SOP计划。

```json
{{
  "goal": "这里填写计划的最终目标，通常保持不变。",
  "tasks": [
    {{
      "id": "task_1",
      "description": "这里填写第一个任务的描述。",
      "agent": "这里必须指定负责此任务的agent_id。",
      "dependencies": []
    }},
    {{
      "id": "task_2",
      "description": "这里填写第二个任务的描述。",
      "agent": "这里必须指定负责此任务的agent_id。",
      "dependencies": ["task_1"]
    }}
  ]
}}
```

请立即生成修订后的SOP计划JSON。
"""

    def _parse_and_validate_plan(self, plan_json_str: str) -> Optional[Plan]:
        try:
            match = re.search(r"```json\n(.*?)\n```", plan_json_str, re.DOTALL)
            if match:
                plan_json_str = match.group(1)

            plan_data = json.loads(plan_json_str)
            plan = Plan(**plan_data)
            logger.info(f"✅ 计划解析成功，共 {len(plan.tasks)} 个任务。")
            return plan
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"❌ 解析或验证计划失败: {e}\n原始JSON字符串:\n{plan_json_str}")
            return None


class DirectAnswer(Action):
    """
    Action to directly answer a user's simple question.
    """
    name: str = "DirectAnswer"

    async def run(self, user_message: str, intent: str) -> str:
        prompt = self._get_prompt(user_message, intent)
        response = await self.llm.aask(prompt)
        return response.strip()

    def _get_prompt(self, user_message: str, intent: str) -> str:
        return f"""
        你是一个智能项目总监，用户向你提出了一个简单的问题。请简洁、友好地回答。
        
        用户问题: {user_message}
        问题类型: {intent}
        
        请直接回答，不要过于复杂。
        """