"""
CoreManager's Prompts
存放核心管理器(CoreManager)所有与LLM交互的提示词模板。
"""

def get_intent_classification_prompt(formatted_history: str, user_message: str, pending_plan_str: str = None) -> str:
    """获取用于用户意图分类的Prompt"""
    plan_context_str = ""
    if pending_plan_str:
        plan_context_str = f"\n---\n## 待审批的计划\n你已经向用户提出了以下计划，正在等待用户反馈：\n{pending_plan_str}\n---"

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