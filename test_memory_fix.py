#!/usr/bin/env python3
"""
测试修复后的记忆系统
"""
import asyncio
from pathlib import Path
from backend.services.llm.agents.base import BaseAgent
from metagpt.schema import Message

async def test_memory_system():
    """测试记忆系统"""
    print("🧪 开始测试记忆系统...")
    
    # 创建测试工作空间
    test_workspace = Path("test_workspace")
    test_workspace.mkdir(exist_ok=True)
    
    # 创建测试Agent
    agent = BaseAgent(
        agent_id="test_agent",
        session_id="test_session",
        workspace_path=str(test_workspace)
    )
    
    print(f"✅ Agent创建成功: {agent.name}")
    print(f"📁 工作空间: {agent.agent_workspace}")
    
    # 测试记忆功能
    test_message = Message(content="这是一条测试记忆", role="user")
    agent.record_work_memory("测试任务", "测试结果")
    
    # 检查记忆文件是否创建
    memory_dir = agent.agent_workspace / "memory"
    if memory_dir.exists():
        print(f"✅ 记忆目录已创建: {memory_dir}")
        for file in memory_dir.iterdir():
            print(f"  📄 记忆文件: {file.name}")
    else:
        print("❌ 记忆目录未创建")
    
    # 测试记忆恢复
    print("\n🔄 测试记忆恢复...")
    agent2 = BaseAgent(
        agent_id="test_agent",
        session_id="test_session",
        workspace_path=str(test_workspace)
    )
    
    context = agent2.get_work_context()
    print(f"📖 恢复的工作上下文: {context}")
    
    print("\n✅ 记忆系统测试完成")

if __name__ == "__main__":
    asyncio.run(test_memory_system())