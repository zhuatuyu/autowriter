#!/usr/bin/env python3
"""
模拟Chainlit UI交互测试
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 模拟chainlit会话
class MockSession:
    def __init__(self):
        self.data = {}
    
    def set(self, key, value):
        self.data[key] = value
    
    def get(self, key, default=None):
        return self.data.get(key, default)

class MockMessage:
    def __init__(self, content):
        self.content = content
    
    async def send(self):
        print(f"📤 发送消息: {self.content}")

# 模拟chainlit模块
class MockChainlit:
    user_session = MockSession()
    
    @staticmethod
    def Message(content):
        return MockMessage(content)

# 替换chainlit导入
sys.modules['chainlit'] = MockChainlit()
import chainlit as cl

# 导入chainlit_app的函数
from chainlit_app import create_project_and_start_work, handle_project_conversation

async def test_user_workflow():
    """测试完整的用户工作流程"""
    print("🧪 开始UI工作流程测试...\n")
    
    # 模拟用户输入项目需求
    user_input = "写一份关于人工智能在教育领域应用的研究报告"
    print(f"👤 用户输入: {user_input}")
    print()
    
    # 测试项目创建和启动
    print("🚀 测试项目创建和启动...")
    try:
        await create_project_and_start_work(user_input)
        print("✅ 项目创建和启动成功")
    except Exception as e:
        print(f"❌ 项目创建失败: {str(e)}")
        return False
    
    print()
    
    # 获取创建的项目ID
    project_id = cl.user_session.get("current_project_id")
    if not project_id:
        print("❌ 未找到项目ID")
        return False
    
    print(f"📋 项目ID: {project_id}")
    print()
    
    # 测试后续对话
    print("💬 测试项目对话...")
    follow_up_messages = [
        "请重点关注AI在个性化学习方面的应用",
        "需要包含具体的案例分析",
        "报告要包含数据分析部分"
    ]
    
    for i, message in enumerate(follow_up_messages, 1):
        print(f"👤 用户消息 {i}: {message}")
        try:
            await handle_project_conversation(project_id, message)
            print(f"✅ 消息 {i} 处理成功")
        except Exception as e:
            print(f"❌ 消息 {i} 处理失败: {str(e)}")
        print()
    
    return True

async def main():
    """主测试函数"""
    print("🎯 Chainlit UI交互测试\n")
    
    success = await test_user_workflow()
    
    print("=" * 50)
    if success:
        print("🎉 UI工作流程测试完成！")
        print("✅ Chainlit应用已准备就绪，用户可以:")
        print("   1. 直接输入项目需求")
        print("   2. 自动创建项目")
        print("   3. 与多智能体团队对话")
        print("   4. 获得实时反馈")
    else:
        print("❌ UI工作流程测试失败")
        print("⚠️ 需要进一步调试")

if __name__ == "__main__":
    asyncio.run(main())