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

        prompt = f"""
# 指令
作为一名世界级的AI项目总监，你的任务是将用户的模糊需求，结合对话历史，转化为一个清晰、结构化的JSON格式的行动计划（Plan）。

## 1. 上下文
**对话历史:**
{formatted_history}

**最新用户需求:**
{user_message}

**可用专家能力:**
{json.dumps(self.agent_capabilities, ensure_ascii=False, indent=2)}

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

        prompt = f"""
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
{json.dumps(self.agent_capabilities, ensure_ascii=False, indent=2)}

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
        if intent == 'status_inquiry':
            # 对于状态查询，需要获取工作区状态
            # (这是一个简化版，实际可以做的更复杂，比如从planner获取执行进度)
            team_summary = self._memory_adapter.get_team_summary()
            status_context = json.dumps(team_summary, ensure_ascii=False, indent=2)
            
            prompt = f"""
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
            prompt = f"""
# 指令：作为AI项目总监，根据上下文，用人性化、专业的语言回答用户的问题。

## 对话历史
{formatted_history}

## 用户最新消息
"{user_message}"

---
请直接回答用户。如果是闲聊，请礼貌回应；如果是问题，请提供简洁、准确的答案；如果是追问，请结合上下文进行解释。
"""
            
        # 3. 调用LLM生成答案
        answer = await self.llm.aask(prompt)
        
        # 4. 记录交互
        self._record_user_message(user_message)
        self._memory_adapter.add_simple_message(content=answer, role=self.profile, cause_by=f"direct_answer_{intent}")
        
        return answer.strip()