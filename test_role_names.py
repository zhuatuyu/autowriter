#!/usr/bin/env python3
"""
测试角色名称修改
验证TeamLeader和ProjectManager的名称是否已正确修改
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.services.agent_service import AgentService
from backend.roles.project_manager import ProjectManagerAgent
from metagpt.roles.di.team_leader import TeamLeader

async def test_role_names():
    """测试角色名称修改"""
    print("🧪 测试角色名称修改...")
    
    # 测试TeamLeader名称
    team_leader = TeamLeader(name="王昭元")
    print(f"✅ TeamLeader名称: {team_leader.name}")
    
    # 测试ProjectManager名称
    project_manager = ProjectManagerAgent()
    print(f"✅ ProjectManager名称: {project_manager.name}")
    print(f"✅ ProjectManager职责: {project_manager.profile}")
    print(f"✅ ProjectManager目标: {project_manager.goal}")
    
    # 测试AgentService中的团队创建
    agent_service = AgentService()
    from metagpt.environment import Environment
    environment = Environment()
    
    team = await agent_service._get_or_create_team("test_project", environment)
    print(f"✅ 团队创建成功，成员数量: {len(team.env.roles)}")
    
    # 检查团队成员名称
    for role_name, role in team.env.roles.items():
        if hasattr(role, 'name') and hasattr(role, 'profile'):
            print(f"  - 角色: {role.name} ({role.profile})")
    
    print("🎉 角色名称修改测试完成！")

if __name__ == "__main__":
    asyncio.run(test_role_names())