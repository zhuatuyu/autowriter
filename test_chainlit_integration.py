#!/usr/bin/env python3
"""
测试Chainlit应用的完整集成功能
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.project_service import ProjectService
from backend.services.agent_service import AgentService
from backend.services.environment import Environment
from backend.models.project import Project

async def test_project_creation():
    """测试项目创建功能"""
    print("🧪 测试项目创建...")
    
    project_service = ProjectService()
    
    # 创建测试项目
    test_project = Project(
        name="测试项目",
        description="这是一个测试项目，用于验证系统功能"
    )
    
    try:
        created_project = await project_service.create_project(test_project)
        print(f"✅ 项目创建成功: {created_project.name} (ID: {created_project.id})")
        return created_project
    except Exception as e:
        print(f"❌ 项目创建失败: {str(e)}")
        return None

async def test_agent_service(project_id: str):
    """测试智能体服务"""
    print("🤖 测试智能体服务...")
    
    agent_service = AgentService()
    environment = Environment()
    
    try:
        # 测试消息处理
        response = await agent_service.process_message(
            project_id=project_id,
            message="请帮我写一份技术文档",
            environment=environment
        )
        print(f"✅ 智能体响应: {response}")
        return True
    except Exception as e:
        print(f"❌ 智能体服务失败: {str(e)}")
        return False

async def test_project_list():
    """测试项目列表功能"""
    print("📋 测试项目列表...")
    
    project_service = ProjectService()
    
    try:
        projects = await project_service.get_all_projects()
        print(f"✅ 获取到 {len(projects)} 个项目")
        for project in projects:
            print(f"   - {project.name}: {project.description}")
        return True
    except Exception as e:
        print(f"❌ 获取项目列表失败: {str(e)}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始Chainlit集成测试...\n")
    
    # 测试项目创建
    project = await test_project_creation()
    if not project:
        print("❌ 项目创建测试失败，停止测试")
        return
    
    print()
    
    # 测试智能体服务
    agent_success = await test_agent_service(project.id)
    if not agent_success:
        print("❌ 智能体服务测试失败")
    
    print()
    
    # 测试项目列表
    list_success = await test_project_list()
    if not list_success:
        print("❌ 项目列表测试失败")
    
    print()
    
    if agent_success and list_success:
        print("🎉 所有测试通过！Chainlit应用应该可以正常工作了")
    else:
        print("⚠️ 部分测试失败，请检查相关功能")

if __name__ == "__main__":
    asyncio.run(main())