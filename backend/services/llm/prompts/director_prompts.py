"""
DirectorAgent's Prompts
存放智能项目总监(DirectorAgent)所有与LLM交互的提示词模板。
"""
import json
from backend.models.plan import Plan

def get_plan_generation_prompt(formatted_history: str, user_message: str, agent_capabilities: dict) -> str:
    """获取用于生成行动计划的Prompt"""
    return f"""
# 指令
作为一名世界级的AI项目总监，你的任务是将用户的模糊需求，结合对话历史，转化为一个清晰、结构化的JSON格式的行动计划（Plan）。

## 1. 上下文
**对话历史:**
{formatted_history}

**最新用户需求:**
{user_message}

**可用专家能力:**
{json.dumps(agent_capabilities, ensure_ascii=False, indent=2)}

## 2. 你的任务
你需要输出一个JSON对象，该对象遵循Plan和Task的数据模型。

- `goal`: 必须是对用户核心目标的精准概括。
- `tasks`: 一个有序的列表，每个task代表一个为实现goal所需执行的、不可再分的原子步骤。
  - `description`: 必须清晰地描述这个任务“做什么”，语言应面向将要执行它的专家。
  - `dependencies`: 如果一个任务需要等待其他任务完成，在这里列出其依赖的任务`id`。任务`id`应为`task_1`, `task_2`等，方便引用。

## 3. 核心原则
- **What, not How**: `description`只描述做什么，不操心怎么做或谁来做。
- **原子性**: 每个Task都应该是最小的可执行单元。例如，不要创建“撰写报告”这种大任务，应拆分为“分析数据”、“撰写初稿”、“审核内容”等。
- **逻辑性**: 任务列表必须逻辑有序。如果B任务依赖A任务的结果，B必须在A之后，并通过`dependencies`字段声明。
- **全面性**: 计划需要覆盖从开始到结束的所有必要步骤，确保最终能完整地响应用户需求。
- **简单任务处理**: 如果用户只是提问或咨询，计划可以只包含一个任务，如 `description: "回答用户关于写作技巧的问题"`。
- **具体化**: 对于搜索任务，`description`必须是一个具体的查询语句，而不是泛化的描述。例如，"搜索关于Python编程的最新趋势" 比 "搜索最新趋势" 更具体。

## 4. 输出格式
你必须严格按照下面的JSON格式输出，不要有任何多余的文字。

```json
{{
  "goal": "用户的核心目标",
  "tasks": [
    {{
      "id": "task_1",
      "description": "第一个原子任务的清晰描述",
      "dependencies": []
    }},
    {{
      "id": "task_2",
      "description": "第二个原子任务的清晰描述",
      "dependencies": ["task_1"]
    }}
  ]
}}
```

现在，请为用户的最新需求生成行动计划。
"""

def get_plan_revision_prompt(formatted_history: str, original_plan: Plan, user_feedback: str, agent_capabilities: dict) -> str:
    """获取用于修订行动计划的Prompt"""
    return f"""
# 指令
作为一名世界级的AI项目总监，你的任务是根据用户的反馈，修订一个已有的行动计划。

## 1. 上下文
**对话历史:**
{formatted_history}

**原始计划:**
```json
{original_plan.model_dump_json(indent=2)}
```

**用户最新反馈/修改意见:**
{user_feedback}

**可用专家能力:**
{json.dumps(agent_capabilities, ensure_ascii=False, indent=2)}

## 2. 你的任务
你需要输出一个**全新的、修订后的**JSON格式的行动计划（Plan）。

- **整合反馈**: 新计划必须充分整合用户的修改意见。例如，如果用户要求“在第2步之前增加一个数据清洗步骤”，你就必须添加这个新任务并调整后续任务的依赖关系。
- **重新思考**: 不要只做简单的增删。要像一个真正的项目总监一样，思考用户的反馈对整个计划的逻辑和流程意味着什么，并进行系统性的优化。
- **保持原则**: 同样要遵循 **What, not How**、**原子性**、**逻辑性** 和 **全面性** 的原则。

## 3. 输出格式
你必须严格按照下面的JSON格式输出，不要有任何多余的文字。

```json
{{
  "goal": "（可能是修订后的）用户核心目标",
  "tasks": [
    {{
      "id": "task_1",
      "description": "第一个原子任务的清晰描述",
      "dependencies": []
    }},
    {{
      "id": "task_2",
      "description": "第二个原子任务的清晰描述",
      "dependencies": ["task_1"]
    }}
  ]
}}
```

现在，请生成修订后的行动计划。
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