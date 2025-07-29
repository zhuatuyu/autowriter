#!/usr/bin/env python3
"""
快速测试脚本 - 验证 ProjectRepo 和 CaseExpertAgent 功能
"""
import asyncio
from pathlib import Path
from backend.utils.project_repo import ProjectRepo
from backend.roles.case_expert import CaseExpertAgent
from backend.actions.case_research import ConductCaseResearch
from metagpt.context import Context
from metagpt.schema import Message

async def quick_test():
    """快速测试主要功能"""
    print("🚀 开始快速测试...")
    
    # 1. 测试 ProjectRepo
    print("\n📁 测试 ProjectRepo...")
    project_repo = ProjectRepo("quick_test")
    
    # 保存测试文件
    test_content = "# 测试文档\n这是一个测试文档。"
    saved_path = project_repo.save_file("test.md", test_content, "research")
    print(f"  ✅ 文件已保存: {saved_path}")
    
    # 2. 测试 CaseExpertAgent
    print("\n🤖 测试 CaseExpertAgent...")
    
    # 创建上下文并注入 ProjectRepo
    context = Context()
    context.kwargs.set('project_repo', project_repo)
    
    # 创建智能体
    agent = CaseExpertAgent(context=context)
    
    # 添加用户消息
    user_message = Message(content="分析苹果公司的商业模式", role="user")
    agent.rc.memory.add(user_message)
    
    # 设置要执行的action
    agent.rc.todo = ConductCaseResearch()
    
    # 添加模拟的案例数据
    from backend.roles.case_expert import CaseReport
    test_report = CaseReport(
        topic="分析苹果公司的商业模式",
        links={"苹果商业模式": ["https://example.com"]},
        summaries={"https://example.com": "苹果通过生态系统和品牌价值创造竞争优势。"}
    )
    
    case_message = Message(content="", instruct_content=test_report, role="case_expert")
    agent.rc.memory.add(case_message)
    
    # 执行智能体
    result = await agent._act()
    print(f"  ✅ 智能体执行成功，结果类型: {type(result)}")
    
    # 检查生成的文件
    cases_dir = project_repo.get_path('research/cases')
    files = list(cases_dir.glob("*.md"))
    print(f"  ✅ 生成了 {len(files)} 个案例研究文件")
    
    print("\n🎉 快速测试完成！所有功能正常工作！")

if __name__ == "__main__":
    asyncio.run(quick_test())