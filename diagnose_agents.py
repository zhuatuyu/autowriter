#!/usr/bin/env python3
"""
智能体执行诊断脚本
用于检查智能体为什么没有生成结果文件
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from metagpt.environment import Environment
from metagpt.schema import Message
from metagpt.logs import logger

from backend.roles.director import DirectorAgent
from backend.roles.case_expert import CaseExpertAgent
from backend.roles.writer_expert import WriterExpertAgent
from backend.roles.data_analyst import DataAnalystAgent
from backend.utils.project_repo import ProjectRepo

async def diagnose_agent_execution():
    """诊断智能体执行问题"""
    print("🔍 开始诊断智能体执行问题...")
    
    # 1. 创建工作空间
    session_id = "diagnose_test"
    project_repo = ProjectRepo(session_id)
    print(f"📁 工作空间: {project_repo.root}")
    
    # 2. 创建智能体
    print("\n🤖 创建智能体...")
    director = DirectorAgent()
    case_expert = CaseExpertAgent()
    writer_expert = WriterExpertAgent()
    data_analyst = DataAnalystAgent()
    
    # 为智能体设置project_repo属性
    print("\n🔧 设置智能体project_repo属性:")
    case_expert.project_repo = project_repo
    writer_expert.project_repo = project_repo
    data_analyst.project_repo = project_repo
    print(f"  ✓ case_expert 已设置 project_repo")
    print(f"  ✓ writer_expert 已设置 project_repo")
    print(f"  ✓ data_analyst 已设置 project_repo")
    
    agents = [director, case_expert, writer_expert, data_analyst]
    
    # 3. 创建Environment
    print("🌍 创建Environment...")
    environment = Environment()
    environment.add_roles(agents)
    
    # 4. 生成测试计划
    print("\n📋 生成测试计划...")
    user_request = "请帮我写一份关于养老院绩效评估的研究报告"
    plan = await director.process_request(user_request)
    
    if not plan:
        print("❌ 计划生成失败")
        return
    
    print(f"✅ 计划生成成功，共{len(plan.tasks)}个任务:")
    for i, task in enumerate(plan.tasks, 1):
        print(f"  {i}. {task.agent}: {task.description}")
        if task.dependencies:
            print(f"     依赖: {task.dependencies}")
    
    # 5. 发布计划消息
    print("\n📨 发布计划消息...")
    plan_message = Message(
        content=plan.model_dump_json(),
        role="Director",
        cause_by=DirectorAgent
    )
    environment.publish_message(plan_message)
    
    # 6. 检查智能体初始状态
    print("\n🔍 检查智能体初始状态:")
    for agent in agents:
        if agent.profile in ['case_expert', 'writer_expert', 'data_analyst']:
            print(f"  {agent.profile}:")
            print(f"    - 消息数: {len(agent.rc.memory.get())}")
            print(f"    - 新消息数: {len(agent.rc.news) if hasattr(agent.rc, 'news') and agent.rc.news else 0}")
            print(f"    - 待执行Action: {agent.rc.todo.__class__.__name__ if agent.rc.todo else 'None'}")
            print(f"    - is_idle: {agent.is_idle}")
            print(f"    - 监听的消息类型: {[str(watch) for watch in agent.rc.watch]}")
    
    # 7. 手动触发智能体思考
    print("\n🧠 手动触发智能体思考...")
    for agent in agents:
        if agent.profile in ['case_expert', 'writer_expert', 'data_analyst']:
            print(f"\n  触发 {agent.profile} 思考...")
            try:
                # 手动设置新消息
                agent.rc.news = [plan_message]
                think_result = await agent._think()
                print(f"    _think结果: {think_result}")
                
                if think_result and agent.rc.todo:
                    print(f"    设置的Action: {agent.rc.todo.__class__.__name__}")
                    
                    # 尝试执行Action
                    print(f"    尝试执行Action...")
                    try:
                        result = await agent._act()
                        print(f"    执行结果: {type(result)} - {result.content[:100] if result and result.content else 'None'}")
                    except Exception as e:
                        print(f"    执行失败: {e}")
                else:
                    print(f"    未设置Action或思考失败")
                    
            except Exception as e:
                print(f"    思考过程出错: {e}")
    
    # 8. 运行Environment几轮
    print("\n🔄 运行Environment 5轮...")
    for i in range(5):
        print(f"\n--- 第 {i+1} 轮 ---")
        try:
            await environment.run(k=1)
            print(f"✅ 第{i+1}轮运行完成")
            
            # 检查智能体状态
            for agent in agents:
                if agent.profile in ['case_expert', 'writer_expert', 'data_analyst']:
                    print(f"  {agent.profile}: 消息数={len(agent.rc.memory.get())}, is_idle={agent.is_idle}")
            
            # 检查文件是否生成
            print("  检查文件生成情况:")
            output_dirs = ["reports", "analysis", "research", "cases", "drafts"]
            for dir_name in output_dirs:
                dir_path = project_repo.get_path(dir_name)
                if dir_path.exists():
                    files = list(dir_path.glob("*"))
                    if files:
                        print(f"    {dir_name}: {len(files)} 个文件")
                        
        except Exception as e:
            print(f"❌ 第{i+1}轮运行失败: {e}")
    
    # 9. 检查最终状态和输出文件
    print("\n🔍 检查最终状态:")
    for agent in agents:
        if agent.profile in ['case_expert', 'writer_expert', 'data_analyst']:
            messages = agent.rc.memory.get()
            print(f"  {agent.profile}:")
            print(f"    - 总消息数: {len(messages)}")
            print(f"    - 待执行Action: {agent.rc.todo.__class__.__name__ if agent.rc.todo else 'None'}")
            print(f"    - is_idle: {agent.is_idle}")
            
            # 显示最近的消息内容
            if messages:
                latest_msg = messages[-1]
                print(f"    - 最新消息: {latest_msg.content[:100] if latest_msg.content else 'None'}...")
    
    # 10. 检查输出文件
    print("\n📄 检查输出文件:")
    output_dirs = ["reports", "analysis", "research", "cases", "drafts"]
    for subdir in output_dirs:
        subdir_path = project_repo.get_path(subdir)
        if subdir_path.exists():
            files = list(subdir_path.glob("**/*"))  # 递归搜索所有文件
            file_list = [f for f in files if f.is_file()]
            if file_list:
                print(f"  {subdir}/: {len(file_list)} 个文件")
                for file in file_list:
                    print(f"    - {file.name} ({file.stat().st_size} bytes)")
            else:
                print(f"  {subdir}/: 空目录")
        else:
            print(f"  {subdir}/: 目录不存在")
            
    # 额外检查：直接列出工作空间下的所有文件
    print("\n🔍 工作空间所有文件:")
    workspace_files = list(project_repo.root.glob("**/*"))
    for file in workspace_files:
        if file.is_file():
            relative_path = file.relative_to(project_repo.root)
            print(f"  {relative_path} ({file.stat().st_size} bytes)")
            
    # 特别检查research目录结构
    print("\n🔍 Research目录详细结构:")
    research_path = project_repo.get_path("research")
    if research_path.exists():
        for item in research_path.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(research_path)
                print(f"  research/{relative_path} ({item.stat().st_size} bytes)")
    else:
        print("  research目录不存在")
            
    # 11. 手动测试文件保存功能
    print("\n🧪 测试文件保存功能:")
    try:
        test_content = "这是一个测试文件内容"
        project_repo.save_file("test_file.txt", test_content, "reports")
        
        test_file_path = project_repo.get_path("reports") / "test_file.txt"
        if test_file_path.exists():
            print("✓ 文件保存功能正常")
            print(f"  文件路径: {test_file_path}")
            print(f"  文件大小: {test_file_path.stat().st_size} bytes")
        else:
            print("✗ 文件保存失败")
    except Exception as e:
        print(f"✗ 文件保存异常: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose_agent_execution())