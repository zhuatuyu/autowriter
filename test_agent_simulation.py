#!/usr/bin/env python3
"""
测试智能体服务的完整流程
模拟用户输入："写一份祥符区2024年小麦"一喷三防"项目财政重点绩效评价报告"
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.agent_service import AgentService
from backend.services.environment import Environment

async def test_agent_service():
    """测试智能体服务"""
    print("🚀 开始测试智能体服务...")
    
    # 创建环境和服务
    environment = Environment()
    agent_service = AgentService()
    
    # 模拟用户输入
    test_message = "写一份祥符区2024年小麦\"一喷三防\"项目财政重点绩效评价报告"
    project_id = "test_project_001"
    
    print(f"📝 测试消息: {test_message}")
    print(f"🆔 项目ID: {project_id}")
    print("-" * 60)
    
    try:
        # 处理消息
        result = await agent_service.process_message(
            project_id=project_id,
            message=test_message,
            environment=environment
        )
        
        print(f"✅ 处理结果: {result}")
        print("-" * 60)
        print("🎉 测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_service())