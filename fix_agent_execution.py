#!/usr/bin/env python3
"""
修复智能体执行问题的脚本
"""
import asyncio
import sys
from pathlib import Path
import json

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from backend.utils.project_repo import ProjectRepo
from backend.roles.director import DirectorAgent
from backend.roles.case_expert import CaseExpertAgent
from backend.roles.writer_expert import WriterExpertAgent
from backend.roles.data_analyst import DataAnalystAgent
from backend.services.environment import Environment
from backend.models.plan import Plan, Task

async def fix_agent_execution():
    """修复智能体执行问题"""
    print("🔧 修复智能体执行问题")
    
    # 1. 创建ProjectRepo
    session_id = "fixed_execution_test"
    project_repo = ProjectRepo(session_id)
    print(f"📁 工作空间路径: {project_repo.root}")
    
    # 2. 创建智能体
    print("\n🤖 创建智能体:")
    director = DirectorAgent()
    case_expert = CaseExpertAgent()
    writer_expert = WriterExpertAgent()
    data_analyst = DataAnalystAgent()
    
    # 3. 设置project_repo属性
    case_expert.project_repo = project_repo
    writer_expert.project_repo = project_repo
    data_analyst.project_repo = project_repo
    print("✓ 已为所有智能体设置project_repo")
    
    # 4. 创建Environment
    agents = [director, case_expert, writer_expert, data_analyst]
    environment = Environment()
    
    # 添加智能体到环境中
    for agent in agents:
        environment.add_role(agent)
    
    # 5. 创建详细的测试计划
    test_plan = Plan(
        goal="测试智能体完整执行流程，确保文件正确保存",
        project_name="智能体执行修复测试",
        description="测试智能体完整执行流程并确保文件正确保存",
        tasks=[
            Task(
                id="task_1",
                description="搜索国内养老院建设服务项目的成功案例，重点关注政府投资和运营效率",
                agent="case_expert",
                dependencies=[],
                priority=1
            ),
            Task(
                id="task_2", 
                description="分析养老院建设项目的财政投入数据和绩效指标",
                agent="data_analyst",
                dependencies=["task_1"],
                priority=2
            ),
            Task(
                id="task_3",
                description="根据案例研究和数据分析结果，撰写综合性报告",
                agent="writer_expert", 
                dependencies=["task_1", "task_2"],
                priority=3
            )
        ]
    )
    
    # 6. 发布测试计划
    print("📋 发布测试计划:")
    # 创建用户需求消息
    from metagpt.actions.add_requirement import UserRequirement
    from metagpt.schema import Message
    
    user_message = Message(
        content="测试智能体完整执行流程：进行人工智能在教育领域的应用案例研究，分析相关数据，并撰写综合报告",
        role="user",
        cause_by=UserRequirement
    )
    
    # 发布消息到环境
    environment.publish_message(user_message)
    print(f"✓ 计划已发布，包含 {len(test_plan.tasks)} 个任务")
    
    # 7. 逐步执行并监控
    print("\n🔄 开始执行:")
    max_rounds = 10  # 增加执行轮数
    
    for round_num in range(1, max_rounds + 1):
        print(f"\n--- 第 {round_num} 轮 ---")
        
        # 检查是否还有活跃的智能体
        active_agents = [agent for agent in agents[1:] if not agent.is_idle]  # 排除director
        if not active_agents:
            print("所有智能体都已空闲，检查是否有待处理的消息...")
            
            # 检查是否有未处理的消息
            has_pending_messages = False
            for agent in agents[1:]:
                if len(agent.rc.news) > 0:
                    has_pending_messages = True
                    print(f"  {agent.profile} 有 {len(agent.rc.news)} 条未处理消息")
            
            if not has_pending_messages:
                print("没有待处理的消息，执行完成")
                break
        
        try:
            await environment.run(k=1)
            print(f"✅ 第{round_num}轮执行完成")
            
            # 详细检查每个智能体状态
            for agent in agents[1:]:  # 排除director
                messages = agent.rc.memory.get()
                news_count = len(agent.rc.news)
                todo_status = "有待执行Action" if agent.rc.todo else "无待执行Action"
                print(f"  {agent.profile}: 消息={len(messages)}, 新消息={news_count}, {todo_status}, idle={agent.is_idle}")
                
                # 如果有新消息但智能体空闲，尝试手动触发
                if news_count > 0 and agent.is_idle:
                    print(f"    尝试手动触发 {agent.profile} 的思考过程...")
                    try:
                        should_act = await agent._think()
                        if should_act:
                            print(f"    {agent.profile} 思考完成，设置了新的Action")
                        else:
                            print(f"    {agent.profile} 思考完成，但没有设置Action")
                    except Exception as e:
                        print(f"    {agent.profile} 思考过程出错: {e}")
            
            # 检查文件生成情况
            workspace_files = list(project_repo.root.glob("**/*"))
            file_count = len([f for f in workspace_files if f.is_file()])
            if file_count > 0:
                print(f"  当前工作空间有 {file_count} 个文件")
                
        except Exception as e:
            print(f"❌ 第{round_num}轮执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 8. 最终检查
    print("\n📊 最终执行结果:")
    
    # 检查智能体最终状态
    for agent in agents[1:]:
        messages = agent.rc.memory.get()
        print(f"\n{agent.profile}:")
        print(f"  - 总消息数: {len(messages)}")
        print(f"  - 新消息数: {len(agent.rc.news)}")
        print(f"  - 待执行Action: {agent.rc.todo.__class__.__name__ if agent.rc.todo else 'None'}")
        print(f"  - 是否空闲: {agent.is_idle}")
        
        # 显示最近的消息
        if messages:
            latest_msg = messages[-1]
            content_preview = (latest_msg.content[:100] + "...") if len(latest_msg.content) > 100 else latest_msg.content
            print(f"  - 最新消息: {content_preview}")
    
    # 检查生成的文件
    print("\n📄 生成的文件:")
    workspace_files = list(project_repo.root.glob("**/*"))
    for file in workspace_files:
        if file.is_file():
            relative_path = file.relative_to(project_repo.root)
            print(f"  {relative_path} ({file.stat().st_size} bytes)")
    
    # 检查各个子目录
    print("\n📁 各子目录文件统计:")
    subdirs = ["reports", "analysis", "research", "cases", "drafts"]
    for subdir in subdirs:
        subdir_path = project_repo.get_path(subdir)
        if subdir_path.exists():
            files = list(subdir_path.glob("**/*"))
            file_list = [f for f in files if f.is_file()]
            print(f"  {subdir}: {len(file_list)} 个文件")
            for file in file_list:
                print(f"    - {file.name} ({file.stat().st_size} bytes)")
        else:
            print(f"  {subdir}: 目录不存在")

if __name__ == "__main__":
    asyncio.run(fix_agent_execution())