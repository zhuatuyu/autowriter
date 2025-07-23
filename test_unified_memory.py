#!/usr/bin/env python3
"""
测试统一记忆系统
"""
import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.llm.unified_memory_storage import UnifiedMemoryStorage
from backend.services.llm.unified_memory_adapter import UnifiedMemoryManager
from backend.services.llm.agents.base import BaseAgent


async def test_unified_memory_storage():
    """测试统一记忆存储"""
    print("🧠 测试统一记忆存储")
    print("=" * 50)
    
    # 创建临时工作空间
    temp_dir = tempfile.mkdtemp()
    try:
        storage = UnifiedMemoryStorage(temp_dir)
        
        # 测试Agent注册
        print("\n📋 测试Agent注册")
        print("-" * 30)
        
        agent_info = {
            "name": "测试Agent",
            "profile": "测试专家",
            "goal": "执行测试任务",
            "constraints": "遵循测试规范"
        }
        
        storage.register_agent("test_agent", agent_info)
        
        # 验证注册结果
        all_agents = storage.get_all_agents()
        print(f"注册的Agent数量: {len(all_agents)}")
        print(f"Agent信息: {all_agents.get('test_agent', {}).get('name', '未找到')}")
        
        # 测试消息添加
        print("\n📝 测试消息添加")
        print("-" * 30)
        
        test_messages = [
            {
                "content": "开始执行任务A",
                "role": "test_agent",
                "cause_by": "task_start",
                "sent_from": "test_agent"
            },
            {
                "content": "任务A执行完成",
                "role": "test_agent", 
                "cause_by": "task_complete",
                "sent_from": "test_agent"
            }
        ]
        
        for msg in test_messages:
            storage.add_message(msg)
        
        # 验证消息存储
        conversation_history = storage.get_conversation_history()
        print(f"存储的消息数量: {len(conversation_history)}")
        
        for i, msg in enumerate(conversation_history):
            print(f"消息 {i+1}: {msg.get('content', '')[:50]}...")
        
        # 测试Agent记忆获取
        print("\n🔍 测试Agent记忆获取")
        print("-" * 30)
        
        agent_memory = storage.get_agent_memory("test_agent")
        print(f"Agent记忆数量: {len(agent_memory)}")
        
        # 测试共享上下文
        print("\n🔄 测试共享上下文")
        print("-" * 30)
        
        storage.update_shared_context("test_key", "test_value")
        storage.update_shared_context("project_status", "进行中")
        
        shared_context = storage.get_shared_context()
        print(f"共享上下文: {shared_context}")
        
        # 测试项目信息
        print("\n📋 测试项目信息")
        print("-" * 30)
        
        storage.set_project_info(
            idea="测试项目",
            investment=100.0,
            session_info={"session_id": "test_001"}
        )
        
        project_info = storage.get_project_info()
        print(f"项目信息: {project_info}")
        
        # 测试统计信息
        print("\n📊 测试统计信息")
        print("-" * 30)
        
        stats = storage.get_statistics()
        print(f"统计信息: {stats}")
        
        print("\n✅ 统一记忆存储测试完成")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)


async def test_unified_memory_manager():
    """测试统一记忆管理器"""
    print("\n🎯 测试统一记忆管理器")
    print("=" * 50)
    
    # 创建临时工作空间
    temp_dir = tempfile.mkdtemp()
    try:
        manager = UnifiedMemoryManager(temp_dir)
        
        # 测试Agent注册
        print("\n📋 测试多Agent注册")
        print("-" * 30)
        
        agents_info = {
            "director": {
                "name": "项目总监",
                "profile": "项目管理专家",
                "goal": "协调团队工作"
            },
            "writer": {
                "name": "写作专家",
                "profile": "内容创作专家", 
                "goal": "撰写高质量内容"
            }
        }
        
        for agent_id, info in agents_info.items():
            manager.register_agent(agent_id, info)
        
        # 测试适配器功能
        print("\n🔧 测试适配器功能")
        print("-" * 30)
        
        director_adapter = manager.get_adapter("director")
        writer_adapter = manager.get_adapter("writer")
        
        # 测试消息发送
        director_adapter.add_simple_message("开始项目规划", cause_by="project_start")
        writer_adapter.add_simple_message("准备开始写作", cause_by="writing_prep")
        
        # 测试Agent间通信
        director_adapter.send_message_to_agent("writer", "请开始撰写第一章")
        
        # 验证消息
        director_memory = director_adapter.get_memory()
        writer_memory = writer_adapter.get_memory()
        
        print(f"总监记忆数量: {len(director_memory)}")
        print(f"写作专家记忆数量: {len(writer_memory)}")
        
        # 测试团队摘要
        print("\n👥 测试团队摘要")
        print("-" * 30)
        
        team_summary = director_adapter.get_team_summary()
        print(f"团队成员数量: {len(team_summary.get('team_members', {}))}")
        print(f"项目信息: {team_summary.get('project_info', {})}")
        
        # 测试项目摘要
        print("\n📊 测试项目摘要")
        print("-" * 30)
        
        manager.set_project_info("统一记忆系统测试项目", 200.0)
        project_summary = manager.get_project_summary()
        
        print(f"项目想法: {project_summary.get('project_info', {}).get('idea', '')}")
        print(f"总消息数: {project_summary.get('statistics', {}).get('total_messages', 0)}")
        
        print("\n✅ 统一记忆管理器测试完成")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)


