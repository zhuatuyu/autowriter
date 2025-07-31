#!/usr/bin/env python3
"""
测试基于Environment的新架构集成
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加路径
sys.path.insert(0, '/Users/xuchuang/Desktop/PYTHON3/autowriter')

from backend.services.environment import Environment
from backend.roles.director import DirectorAgent
from backend.roles.case_expert import CaseExpertAgent
from backend.roles.writer_expert import WriterExpertAgent
from backend.roles.data_analyst import DataAnalystAgent
from backend.utils.project_repo import ProjectRepo
from metagpt.actions.add_requirement import UserRequirement
from metagpt.schema import Message

async def test_environment_integration():
    """测试Environment集成"""
    print("🧪 开始测试基于Environment的新架构...")
    
    # 1. 创建测试会话
    session_id = "test_session_001"
    project_repo = ProjectRepo(session_id)
    
    # 2. 创建Environment
    environment = Environment()
    print("✅ Environment创建成功")
    
    # 3. 创建各个角色
    try:
        director = DirectorAgent()
        case_expert = CaseExpertAgent()
        writer_expert = WriterExpertAgent()
        data_analyst = DataAnalystAgent()
        
        print("✅ 所有角色创建成功")
        
        # 4. 为角色注入ProjectRepo上下文
        for role in [case_expert, writer_expert, data_analyst]:
            role.set_context({"project_repo": project_repo})
        
        # 5. 将角色添加到Environment
        environment.add_roles([director, case_expert, writer_expert, data_analyst])
        print("✅ 角色已添加到Environment")
        
        # 6. 创建初始用户需求消息
        user_request = "写一份国内养老院建设服务项目提供给政府财政局的绩效报告，参考案例找1个就可以"
        initial_message = Message(
            content=user_request, 
            role="user", 
            cause_by=UserRequirement
        )
        
        # 7. 直接将消息发送给Director
        print("📨 直接向Director发送消息...")
        director.put_message(initial_message)
        
        # 8. 运行Environment（限制轮次避免无限循环）
        print("🚀 开始运行Environment...")
        
        # 分步运行，观察每一轮的情况
        for round_num in range(5):
            print(f"\n--- 第 {round_num + 1} 轮 ---")
            
            # 检查每个角色的状态
            for role_name, role in environment.get_roles().items():
                msg_count = len(role.rc.memory.get())
                print(f"  {role_name}: 消息数={msg_count}, 空闲={role.is_idle}")
            
            # 运行一轮
            await environment.run(k=1)
            
            # 检查是否所有角色都空闲
            if environment.is_idle:
                print("  所有角色都已空闲，停止运行")
                break
        
        print("✅ Environment运行完成")
        
        # 9. 检查输出文件
        reports_dir = project_repo.get_path("reports")
        if reports_dir.exists():
            report_files = list(reports_dir.glob("*.md"))
            if report_files:
                print(f"✅ 发现报告文件: {[f.name for f in report_files]}")
                # 显示第一个报告的前几行
                with open(report_files[0], 'r', encoding='utf-8') as f:
                    content = f.read()[:500]
                    print(f"📄 报告内容预览:\n{content}...")
            else:
                print("⚠️ 未发现报告文件")
        else:
            print("⚠️ 报告目录不存在")
            
        # 10. 检查所有角色的消息历史
        print("\n📋 角色消息历史:")
        for role_name, role in environment.get_roles().items():
            messages = role.rc.memory.get()
            print(f"  {role_name}: {len(messages)} 条消息")
            for i, msg in enumerate(messages):
                print(f"    {i+1}. {msg.role}: {msg.content[:100]}...")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

async def test_simple_director():
    """简单测试Director角色"""
    print("\n🧪 简单测试Director角色...")
    
    try:
        # 创建Environment和Director
        environment = Environment()
        director = DirectorAgent()
        environment.add_role(director)
        
        # 发送消息
        user_request = "写一份养老院建设项目的绩效报告"
        initial_message = Message(
            content=user_request, 
            role="user", 
            cause_by=UserRequirement
        )
        
        director.put_message(initial_message)
        print(f"✅ 消息已发送给Director: {user_request}")
        
        # 运行一轮
        print("🚀 运行Director...")
        await director.run()
        
        # 检查结果
        messages = director.rc.memory.get()
        print(f"📋 Director处理了 {len(messages)} 条消息")
        for i, msg in enumerate(messages):
            print(f"  {i+1}. {msg.role}: {msg.content[:200]}...")
            
    except Exception as e:
        print(f"❌ Director测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_director())
    asyncio.run(test_environment_integration())