#!/usr/bin/env python3
"""
测试 ProjectRepo 与 CaseExpertAgent 集成功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入必要的模块
from metagpt.context import Context
from backend.utils.project_repo import ProjectRepo
from backend.roles.case_expert import CaseExpertAgent
from backend.actions.case_research import ConductCaseResearch

def test_project_repo_basic():
    """测试 ProjectRepo 基本功能"""
    print("🧪 测试 ProjectRepo 基本功能...")
    
    # 使用测试会话ID
    test_session_id = "test_123456"
    
    # 创建 ProjectRepo 实例
    project_repo = ProjectRepo(test_session_id)
    
    # 验证基本属性
    assert project_repo.session_id == test_session_id
    assert project_repo.root.name == f"project_{test_session_id}"
    
    # 验证目录结构
    expected_dirs = [
        'uploads', 'research', 'analysis', 
        'design', 'drafts', 'outputs'
    ]
    
    for dir_name in expected_dirs:
        dir_path = project_repo.get_path(dir_name)
        assert dir_path.exists(), f"目录 {dir_name} 不存在"
        print(f"  ✅ 目录 {dir_name}: {dir_path}")
    
    # 测试嵌套目录
    cases_dir = project_repo.get_path('research/cases')
    assert cases_dir.exists(), "案例研究目录不存在"
    print(f"  ✅ 案例研究目录: {cases_dir}")
    
    # 测试文件保存
    test_content = "这是一个测试文件"
    saved_path = project_repo.save_file("test.txt", test_content, "outputs")
    assert saved_path.exists(), "文件保存失败"
    assert saved_path.read_text(encoding='utf-8') == test_content, "文件内容不匹配"
    print(f"  ✅ 文件保存测试: {saved_path}")
    
    print("🎉 ProjectRepo 基本功能测试通过！\n")
    return project_repo

def test_context_injection():
    """测试 Context 注入功能"""
    print("🧪 测试 Context 注入功能...")
    
    test_session_id = "test_context_123"
    
    # 创建 ProjectRepo
    project_repo = ProjectRepo(test_session_id)
    
    # 创建 Context 并注入 ProjectRepo
    context = Context()
    context.kwargs.set('project_repo', project_repo)
    
    # 验证注入成功
    retrieved_repo = context.kwargs.get('project_repo')
    assert retrieved_repo is not None, "ProjectRepo 注入失败"
    assert retrieved_repo.session_id == test_session_id, "ProjectRepo 会话ID不匹配"
    
    print(f"  ✅ ProjectRepo 成功注入到 Context")
    print(f"  ✅ 会话ID匹配: {retrieved_repo.session_id}")
    print("🎉 Context 注入功能测试通过！\n")
    return context, project_repo

async def test_case_research_action():
    """测试 ConductCaseResearch Action"""
    print("🧪 测试 ConductCaseResearch Action...")
    
    test_session_id = "test_action_123"
    
    # 创建 ProjectRepo
    project_repo = ProjectRepo(test_session_id)
    
    # 创建 Context 并注入 ProjectRepo
    context = Context()
    context.kwargs.set('project_repo', project_repo)
    
    # 创建 ConductCaseResearch Action
    action = ConductCaseResearch(context=context)
    
    # 测试数据
    test_topic = "苹果公司的商业模式分析"
    test_content = """
    苹果公司是全球领先的科技公司，以其创新的产品设计和强大的品牌影响力著称。
    
    **商业模式特点：**
    1. 硬件销售：iPhone、iPad、Mac等产品是主要收入来源
    2. 服务业务：App Store、iCloud、Apple Music等服务快速增长
    3. 生态系统：通过软硬件一体化创造用户粘性
    4. 高端定位：专注于高端市场，保持较高的利润率
    
    **财务表现：**
    - 2023年营收达到3943亿美元
    - 毛利率保持在40%以上
    - 服务业务毛利率超过70%
    
    **竞争优势：**
    - 强大的品牌价值
    - 完整的生态系统
    - 持续的创新能力
    - 优秀的供应链管理
    """
    
    try:
        # 执行 Action
        result_path = await action.run(test_topic, test_content, project_repo)
        
        # 验证结果
        assert result_path is not None, "Action 执行结果为空"
        assert result_path.exists(), "报告文件未生成"
        
        # 验证文件内容
        saved_content = result_path.read_text(encoding='utf-8')
        assert len(saved_content) > 100, "保存的文件内容太短"
        assert "苹果" in saved_content, "报告内容不包含关键词"
        
        print(f"  ✅ Action 执行成功")
        print(f"  ✅ 报告已保存: {result_path}")
        print(f"  ✅ 报告长度: {len(saved_content)} 字符")
        
        print("🎉 ConductCaseResearch Action 测试通过！\n")
        return result_path
        
    except Exception as e:
        print(f"  ❌ Action 执行失败: {e}")
        raise

async def test_case_expert_agent():
    """测试 CaseExpertAgent 完整功能"""
    print("🧪 测试 CaseExpertAgent 完整功能...")
    
    test_session_id = "test_agent_123"
    
    # 创建 ProjectRepo
    project_repo = ProjectRepo(test_session_id)
    
    # 注入 ProjectRepo
    context = Context()
    context.kwargs.set('project_repo', project_repo)
    
    # 创建 CaseExpertAgent
    agent = CaseExpertAgent(context=context)
    
    # 测试用户请求
    user_request = "请分析特斯拉公司的电动汽车业务模式"
    
    try:
        # 添加用户消息到agent的内存
        from metagpt.schema import Message
        user_message = Message(content=user_request, role="user")
        agent.rc.memory.add(user_message)
        
        # 设置当前要执行的action（模拟正常的工作流程）
        # 我们直接测试最后一个action：ConductCaseResearch
        agent.rc.todo = ConductCaseResearch()
        
        # 创建一个包含案例研究数据的消息（模拟前面步骤的结果）
        from backend.roles.case_expert import CaseReport
        test_report = CaseReport(
            topic=user_request,
            links={
                "特斯拉商业模式分析": ["https://example1.com", "https://example2.com"]
            },
            summaries={
                "https://example1.com": "特斯拉通过直销模式和垂直整合策略，在电动汽车市场建立了强大的竞争优势。",
                "https://example2.com": "特斯拉的超级充电网络和自动驾驶技术是其核心差异化优势。"
            }
        )
        
        # 添加包含案例数据的消息
        case_message = Message(
            content="",
            instruct_content=test_report,
            role="case_expert"
        )
        agent.rc.memory.add(case_message)
        
        # 执行智能体任务
        result = await agent._act()
        
        # 验证结果
        assert result is not None, "智能体执行结果为空"
        assert hasattr(result, 'instruct_content'), "结果消息缺少 instruct_content"
        
        print(f"  ✅ CaseExpertAgent 执行成功")
        print(f"  ✅ 结果类型: {type(result)}")
        
        # 验证文件保存
        cases_dir = project_repo.get_path('research/cases')
        saved_files = list(cases_dir.glob("*.md"))
        assert len(saved_files) > 0, "没有找到保存的案例研究文件"
        
        print(f"  ✅ 共保存了 {len(saved_files)} 个案例研究文件")
        
        # 验证最新文件内容
        latest_file = max(saved_files, key=lambda x: x.stat().st_mtime)
        saved_content = latest_file.read_text(encoding='utf-8')
        assert "特斯拉" in saved_content, "报告内容不包含关键词"
        print(f"  ✅ 最新报告: {latest_file}")
        
        print("🎉 CaseExpertAgent 完整功能测试通过！\n")
        return result
        
    except Exception as e:
        print(f"  ❌ CaseExpertAgent 执行失败: {e}")
        raise

async def main():
    """主测试函数"""
    print("🚀 开始 ProjectRepo 集成测试\n")
    
    try:
        # 1. 测试 ProjectRepo 基本功能
        test_project_repo_basic()
        
        # 2. 测试 Context 注入
        test_context_injection()
        
        # 3. 测试 ConductCaseResearch Action
        await test_case_research_action()
        
        # 4. 测试 CaseExpertAgent 完整功能
        await test_case_expert_agent()
        
        print("🎉🎉🎉 所有测试通过！ProjectRepo 集成功能正常工作！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())