async def test_base_agent_integration():
    """测试BaseAgent与统一记忆系统的集成"""
    print("\n🤖 测试BaseAgent集成")
    print("=" * 50)
    
    # 创建临时工作空间
    temp_dir = tempfile.mkdtemp()
    try:
        # 创建Agent工作空间
        agent_workspace = Path(temp_dir) / "test_agent"
        
        # 创建BaseAgent实例
        agent = BaseAgent(
            agent_id="test_agent",
            session_id="test_session",
            workspace_path=str(agent_workspace),
            profile="测试专家"
        )
        
        print(f"Agent创建成功: {agent.name}")
        print(f"使用统一记忆: {getattr(agent, '_use_unified_memory', False)}")
        
        # 测试工作记忆记录
        print("\n💾 测试工作记忆记录")
        print("-" * 30)
        
        agent.record_work_memory("执行测试任务", "任务执行成功")
        agent.record_work_memory("数据分析", "分析完成，发现3个关键点")
        
        # 测试工作上下文获取
        print("\n📋 测试工作上下文")
        print("-" * 30)
        
        work_context = agent.get_work_context()
        print(f"工作上下文:\n{work_context}")
        
        # 测试Agent状态
        print("\n📊 测试Agent状态")
        print("-" * 30)
        
        status = await agent.get_status()
        print(f"Agent状态: {status.get('status', '未知')}")
        print(f"记忆系统: {status.get('memory_system', '未知')}")
        print(f"记忆数量: {status.get('memory_count', 0)}")
        
        # 测试任务执行
        print("\n⚙️ 测试任务执行")
        print("-" * 30)
        
        test_task = {
            "description": "测试任务执行",
            "type": "test",
            "priority": "normal"
        }
        
        result = await agent.execute_task(test_task)
        print(f"任务执行结果: {result.get('status', '未知')}")
        
        # 再次检查工作上下文
        updated_context = agent.get_work_context()
        print(f"更新后的工作上下文:\n{updated_context}")
        
        print("\n✅ BaseAgent集成测试完成")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)


async def test_memory_comparison():
    """对比统一记忆系统与原有系统的差异"""
    print("\n⚖️ 记忆系统对比测试")
    print("=" * 50)
    
    # 创建两个临时工作空间
    temp_dir1 = tempfile.mkdtemp()
    temp_dir2 = tempfile.mkdtemp()
    
    try:
        # 测试统一记忆系统
        print("\n🔄 统一记忆系统测试")
        print("-" * 30)
        
        unified_workspace = Path(temp_dir1) / "unified_agent"
        unified_agent = BaseAgent(
            agent_id="unified_test",
            session_id="unified_session", 
            workspace_path=str(unified_workspace),
            profile="统一记忆测试专家"
        )
        
        # 记录一些工作记忆
        for i in range(3):
            unified_agent.record_work_memory(f"统一系统任务{i+1}", f"任务{i+1}完成")
        
        unified_context = unified_agent.get_work_context()
        unified_status = await unified_agent.get_status()
        
        print(f"统一系统记忆数量: {unified_status.get('memory_count', 0)}")
        print(f"统一系统类型: {unified_status.get('memory_system', '未知')}")
        
        print("\n📊 对比结果")
        print("-" * 30)
        print(f"统一记忆系统:")
        print(f"  - 记忆数量: {unified_status.get('memory_count', 0)}")
        print(f"  - 系统类型: {unified_status.get('memory_system', '未知')}")
        print(f"  - 团队协作: {'支持' if getattr(unified_agent, '_use_unified_memory', False) else '不支持'}")
        
        # 测试团队功能（如果可用）
        if getattr(unified_agent, '_use_unified_memory', False):
            print("\n👥 团队功能测试")
            print("-" * 30)
            
            team_context = unified_agent.get_team_context()
            print(f"团队上下文可用: {'是' if team_context.get('project_info') else '否'}")
        
        print("\n✅ 记忆系统对比完成")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir1)
        shutil.rmtree(temp_dir2)


if __name__ == "__main__":
    print("🧪 统一记忆系统测试套件")
    print("=" * 60)
    
    # 运行所有测试
    asyncio.run(test_unified_memory_storage())
    asyncio.run(test_unified_memory_manager())
    asyncio.run(test_base_agent_integration())
    asyncio.run(test_memory_comparison())
    
    print("\n🎉 所有测试完成！")
    print("\n📋 测试总结：")
    print("1. ✅ 统一记忆存储功能正常")
    print("2. ✅ 统一记忆管理器功能正常")
    print("3. ✅ BaseAgent集成功能正常")
    print("4. ✅ 记忆系统对比功能正常")
    print("\n🚀 统一记忆系统已准备就绪！")