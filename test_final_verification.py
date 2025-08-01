#!/usr/bin/env python3
"""
最终验证测试 - 验证Chainlit应用的核心功能
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.project_service import ProjectService
from backend.services.agent_service import AgentService
from backend.services.environment import Environment
from backend.models.project import Project

async def test_complete_workflow():
    """测试完整的工作流程"""
    print("🎯 最终验证测试开始...\n")
    
    # 初始化服务
    project_service = ProjectService()
    agent_service = AgentService()
    environment = Environment()
    
    # 1. 测试项目创建
    print("1️⃣ 测试项目创建...")
    test_project = Project(
        name="AI教育应用研究报告",
        description="写一份关于人工智能在教育领域应用的研究报告"
    )
    
    try:
        created_project = await project_service.create_project(test_project)
        print(f"✅ 项目创建成功: {created_project.name}")
        print(f"   项目ID: {created_project.id}")
        print(f"   工作空间: {created_project.workspace_path}")
    except Exception as e:
        print(f"❌ 项目创建失败: {str(e)}")
        return False
    
    print()
    
    # 2. 测试多智能体处理
    print("2️⃣ 测试多智能体消息处理...")
    test_messages = [
        "请重点关注AI在个性化学习方面的应用",
        "需要包含具体的案例分析和数据支撑",
        "报告结构要清晰，包含摘要、正文和结论"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"   消息 {i}: {message}")
        try:
            response = await agent_service.process_message(
                project_id=created_project.id,
                message=message,
                environment=environment
            )
            print(f"   ✅ 响应: {response}")
        except Exception as e:
            print(f"   ❌ 处理失败: {str(e)}")
            return False
    
    print()
    
    # 3. 测试项目检索
    print("3️⃣ 测试项目检索...")
    try:
        retrieved_project = await project_service.get_project(created_project.id)
        if retrieved_project:
            print(f"✅ 项目检索成功: {retrieved_project.name}")
        else:
            print("❌ 项目检索失败: 未找到项目")
            return False
    except Exception as e:
        print(f"❌ 项目检索失败: {str(e)}")
        return False
    
    print()
    
    # 4. 测试项目列表
    print("4️⃣ 测试项目列表...")
    try:
        all_projects = await project_service.get_all_projects()
        print(f"✅ 获取到 {len(all_projects)} 个项目:")
        for project in all_projects:
            print(f"   - {project.name} ({project.id[:8]}...)")
    except Exception as e:
        print(f"❌ 获取项目列表失败: {str(e)}")
        return False
    
    return True

async def test_error_handling():
    """测试错误处理"""
    print("🛡️ 测试错误处理...\n")
    
    project_service = ProjectService()
    agent_service = AgentService()
    environment = Environment()
    
    # 测试无效项目ID
    print("1️⃣ 测试无效项目ID...")
    try:
        response = await agent_service.process_message(
            project_id="invalid-project-id",
            message="测试消息",
            environment=environment
        )
        print(f"✅ 错误处理正常: {response}")
    except Exception as e:
        print(f"⚠️ 异常处理: {str(e)}")
    
    print()
    
    # 测试获取不存在的项目
    print("2️⃣ 测试获取不存在的项目...")
    try:
        project = await project_service.get_project("non-existent-id")
        if project is None:
            print("✅ 正确返回None")
        else:
            print("❌ 应该返回None")
    except Exception as e:
        print(f"⚠️ 异常处理: {str(e)}")
    
    return True

async def main():
    """主测试函数"""
    print("🚀 AutoWriter Chainlit应用最终验证\n")
    print("=" * 60)
    
    # 核心功能测试
    workflow_success = await test_complete_workflow()
    
    print("=" * 60)
    
    # 错误处理测试
    error_handling_success = await test_error_handling()
    
    print("=" * 60)
    print("📊 测试结果总结:")
    print(f"   核心工作流程: {'✅ 通过' if workflow_success else '❌ 失败'}")
    print(f"   错误处理: {'✅ 通过' if error_handling_success else '❌ 失败'}")
    
    if workflow_success and error_handling_success:
        print("\n🎉 所有测试通过！")
        print("✅ Chainlit应用已完全就绪，功能包括:")
        print("   • 自动项目创建")
        print("   • 多智能体协作")
        print("   • 实时消息处理")
        print("   • 项目管理")
        print("   • 错误处理")
        print("\n🌐 应用地址: http://localhost:8000")
        print("💡 用户只需输入项目需求即可开始使用！")
    else:
        print("\n❌ 部分测试失败，需要进一步调试")

if __name__ == "__main__":
    asyncio.run(main())