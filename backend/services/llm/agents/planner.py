"""
PlannerAgent - 规划执行者
负责接收Plan并调度Expert Agents执行Tasks
"""
from typing import Dict, Any

from metagpt.logs import logger
from backend.services.llm.agents.base import BaseAgent
from backend.models.plan import Plan, Task

class PlannerAgent(BaseAgent):
    """
    🧑‍💻 规划执行者 (Planner) - 虚拟办公室的项目经理

    职责:
    1. 接收Director制定的Plan
    2. 解析Plan中的Tasks
    3. 智能匹配并调度合适的Expert Agent来执行Task
    4. 监控Task执行状态，处理依赖关系
    5. 收集所有Task结果，完成Plan
    """

    def __init__(self, session_id: str, workspace_path: str, memory_manager=None):
        super().__init__(
            agent_id="planner",
            session_id=session_id,
            workspace_path=workspace_path,
            memory_manager=memory_manager,
            profile="规划执行者",
            goal="高效、准确地执行计划，协调团队完成任务"
        )
        self.role = "项目经理"
        # self.expert_map = self._initialize_expert_map() # 弃用基于关键词的路由

    def _initialize_expert_map(self) -> Dict[str, str]:
        """
        (已弃用) 初始化任务描述关键词到专家AgentID的映射。
        现在Planner将严格按照Director在Plan中指定的agent_id来分配任务。
        """
        return {}

    async def execute_plan(self, plan: Plan, expert_team: Dict[str, BaseAgent]) -> Dict[str, Any]:
        """
        执行整个计划的核心方法
        """
        logger.info(f"🧑‍💻 Planner开始执行计划: {plan.goal}")
        plan.status = "in_progress"
        
        while not plan.is_completed():
            next_task = plan.get_next_task()
            if not next_task:
                # 如果没有可执行的任务，但计划未完成，说明可能存在循环依赖或问题
                logger.warning(f"🤔 计划'{plan.goal}'无法找到下一个可执行任务，但尚未完成。")
                break

            next_task.status = "in_progress"
            
            # 严格按照Plan中指定的Agent进行分配
            expert_agent = self._assign_task_to_expert(next_task, expert_team)

            if not expert_agent:
                error_msg = f"❌ 无法为任务 '{next_task.description}' 找到指定的专家 '{next_task.agent}'。"
                logger.error(error_msg)
                next_task.status = "error"
                next_task.result = error_msg
                plan.status = "error"
                continue

            logger.info(f"⏳ 将任务 '{next_task.description}' 分配给 {expert_agent.name}({expert_agent.profile})")
            
            # 执行任务
            try:
                # 传递任务本身和上下文信息（例如之前任务的结果）
                context = self._gather_context_for_task(plan, next_task)
                task_result = await expert_agent.execute_task(next_task, context)
                
                # 增强：检查任务执行状态
                if task_result and task_result.get("status") == "completed":
                    next_task.result = task_result.get("result")
                    next_task.status = "completed"
                    logger.info(f"✅ 任务 '{next_task.description}' 已由 {expert_agent.name} 成功完成。")
                else:
                    error_msg = f"❌ 专家 {expert_agent.name} 执行任务 '{next_task.description}' 失败或状态异常。"
                    logger.error(f"{error_msg} 返回结果: {task_result}")
                    next_task.status = "error"
                    next_task.result = task_result.get("result", "执行失败，无详细信息。")
                    plan.status = "error"
                    break # 中断计划执行

            except Exception as e:
                error_msg = f"❌ 专家 {expert_agent.name} 执行任务 '{next_task.description}' 时发生异常: {e}"
                logger.error(error_msg, exc_info=True)
                next_task.status = "error"
                next_task.result = str(e)
                plan.status = "error"
                break # 中断计划执行

        if plan.is_completed():
            plan.status = "completed"
            logger.info(f"🎉 计划 '{plan.goal}' 已成功完成！")
        else:
            logger.error(f"💔 计划 '{plan.goal}' 执行失败或未完成。")
        
        return self._summarize_plan_result(plan)

    def _assign_task_to_expert(self, task: Task, expert_team: Dict[str, BaseAgent]) -> BaseAgent:
        """严格根据任务中指定的agent_id来分配专家"""
        # 新逻辑：直接使用task中由Director指定的agent_id
        # 安全校验：检查Task对象是否有agent属性
        if not hasattr(task, 'agent') or not task.agent:
            logger.error(f"任务 '{task.description}' 未指定负责的agent或agent字段为空。")
            return None

        agent_id = task.agent
        
        task.owner_agent_id = agent_id # 记录执行者
        return expert_team.get(agent_id)
        
    def _gather_context_for_task(self, plan: Plan, current_task: Task) -> Dict[str, Any]:
        """为当前任务收集其依赖任务的结果作为上下文"""
        context = {}
        if not current_task.dependencies:
            return context
        
        for dep_id in current_task.dependencies:
            dep_task = plan.get_task_by_id(dep_id)
            if dep_task and dep_task.status == "completed":
                context[dep_id] = dep_task.result
        
        return context

    def _summarize_plan_result(self, plan: Plan) -> Dict[str, Any]:
        """汇总计划的最终结果"""
        final_result = {
            "goal": plan.goal,
            "status": plan.status,
            "tasks": []
        }
        # 通常，最后一个任务的结果是整个计划的最终产出
        if plan.tasks:
            final_result["final_output"] = plan.tasks[-1].result

        for task in plan.tasks:
             final_result["tasks"].append({
                 "description": task.description,
                 "owner": task.owner_agent_id,
                 "status": task.status,
                 "result": str(task.result) if not isinstance(task.result, dict) else {k: (v[:200] + "..." if isinstance(v, str) and len(v) > 200 else v) for k, v in task.result.items()}
             })
        
        return final_result 