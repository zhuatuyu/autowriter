"""
DirectorAgent's Prompts
存放智能项目总监(DirectorAgent)所有与LLM交互的提示词模板。
"""
import json
from backend.models.plan import Plan

def get_plan_generation_prompt(formatted_history: str, user_message: str, agent_capabilities: dict) -> str:
    """获取用于生成计划的Prompt"""
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

## 当前对话上下文（最近5条）
---
{formatted_history}
---

## 用户最新请求
---
{user_message}
---

## 你的任务
请严格按照以下JSON格式，为用户的最新请求制定一份SOP计划。

```json
{{
  "goal": "这里填写整个计划的最终目标，必须与用户请求紧密相关。",
  "tasks": [
    {{
      "id": "task_1",
      "description": "这里填写第一个原子任务的具体、可执行的描述。例如：'搜索"数字化城市管理政府购买服务项目的成功案例"'",
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
      "description": "这里填写第三个原子任务。例如：'根据task_2的总结，撰写报告的"案例分析"章节'",
      "agent": "writer_expert",
      "dependencies": ["task_2"]
    }}
  ]
}}
```

请立即生成SOP计划JSON。
"""

def get_plan_revision_prompt(formatted_history: str, original_plan: Plan, user_feedback: str, agent_capabilities: dict) -> str:
    """获取用于修订计划的Prompt"""
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

## 当前对话上下文
---
{formatted_history}
---

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

def get_direct_answer_prompt(formatted_history: str, user_message: str, intent: str, team_summary: dict = None) -> str:
    """获取用于直接回答问题的Prompt"""
    if intent == 'status_inquiry':
        status_context = json.dumps(team_summary, ensure_ascii=False, indent=2) if team_summary else "暂无项目状态信息。"
        return f"""
# 指令：作为AI项目总监，根据上下文和当前项目状态，回答用户的状态查询。

## 对话历史
{formatted_history}

## 当前项目状态摘要
{status_context}

## 用户问题
"{user_message}"

---
请用人性化的语言，清晰地回答用户关于项目进展的问题。
"""
    else: #  trivial_chat, simple_qa, contextual_follow_up
        return f"""
# 指令：作为AI项目总监，根据上下文，用人性化、专业的语言回答用户的问题。

## 对话历史
{formatted_history}

## 用户最新消息
"{user_message}"

---
请直接回答用户。如果是闲聊，请礼貌回应；如果是问题，请提供简洁、准确的答案；如果是追问，请结合上下文进行解释。
"""

def get_intent_classification_prompt(formatted_history: str, user_message: str, pending_plan_str: str = None) -> str:
    """获取用于用户意图分类的Prompt"""
    plan_context_str = ""
    if pending_plan_str:
        plan_context_str = f"\\n---\\n## 待审批的计划\\n你已经向用户提出了以下计划，正在等待用户反馈：\\n{pending_plan_str}\\n---"

    return f"""
# 指令：分析用户意图

根据对话历史和用户最新消息，将用户意图分类到以下类别之一。

## 对话历史
{formatted_history}
{plan_context_str}
## 用户最新消息
"{user_message}"

## 意图类别
1.  **trivial_chat**: 简单的问候、感谢或无关的闲聊。 (例如: "你好", "谢谢你", "今天天气不错")
2.  **simple_qa**: 关于某个主题的直接问题，可以由专家一次性回答，不需要多步骤计划。(例如: "绩效报告的关键要素是什么？", "写摘要有什么技巧？")
3.  **contextual_follow_up**: 对上一轮对话的追问，依赖紧密的上下文。(例如: "继续说", "详细解释一下", "为什么？")
4.  **status_inquiry**: 查询项目或任务的当前状态。(例如: "我们上次聊到哪了?", "报告写得怎么样了？")
5.  **planning_request**: 提出一个需要多个步骤或多个专家协作才能完成的复杂需求。(例如: "帮我写一份关于XX的报告", "分析一下这份文件并给出改进建议")
6.  **plan_feedback**: (仅当存在'待审批的计划'时) 用户对你提出的计划进行反馈，无论是同意、否定还是提出修改意见。

请只输出最匹配的意图类别名称（例如: `planning_request`）。
""" 