#!/usr/bin/env python3
"""
测试WebSocket管理器修复是否正确
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.services.company import AICompany
from backend.services.websocket_manager import WebSocketManager

async def test_websocket_fix():
    """测试WebSocket管理器修复"""
    print("🧪 开始测试WebSocket管理器修复...")
    
    try:
        # 创建WebSocket管理器
        websocket_manager = WebSocketManager()
        
        # 创建AI公司管理器
        session_id = "test_session_123"
        company = AICompany(session_id)
        
        print(f"✅ AI公司管理器创建成功: {session_id}")
        
        # 测试项目启动
        test_requirement = "创建一个简单的测试项目，用于验证WebSocket功能"
        
        print("🚀 开始启动项目...")
        success = await company.start_project(test_requirement, websocket_manager)
        
        if success:
            print("✅ 项目启动成功，没有出现WebSocket管理器错误")
            
            # 等待一段时间让项目运行
            await asyncio.sleep(3)
            
            # 检查项目状态
            status = company.get_project_status()
            print(f"📊 项目状态: {status}")
            
            # 停止项目
            company.stop_project()
            print("🛑 项目已停止")
            
        else:
            print("❌ 项目启动失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("🎉 测试完成，WebSocket管理器修复验证成功")
    return True

if __name__ == "__main__":
    # 运行测试
    result = asyncio.run(test_websocket_fix())
    sys.exit(0 if result else 1)