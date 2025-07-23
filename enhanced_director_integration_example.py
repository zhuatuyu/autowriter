#!/usr/bin/env python3
"""
增强版Director集成示例
展示如何在现有的AutoWriter系统中使用新的Director
"""
import asyncio
import json
from typing import Dict, Any

from backend.services.llm.agents.enhanced_director import EnhancedDirectorAgent


class EnhancedAutoWriterSystem:
    """
    集成增强版Director的AutoWriter系统示例
    """
    
    def __init__(self):
        self.directors = {}  # session_id -> director
        self.agents = {
            "document_expert": None,  # 这里应该是实际的Agent实例
            "case_expert": None,
            "data_analyst": None, 
            "writer_expert": None,
            "chief_editor": None
        }
    
    def get_or_create_director(self, session_id: str) -> EnhancedDirectorAgent:
        """获取或创建Director实例"""
        if session_id not in self.directors:
            self.directors[session_id] = EnhancedDirectorAgent(
                session_id=session_id,
                workspace_path=f"./workspaces/{session_id}"
            )
        return self.directors[session_id]
    
    async def process_user_message(self, session_id: str, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理用户消息的主入口
        """
        director = self.get_or_create_director(session_id)
        
        # Director处理请求并返回响应
        response = await director.process_request(user_message, context)
        
        # 根据响应类型决定后续行动
        if response.get("response_type") == "direct_answer":
            # 直接回答，无需进一步处理
            return response
        
        elif response.get("response_type") == "simple_task":
            # 简单任务，委托给单个Agent
            return await self._execute_simple_task(response)
        
        elif response.get("response_type") == "complex_workflow":
            # 复杂工作流，需要多Agent协作
            return await self._execute_complex_workflow(response)
        
        elif response.get("response_type") == "consultation":
            # 专业咨询，可能需要后续服务
            return await self._handle_consultation_followup(response)
        
        else:
            # 其他类型的响应
            return response
    
    async def _execute_simple_task(self, director_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行简单任务
        """
        task_plan = director_response.get("task_plan", {})
        next_actions = director_response.get("next_actions", [])
        
        if not next_actions:
            return director_response
        
        # 获取目标Agent
        target_agent_id = next_actions[0]
        
        # 这里应该调用实际的Agent
        # agent = self.agents.get(target_agent_id)
        # if agent:
        #     agent_result = await agent.process_request(...)
        
        # 模拟Agent执行结果
        agent_result = {
            "agent_id": target_agent_id,
            "status": "completed",
            "result": f"模拟{target_agent_id}完成任务",
            "details": "这里是具体的执行结果"
        }
        
        return {
            **director_response,
            "execution_result": agent_result,
            "status": "task_completed"
        }
    
    async def _execute_complex_workflow(self, director_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行复杂工作流
        """
        task_plan = director_response.get("task_plan", {})
        steps = task_plan.get("steps", [])
        
        execution_results = []
        
        for step in steps:
            agent_id = step.get("agent_id")
            action = step.get("action")
            parameters = step.get("parameters", {})
            
            # 这里应该调用实际的Agent
            # agent = self.agents.get(agent_id)
            # if agent:
            #     step_result = await agent.execute_action(action, parameters)
            
            # 模拟步骤执行
            step_result = {
                "step_id": step.get("step_id"),
                "agent_id": agent_id,
                "status": "completed",
                "result": f"模拟{agent_id}完成{action}",
                "output": f"这是{agent_id}的输出结果"
            }
            
            execution_results.append(step_result)
        
        return {
            **director_response,
            "workflow_execution": execution_results,
            "status": "workflow_completed"
        }
    
    async def _handle_consultation_followup(self, director_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理咨询后续服务
        """
        follow_up_services = director_response.get("follow_up_services", [])
        
        return {
            **director_response,
            "available_services": follow_up_services,
            "status": "consultation_completed"
        }


async def demo_enhanced_system():
    """
    演示增强版系统的使用
    """
    system = EnhancedAutoWriterSystem()
    
    print("🚀 增强版AutoWriter系统演示")
    print("=" * 60)
    
    # 模拟用户会话
    session_id = "demo_session_001"
    
    # 场景1：用户询问专业问题
    print("\n📝 场景1：专业问题咨询")
    print("-" * 40)
    
    response1 = await system.process_user_message(
        session_id=session_id,
        user_message="绩效报告撰写的技巧有哪些？"
    )
    
    print(f"用户: 绩效报告撰写的技巧有哪些？")
    print(f"系统: {response1.get('message', '无回答')[:200]}...")
    print(f"响应类型: {response1.get('response_type')}")
    
    # 场景2：用户请求搜索案例
    print("\n🔍 场景2：案例搜索请求")
    print("-" * 40)
    
    response2 = await system.process_user_message(
        session_id=session_id,
        user_message="帮我搜索一些智慧城市项目的成功案例"
    )
    
    print(f"用户: 帮我搜索一些智慧城市项目的成功案例")
    print(f"系统: {response2.get('message', '无回答')}")
    print(f"响应类型: {response2.get('response_type')}")
    print(f"执行状态: {response2.get('status')}")
    
    if response2.get('execution_result'):
        result = response2['execution_result']
        print(f"Agent执行结果: {result.get('result')}")
    
    # 场景3：复杂报告撰写需求
    print("\n📊 场景3：复杂报告撰写")
    print("-" * 40)
    
    response3 = await system.process_user_message(
        session_id=session_id,
        user_message="我需要完成一份数字化政务服务的绩效评价报告，包括数据分析、案例研究和最终成稿"
    )
    
    print(f"用户: 我需要完成一份数字化政务服务的绩效评价报告...")
    print(f"系统: {response3.get('message', '无回答')}")
    print(f"响应类型: {response3.get('response_type')}")
    print(f"执行状态: {response3.get('status')}")
    
    if response3.get('workflow_execution'):
        print("工作流执行结果:")
        for step_result in response3['workflow_execution']:
            print(f"  - {step_result.get('agent_id')}: {step_result.get('result')}")
    
    # 场景4：上下文相关的后续问题
    print("\n🔄 场景4：上下文相关问题")
    print("-" * 40)
    
    response4 = await system.process_user_message(
        session_id=session_id,
        user_message="基于刚才的讨论，你觉得我应该重点关注哪些指标？"
    )
    
    print(f"用户: 基于刚才的讨论，你觉得我应该重点关注哪些指标？")
    print(f"系统: {response4.get('message', '无回答')[:200]}...")
    print(f"响应类型: {response4.get('response_type')}")
    
    print("\n" + "=" * 60)
    print("✅ 演示完成")


async def demo_director_capabilities():
    """
    演示Director的各种能力
    """
    print("\n🎯 Director能力演示")
    print("=" * 60)
    
    director = EnhancedDirectorAgent(
        session_id="capability_demo",
        workspace_path="./demo_workspace"
    )
    
    # 能力1：专业知识问答
    print("\n💡 能力1：专业知识问答")
    print("-" * 30)
    
    knowledge_questions = [
        "什么是绩效评价？",
        "如何设计有效的评价指标？",
        "报告写作的常见误区有哪些？"
    ]
    
    for question in knowledge_questions:
        response = await director.process_request(question)
        print(f"Q: {question}")
        print(f"A: {response.get('message', '无回答')[:100]}...")
        print()
    
    # 能力2：任务规划和分配
    print("\n📋 能力2：任务规划和分配")
    print("-" * 30)
    
    planning_request = "我需要分析某个项目的社会效益，包括数据收集、案例对比和报告撰写"
    response = await director.process_request(planning_request)
    
    print(f"需求: {planning_request}")
    print(f"规划: {response.get('message', '无回答')}")
    
    if response.get('task_plan'):
        plan = response['task_plan']
        print(f"计划类型: {plan.get('workflow_type')}")
        print(f"预估时间: {plan.get('estimated_time')}")
        print("执行步骤:")
        for step in plan.get('steps', []):
            print(f"  {step.get('step_id')}: {step.get('agent_id')} - {step.get('expected_output')}")
    
    # 能力3：上下文记忆
    print("\n🧠 能力3：上下文记忆")
    print("-" * 30)
    
    context = director.get_work_context()
    print(f"对话轮数: {len(context.get('conversation_context', []))}")
    print("最近对话:")
    for ctx in context.get('conversation_context', [])[-3:]:
        role = "用户" if ctx['role'] == 'user' else "Director"
        content = ctx['content'][:50] + "..." if len(ctx['content']) > 50 else ctx['content']
        print(f"  [{role}]: {content}")
    
    print("\n" + "=" * 60)
    print("✅ 能力演示完成")


if __name__ == "__main__":
    print("🌟 增强版Director集成示例")
    
    # 运行系统演示
    asyncio.run(demo_enhanced_system())
    
    # 运行能力演示
    asyncio.run(demo_director_capabilities())
    
    print("\n🎉 所有演示完成！")
    print("\n📝 总结：")
    print("1. 增强版Director具备深度客户沟通能力")
    print("2. 能够智能识别用户意图并选择最佳处理策略")
    print("3. 支持简单任务的直接分配和复杂工作流的规划")
    print("4. 维护对话上下文，支持连续对话")
    print("5. 基于MetaGPT的设计理念，具备强大的规划和协调能力")