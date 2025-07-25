#!/usr/bin/env python
"""
测试案例专家Agent的功能
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.roles.case_expert import CaseExpertAgent
from pathlib import Path

async def test_case_expert():
    """测试案例专家的基本功能"""
    print("🧪 开始测试案例专家...")
    
    # 创建测试工作空间
    test_workspace = Path("test_workspace")
    test_workspace.mkdir(exist_ok=True)
    
    try:
        # 创建案例专家实例
        case_expert = CaseExpertAgent(
            agent_id="test_case_expert",
            session_id="test_session",
            workspace_path=str(test_workspace)
        )
        
        print("✅ 案例专家实例创建成功")
        print(f"📁 工作空间: {case_expert.agent_workspace}")
        print(f"🔍 搜索引擎: {type(case_expert.search_engine)}")
        print(f"⚡ Actions: {[action.__class__.__name__ for action in case_expert.actions]}")
        print(f"🔄 React Mode: {case_expert.rc.react_mode}")
        
        # 测试简单的案例研究任务
        test_topic = "智慧城市管理系统案例研究"
        print(f"\n🎯 开始执行测试任务: {test_topic}")
        
        # 调用案例专家进行研究
        result = await case_expert.run(test_topic)
        
        print(f"\n✅ 任务执行完成!")
        print(f"📋 结果类型: {type(result)}")
        if result:
            print(f"📄 结果内容: {result.content[:200]}...")
            if hasattr(result, 'instruct_content'):
                print(f"📊 指令内容: {type(result.instruct_content)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理测试文件（可选）
        # import shutil
        # shutil.rmtree(test_workspace, ignore_errors=True)
        pass

if __name__ == "__main__":
    success = asyncio.run(test_case_expert())
    if success:
        print("\n🎉 案例专家测试通过!")
    else:
        print("\n💥 案例专家测试失败!")
        sys.exit(1) 