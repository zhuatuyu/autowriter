#!/usr/bin/env python3
"""
调试智能体文件保存问题的专用脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from backend.utils.project_repo import ProjectRepo
from backend.actions.case_research import ConductCaseResearch
from backend.actions.writer_action import WriteContent
from backend.actions.data_analyst_action import AnalyzeData

async def test_action_file_saving():
    """测试各个Action的文件保存功能"""
    print("🧪 测试Action文件保存功能")
    
    # 1. 创建ProjectRepo
    session_id = "debug_file_test"
    project_repo = ProjectRepo(session_id)
    print(f"📁 工作空间路径: {project_repo.root}")
    
    # 2. 测试ConductCaseResearch Action
    print("\n--- 测试 ConductCaseResearch ---")
    try:
        case_action = ConductCaseResearch()
        topic = "测试案例研究主题"
        content = "这是测试内容，用于验证案例研究报告的生成和保存功能。"
        
        result_path = await case_action.run(
            topic=topic,
            content=content,
            project_repo=project_repo
        )
        print(f"✓ ConductCaseResearch 完成，保存路径: {result_path}")
        
        # 验证文件是否存在
        if Path(result_path).exists():
            print(f"✓ 文件确实存在: {Path(result_path).stat().st_size} bytes")
        else:
            print("✗ 文件不存在！")
            
    except Exception as e:
        print(f"✗ ConductCaseResearch 失败: {e}")
    
    # 3. 测试WriteContent Action
    print("\n--- 测试 WriteContent ---")
    try:
        writer_action = WriteContent()
        topic = "测试写作主题"
        summary = "这是测试摘要内容"
        
        content = await writer_action.run(
            topic=topic,
            summary=summary,
            project_repo=project_repo
        )
        print(f"✓ WriteContent 完成，内容长度: {len(content)} 字符")
        
    except Exception as e:
        print(f"✗ WriteContent 失败: {e}")
    
    # 4. 测试AnalyzeData Action
    print("\n--- 测试 AnalyzeData ---")
    try:
        analyst_action = AnalyzeData()
        data_content = "测试数据内容"
        analysis_type = "基础分析"
        
        result = await analyst_action.run(
            data_content=data_content,
            analysis_type=analysis_type,
            project_repo=project_repo
        )
        print(f"✓ AnalyzeData 完成，结果长度: {len(result)} 字符")
        
    except Exception as e:
        print(f"✗ AnalyzeData 失败: {e}")
    
    # 5. 检查所有生成的文件
    print("\n📄 检查所有生成的文件:")
    workspace_files = list(project_repo.root.glob("**/*"))
    for file in workspace_files:
        if file.is_file():
            relative_path = file.relative_to(project_repo.root)
            print(f"  {relative_path} ({file.stat().st_size} bytes)")
    
    # 6. 测试project_repo的各个子目录
    print("\n📁 检查各子目录:")
    subdirs = ["reports", "analysis", "research", "cases", "drafts"]
    for subdir in subdirs:
        subdir_path = project_repo.get_path(subdir)
        if subdir_path.exists():
            files = list(subdir_path.glob("**/*"))
            file_count = len([f for f in files if f.is_file()])
            print(f"  {subdir}: {file_count} 个文件")
            for file in files:
                if file.is_file():
                    print(f"    - {file.name} ({file.stat().st_size} bytes)")
        else:
            print(f"  {subdir}: 目录不存在")

if __name__ == "__main__":
    asyncio.run(test_action_file_saving())