#!/usr/bin/env python3
"""
直接测试CaseExpert智能体，验证其是否能正常工作
"""
import asyncio
import sys
import os

# 添加路径
sys.path.insert(0, '/Users/xuchuang/Desktop/PYTHON3/autowriter')
sys.path.insert(0, '/Users/xuchuang/Desktop/PYTHON3/autowriter/example/MetaGPT_bak')

# 设置环境变量
os.environ['PYTHONPATH'] = '/Users/xuchuang/Desktop/PYTHON3/autowriter/example/MetaGPT_bak'

from metagpt.logs import logger
from metagpt.schema import Message
from backend.roles.case_expert import CaseExpertAgent
from backend.configs.llm_provider import llm
from metagpt.config2 import config

async def test_case_expert():
    """直接测试CaseExpert智能体"""
    print("🚀 开始测试CaseExpert智能体...")
    
    try:
        # 初始化智能体
        print("📝 初始化CaseExpert智能体...")
        agent = CaseExpertAgent(
            name="TestCaseExpert",
            cases_dir="/Users/xuchuang/Desktop/PYTHON3/autowriter/workspaces/test_cases"
        )
        print(f"✅ 智能体初始化成功: {agent.profile}")
        print(f"📁 输出目录: {agent.cases_dir}")
        print(f"🔍 搜索引擎: {type(agent.search_engine).__name__}")
        print(f"🎯 Actions: {[type(action).__name__ for action in agent.actions]}")
        
        # 创建测试消息
        test_topic = "国内养老院建设政府项目绩效评估报告"
        print(f"\n📨 创建测试消息: {test_topic}")
        
        msg = Message(content=test_topic, role="user")
        agent.put_message(msg)
        
        print(f"💭 智能体内存中的消息数量: {len(agent.rc.memory.storage)}")
        print(f"📋 当前待执行Action: {agent.rc.todo}")
        
        # 执行智能体
        print("\n🔄 开始执行智能体...")
        result = await agent.run()
        
        print(f"\n📊 执行结果:")
        print(f"  - 返回值类型: {type(result)}")
        print(f"  - 返回值内容: {result}")
        print(f"  - 内存中消息数量: {len(agent.rc.memory.storage)}")
        
        # 检查内存中的消息
        print(f"\n🧠 内存中的消息:")
        for i, memory_msg in enumerate(agent.rc.memory.storage):
            print(f"  消息 {i+1}:")
            print(f"    - 角色: {memory_msg.role}")
            print(f"    - 内容: {memory_msg.content[:100]}...")
            print(f"    - 触发者: {memory_msg.cause_by}")
            print(f"    - 指令内容类型: {type(memory_msg.instruct_content)}")
        
        if result:
            print("✅ 测试成功: 智能体正常返回结果")
            return True
        else:
            print("❌ 测试失败: 智能体返回None")
            return False
            
    except Exception as e:
        print(f"💥 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 CaseExpert智能体直接测试")
    print("=" * 60)
    
    success = asyncio.run(test_case_expert())
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试通过: 智能体工作正常")
    else:
        print("💀 测试失败: 智能体存在问题")
    print("=" * 60)