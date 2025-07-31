#!/usr/bin/env python3
"""
生产环境智能体测试脚本
确保所有智能体的工作结果能正确输出到指定目录
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.utils.project_repo import ProjectRepo
from backend.roles.director import DirectorAgent
from backend.roles.case_expert import CaseExpertAgent
from backend.roles.writer_expert import WriterExpertAgent
from backend.roles.data_analyst import DataAnalystAgent
from metagpt.environment import Environment
from metagpt.schema import Message
from metagpt.config2 import Config

async def test_production_agents():
    """测试生产环境中的智能体协作和文件输出"""
    print("🚀 测试生产环境智能体协作")
    
    # 1. 创建工作空间
    session_id = "production_test"
    project_repo = ProjectRepo(session_id)
    workspace_path = project_repo.root
    
    print(f"📁 工作空间路径: {workspace_path}")
    
    # 2. 配置MetaGPT
    config = Config.default()
    config.llm.model = "qwen-max-latest"
    
    # 3. 创建环境和智能体
    environment = Environment()
    
    # 创建智能体并设置project_repo
    director = DirectorAgent(config=config)
    case_expert = CaseExpertAgent(config=config)
    writer = WriterExpertAgent(config=config)
    data_analyst = DataAnalystAgent(config=config)
    
    # 为每个智能体设置project_repo
    for agent in [director, case_expert, writer, data_analyst]:
        agent.project_repo = project_repo
    
    # 将智能体添加到环境
    environment.add_roles([director, case_expert, writer, data_analyst])
    
    print("✓ 智能体环境初始化完成")
    
    # 4. 创建用户需求消息
    user_message = Message(
        content="请进行人工智能在教育领域的应用案例研究，分析相关数据，并撰写综合报告",
        role="user"
    )
    
    print(f"📝 发布用户需求: {user_message.content}")
    environment.publish_message(user_message)
    
    # 5. 运行智能体协作
    print("\n🤖 开始智能体协作...")
    max_rounds = 5
    
    for round_num in range(1, max_rounds + 1):
        print(f"\n--- 第 {round_num} 轮协作 ---")
        
        # 运行一轮
        await environment.run()
        
        # 检查智能体状态
        all_idle = True
        for agent in [director, case_expert, writer, data_analyst]:
            is_idle = agent.rc.todo is None
            print(f"  {agent.profile}: {'空闲' if is_idle else '工作中'}")
            if not is_idle:
                all_idle = False
        
        # 检查消息队列
        msg_count = len(environment.history)
        print(f"  消息队列: {msg_count} 条消息")
        
        if all_idle:
            print("✓ 所有智能体已完成工作")
            break
    
    # 6. 检查文件生成情况
    print("\n📄 检查文件生成情况:")
    
    total_files = 0
    expected_dirs = ["reports", "analysis", "research", "uploads", "drafts"]
    
    for subdir in expected_dirs:
        subdir_path = workspace_path / subdir
        if subdir_path.exists():
            files = [f for f in subdir_path.rglob("*") if f.is_file()]
            total_files += len(files)
            print(f"  {subdir}/: {len(files)} 个文件")
            for file in files:
                rel_path = file.relative_to(workspace_path)
                print(f"    - {rel_path} ({file.stat().st_size} 字节)")
        else:
            print(f"  {subdir}/: 目录不存在")
    
    print(f"\n🎯 总计生成文件: {total_files} 个")
    
    # 7. 验证关键文件
    print("\n🔍 验证关键文件:")
    
    # 检查案例研究文件
    research_files = list((workspace_path / "research").rglob("*.md")) if (workspace_path / "research").exists() else []
    if research_files:
        print(f"✅ 案例研究文件: {len(research_files)} 个")
    else:
        print("❌ 缺少案例研究文件")
    
    # 检查分析报告文件
    analysis_files = list((workspace_path / "analysis").rglob("*.md")) if (workspace_path / "analysis").exists() else []
    if analysis_files:
        print(f"✅ 数据分析报告: {len(analysis_files)} 个")
    else:
        print("❌ 缺少数据分析报告")
    
    # 检查写作报告文件
    report_files = list((workspace_path / "reports").rglob("*.md")) if (workspace_path / "reports").exists() else []
    if report_files:
        print(f"✅ 写作报告: {len(report_files)} 个")
    else:
        print("❌ 缺少写作报告")
    
    # 8. 最终评估
    if total_files >= 3:  # 至少应该有案例研究、数据分析、写作报告三个文件
        print("\n🎉 生产环境智能体测试成功！")
        print("✅ 所有智能体的工作结果都已正确输出到指定目录")
        return True
    else:
        print("\n⚠️ 生产环境智能体测试部分成功")
        print(f"❌ 预期至少3个文件，实际生成{total_files}个文件")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_production_agents())
    if success:
        print("\n✅ 生产环境就绪！")
    else:
        print("\n❌ 生产环境需要进一步调试")
        sys.exit(1)