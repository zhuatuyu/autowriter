#!/usr/bin/env python3
"""
完整的智能体工作流程测试
测试整个养老院建设项目报告生成流程，确保所有智能体正常工作并生成完整结果
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.services.environment import Environment
from backend.roles.director import DirectorAgent
from backend.roles.case_expert import CaseExpertAgent
from backend.roles.data_analyst import DataAnalystAgent
from backend.roles.writer_expert import WriterExpertAgent
from backend.models.session import WorkSession, SessionState
from backend.utils.project_repo import ProjectRepo
from datetime import datetime


async def test_complete_workflow():
    """测试完整的智能体工作流程"""
    print("🚀 开始完整工作流程测试...")
    
    # 1. 创建结果目录
    results_dir = project_root / "test_results"
    results_dir.mkdir(exist_ok=True)
    
    # 清理之前的测试结果
    for file in results_dir.glob("*"):
        if file.is_file():
            file.unlink()
    
    print(f"📁 结果目录已创建: {results_dir}")
    
    # 2. 初始化项目仓库
    session_id = "test_workflow_session"
    project_repo = ProjectRepo(session_id)
    
    # 3. 创建智能体
    print("🤖 创建智能体...")
    director = DirectorAgent()
    case_expert = CaseExpertAgent()
    data_analyst = DataAnalystAgent()
    writer_expert = WriterExpertAgent()
    
    # 4. 创建环境并添加智能体
    env = Environment()
    env.add_role(director)
    env.add_role(case_expert)
    env.add_role(data_analyst)
    env.add_role(writer_expert)
    
    # 5. 设置项目仓库
    for role in [director, case_expert, data_analyst, writer_expert]:
        role.project_repo = project_repo
    
    # 6. 创建会话（简化版本，不使用SessionManager）
    print(f"📋 创建测试会话: {session_id}")
    
    print("📝 开始执行养老院建设项目报告生成任务...")
    
    # 7. 定义测试需求
    user_requirement = """为政府财政局撰写一份关于国内养老院建设服务项目的绩效报告，包含一个参考案例分析、项目绩效数据及结论建议，以支持财政决策。

