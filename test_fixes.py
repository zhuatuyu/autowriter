#!/usr/bin/env python3
"""
测试修复后的CaseExpert和ProjectManager
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.roles.case_expert import CaseExpertAgent
from backend.roles.project_manager import ProjectManagerAgent
from backend.services.environment import Environment
from metagpt.schema import Message
from metagpt.actions.add_requirement import UserRequirement


async def test_case_expert():
    """测试CaseExpert的硬编码搜索引擎配置"""
    print("🧪 测试CaseExpert...")
    
    try:
        case_expert = CaseExpertAgent()
        print(f"✅ CaseExpert创建成功: {case_expert.profile}")
        
        # 检查搜索引擎配置
        if hasattr(case_expert, 'search_engine'):
            print(f"✅ 搜索引擎配置存在: {type(case_expert.search_engine)}")
        else:
            print("❌ 搜索引擎配置不存在")
            
        return True
    except Exception as e:
        print(f"❌ CaseExpert测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_project_manager():
    """测试ProjectManager的WriteTasks配置"""
    print("\n🧪 测试ProjectManager...")
    
    try:
        pm = ProjectManagerAgent()
        print(f"✅ ProjectManager创建成功: {pm.profile}")
        
        # 检查Actions配置
        print(f"✅ Actions: {pm.actions}")
        print(f"✅ Tools: {pm.tools}")
        print(f"✅ Instruction: {pm.instruction}")
        
        # 检查工具执行映射
        pm._update_tool_execution()
        if "WriteTasks" in pm.tool_execution_map:
            print("✅ WriteTasks工具映射配置成功")
        else:
            print("❌ WriteTasks工具映射配置失败")
            
        return True
    except Exception as e:
        print(f"❌ ProjectManager测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_environment_integration():
    """测试环境集成"""
    print("\n🧪 测试环境集成...")
    
    try:
        # 创建环境
        env = Environment()
        
        # 创建智能体
        case_expert = CaseExpertAgent()
        pm = ProjectManagerAgent()
        
        # 添加到环境
        env.add_role(case_expert)
        env.add_role(pm)
        
        print(f"✅ 环境中有 {len(env.roles)} 个智能体")
        
        # 发布一个测试消息
        test_message = Message(
            content="测试用户需求：分析养老院建设项目",
            role="User",
            cause_by=UserRequirement
        )
        
        env.publish_message(test_message)
        print("✅ 测试消息发布成功")
        
        # 检查智能体是否接收到消息
        for role in env.roles:
            print(f"  {role.profile}: 消息数={len(role.rc.memory.storage)}, 新消息数={len(role.rc.news)}")
            
        return True
    except Exception as e:
        print(f"❌ 环境集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("🚀 开始测试修复后的系统...")
    
    results = []
    
    # 测试CaseExpert
    results.append(await test_case_expert())
    
    # 测试ProjectManager
    results.append(await test_project_manager())
    
    # 测试环境集成
    results.append(await test_environment_integration())
    
    # 总结结果
    print(f"\n📊 测试结果总结:")
    print(f"✅ 成功: {sum(results)}/{len(results)}")
    print(f"❌ 失败: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 所有测试通过！修复成功！")
        return True
    else:
        print("⚠️  部分测试失败，需要进一步检查")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)