#!/usr/bin/env python3
"""
测试增强版Director的各种能力
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.llm.agents.enhanced_director import EnhancedDirectorAgent


async def test_enhanced_director():
    """测试增强版Director的各种场景"""
    
    # 初始化Director
    director = EnhancedDirectorAgent(
        session_id="test_session_001",
        workspace_path="./test_workspace"
    )
    
    print("🎯 增强版智能项目总监测试开始")
    print("=" * 60)
    
    # 测试场景1：直接回答专业问题
    print("\n📝 测试场景1：专业问题直接回答")
    print("-" * 40)
    
    question1 = "绩效报告撰写有什么技巧？应该参考哪些网络案例？"
    response1 = await director.process_request(question1)
    
    print(f"用户问题: {question1}")
    print(f"Director回答: {response1.get('message', '无回答')}")
    print(f"响应类型: {response1.get('response_type', '未知')}")
    
    # 测试场景2：简单任务分配
    print("\n🔍 测试场景2：简单任务分配")
    print("-" * 40)
    
    question2 = "帮我找找历史报告中关于交通运输的文档"
    response2 = await director.process_request(question2)
    
    print(f"用户需求: {question2}")
    print(f"Director回答: {response2.get('message', '无回答')}")
    print(f"响应类型: {response2.get('response_type', '未知')}")
    print(f"下一步行动: {response2.get('next_actions', [])}")
    
    # 测试场景3：复杂工作流规划
    print("\n📊 测试场景3：复杂工作流规划")
    print("-" * 40)
    
    question3 = "我需要写一份关于数字化城市管理的绩效评价报告，请帮我完成从资料收集到最终成稿的全过程"
    response3 = await director.process_request(question3)
    
    print(f"用户需求: {question3}")
    print(f"Director回答: {response3.get('message', '无回答')}")
    print(f"响应类型: {response3.get('response_type', '未知')}")
    
    if response3.get('task_plan'):
        plan = response3['task_plan']
        print(f"执行计划ID: {plan.get('plan_id', '未知')}")
        print(f"工作流类型: {plan.get('workflow_type', '未知')}")
        print(f"预估时间: {plan.get('estimated_time', '未知')}")
        print("执行步骤:")
        for step in plan.get('steps', []):
            print(f"  - {step.get('step_id', '未知')}: {step.get('agent_id', '未知')} - {step.get('action', '未知')}")
    
    # 测试场景4：专业咨询
    print("\n💡 测试场景4：专业咨询")
    print("-" * 40)
    
    question4 = "我们团队在报告写作过程中总是遇到结构混乱的问题，你有什么建议吗？"
    response4 = await director.process_request(question4)
    
    print(f"用户咨询: {question4}")
    print(f"Director建议: {response4.get('message', '无回答')}")
    print(f"响应类型: {response4.get('response_type', '未知')}")
    
    # 测试场景5：上下文相关的对话
    print("\n🔄 测试场景5：上下文相关对话")
    print("-" * 40)
    
    question5 = "基于我们刚才讨论的内容，你觉得我应该先从哪个环节开始？"
    response5 = await director.process_request(question5)
    
    print(f"用户问题: {question5}")
    print(f"Director回答: {response5.get('message', '无回答')}")
    print(f"响应类型: {response5.get('response_type', '未知')}")
    
    # 显示Director的工作上下文
    print("\n📋 Director工作上下文")
    print("-" * 40)
    
    context = director.get_work_context()
    print(f"对话轮数: {len(context.get('conversation_context', []))}")
    print(f"活跃任务: {len(context.get('active_tasks', []))}")
    print(f"规划状态: {context.get('planner_status', {})}")
    
    # 测试规划状态
    plan_status = director.get_current_plan_status()
    print(f"当前规划: {plan_status}")
    
    print("\n" + "=" * 60)
    print("🎯 增强版智能项目总监测试完成")


async def test_intent_analysis():
    """测试意图分析能力"""
    
    director = EnhancedDirectorAgent(
        session_id="test_intent_001", 
        workspace_path="./test_workspace"
    )
    
    print("\n🧠 意图分析能力测试")
    print("=" * 60)
    
    test_messages = [
        "你好，我想了解一下绩效报告的基本结构",
        "帮我搜索一些关于智慧城市的案例",
        "我需要完成一份完整的项目绩效评价报告",
        "请帮我分析一下这个项目的数据",
        "你觉得我们的报告质量怎么样？",
        "帮我找找历史文档中的相关资料"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n测试 {i}: {message}")
        print("-" * 40)
        
        # 直接调用意图分析方法
        intent = await director._analyze_user_intent(message)
        
        print(f"意图类型: {intent.get('intent_type', '未知')}")
        print(f"复杂度: {intent.get('complexity', '未知')}")
        print(f"需要的Agent: {intent.get('required_agents', [])}")
        print(f"工作流类型: {intent.get('workflow_type', '未知')}")
        print(f"可直接回答: {intent.get('can_answer_directly', '未知')}")
        print(f"推理过程: {intent.get('reasoning', '无')[:100]}...")


if __name__ == "__main__":
    print("🚀 开始测试增强版智能项目总监")
    
    # 运行主要功能测试
    asyncio.run(test_enhanced_director())
    
    # 运行意图分析测试
    asyncio.run(test_intent_analysis())
    
    print("\n✅ 所有测试完成！")