具体要求：
1. 包含至少一个成功的养老院建设案例分析
2. 提供相关的绩效数据和图表分析
3. 给出明确的结论和政策建议
4. 报告格式符合政府公文标准
"""
    
    # 8. 处理用户需求
    print(f"📋 用户需求: {user_requirement}")
    
    try:
        # 让Director处理需求并生成计划
        plan = await director.process_request(user_requirement)
        print("✅ Director已生成执行计划")
        
        if not plan:
            print("❌ 错误：Director未能生成有效计划！")
            return False
            
        # 手动将计划作为消息发布到环境中
        from metagpt.schema import Message
        plan_message = Message(
            content=plan.model_dump_json(),
            role="Director",
            cause_by=DirectorAgent
        )
        env.publish_message(plan_message)
        print("📨 计划消息已发布到环境中")
        
        # 添加调试信息：检查智能体是否接收到消息
        print("\n🔍 检查智能体消息接收状态:")
        for role in [case_expert, data_analyst, writer_expert]:
            print(f"  {role.profile}: 消息数={len(role.rc.memory.storage)}, 新消息数={len(role.rc.news)}")
            if role.rc.news:
                print(f"    最新消息来源: {role.rc.news[0].cause_by}")
                print(f"    消息内容长度: {len(role.rc.news[0].content)}")
        
        # 运行环境执行任务
        print("\n🔄 开始执行环境任务...")
        
        # 手动触发智能体的_think和_act方法
        for role in [case_expert, data_analyst, writer_expert]:
            if role.rc.news:
                print(f"\n🤖 手动触发 {role.profile} 的思考和行动...")
                try:
                    # 调用_think方法
                    should_act = await role._think()
                    print(f"  {role.profile}._think() 返回: {should_act}")
                    
                    if should_act and role.rc.todo:
                        # 调用_act方法
                        print(f"  {role.profile} 开始执行 {role.rc.todo}")
                        result = await role._act()
                        print(f"  {role.profile}._act() 完成，结果: {type(result)}")
                        
                        # 检查是否需要继续执行下一个action
                        if hasattr(role, 'actions') and len(role.actions) > 1:
                            current_action_index = role.actions.index(role.rc.todo) if role.rc.todo in role.actions else 0
                            if current_action_index < len(role.actions) - 1:
                                # 设置下一个action
                                role.rc.todo = role.actions[current_action_index + 1]
                                print(f"  {role.profile}: 设置下一个action为 {role.rc.todo}")
                                
                                # 继续执行下一个action
                                act_result2 = await role._act()
                                print(f"  {role.profile}._act() 第二次完成，结果: {type(act_result2)}")
                                
                                # 如果还有第三个action
                                if current_action_index + 1 < len(role.actions) - 1:
                                    role.rc.todo = role.actions[current_action_index + 2]
                                    print(f"  {role.profile}: 设置第三个action为 {role.rc.todo}")
                                    act_result3 = await role._act()
                                    print(f"  {role.profile}._act() 第三次完成，结果: {type(act_result3)}")
                    else:
                        print(f"  {role.profile} 没有需要执行的任务")
                except Exception as e:
                    print(f"  {role.profile} 执行出错: {e}")
                    import traceback
                    traceback.print_exc()
        
        # 检查是否有文件生成
        workspace_path = Path("workspaces") / session_id
        generated_files = []
        if workspace_path.exists():
            for file_path in workspace_path.rglob("*"):
                if file_path.is_file():
                    generated_files.append(str(file_path))
        print(f"\n📁 发现生成文件: {generated_files}")
        
        print("✅ 环境执行完成")
        
        # 9. 检查生成的文件
        print("\n📊 检查生成的结果文件...")
        
        # 检查工作空间目录
        workspace_path = Path("workspaces/test_workflow_session")
        generated_files = []
        
        if workspace_path.exists():
            for file_path in workspace_path.rglob("*.md"):
                if file_path.is_file():
                    generated_files.append(file_path)
                    print(f"✅ 发现文件: {file_path}")
        
        if not generated_files:
            print("❌ 错误：没有生成任何文件！")
            return False
            
        print(f"✅ 共生成 {len(generated_files)} 个文件:")
        for file in generated_files:
            print(f"  - {file.name} ({file.stat().st_size} bytes)")
            
        # 10. 验证关键文件是否存在
        expected_files = [
            "案例搜索结果.md",
            "案例分析报告.md", 
            "绩效数据分析.md",
            "养老院建设项目绩效报告.md"
        ]
        
        missing_files = []
        for expected_file in expected_files:
            if not (results_dir / expected_file).exists():
                missing_files.append(expected_file)
                
        if missing_files:
            print(f"⚠️  缺少预期文件: {missing_files}")
        else:
            print("✅ 所有预期文件都已生成")
            
        # 11. 检查最终报告内容
        final_report_path = results_dir / "养老院建设项目绩效报告.md"
        if final_report_path.exists():
            with open(final_report_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"\n📄 最终报告内容预览 ({len(content)} 字符):")
                print("=" * 50)
                print(content[:500] + "..." if len(content) > 500 else content)
                print("=" * 50)
                
                # 验证报告包含关键部分
                required_sections = ["案例分析", "绩效", "建议", "结论"]
                missing_sections = [section for section in required_sections 
                                  if section not in content]
                
                if missing_sections:
                    print(f"⚠️  报告缺少关键章节: {missing_sections}")
                else:
                    print("✅ 报告包含所有关键章节")
        
        # 12. 生成测试总结报告
        summary_report = {
            "test_time": str(asyncio.get_event_loop().time()),
            "session_id": session_id,
            "user_requirement": user_requirement,
            "generated_files": [f.name for f in generated_files],
            "file_sizes": {f.name: f.stat().st_size for f in generated_files},
            "missing_files": missing_files,
            "test_status": "SUCCESS" if not missing_files else "PARTIAL_SUCCESS"
        }
        
        with open(results_dir / "test_summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary_report, f, ensure_ascii=False, indent=2)
            
        print(f"\n📋 测试总结已保存到: {results_dir / 'test_summary.json'}")
        print(f"🎯 测试状态: {summary_report['test_status']}")
        
        return len(missing_files) == 0
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 保存错误信息
        error_report = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "test_status": "FAILED"
        }
        
        with open(results_dir / "error_report.json", 'w', encoding='utf-8') as f:
            json.dump(error_report, f, ensure_ascii=False, indent=2)
            
        return False


async def main():
    """主函数"""
    print("🧪 智能体完整工作流程测试")
    print("=" * 60)
    
    success = await test_complete_workflow()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试成功完成！所有智能体正常工作，生成了完整的报告。")
    else:
        print("⚠️  测试部分成功或失败，请检查生成的文件和错误报告。")
    
    print(f"📁 所有结果文件保存在: {project_root / 'test_results'}")


if __name__ == "__main__":
    asyncio.run(main())