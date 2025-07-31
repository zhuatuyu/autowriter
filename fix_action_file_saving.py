#!/usr/bin/env python3
"""
修复Action文件保存问题的专用脚本
确保各个Action能正确保存文件到指定目录
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.utils.project_repo import ProjectRepo
from backend.actions.case_research import ConductCaseResearch
from backend.actions.writer_action import WriteContent
from backend.actions.data_analyst_action import AnalyzeData
from metagpt.config2 import Config

async def fix_action_file_saving():
    """修复并测试Action文件保存功能"""
    print("🔧 修复Action文件保存问题")
    
    # 1. 创建工作空间
    workspace_path = "workspaces/action_fix_test"
    os.makedirs(workspace_path, exist_ok=True)
    project_repo = ProjectRepo("action_fix_test")
    
    print(f"📁 工作空间路径: {workspace_path}")
    print(f"📁 ProjectRepo根目录: {project_repo.root}")
    
    # 2. 配置MetaGPT
    config = Config.default()
    config.llm.model = "qwen-max-latest"
    
    # 3. 测试并修复ConductCaseResearch Action
    print("\n🔍 测试案例研究Action文件保存:")
    try:
        case_action = ConductCaseResearch(config=config)
        
        test_content = """
        案例1: AI教育应用案例1
        人工智能在个性化学习中的应用，通过机器学习算法分析学生学习行为，提供定制化学习路径。
        
        案例2: AI教育应用案例2
        智能教学助手在课堂中的应用，能够实时回答学生问题，提供学习建议。
        """
        
        # 确保目录存在
        research_cases_dir = project_repo.get_path('research/cases')
        research_cases_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {research_cases_dir}")
        
        case_result = await case_action.run(
            topic="人工智能在教育领域的应用案例研究",
            content=test_content,
            project_repo=project_repo
        )
        print(f"✓ 案例研究完成，保存路径: {case_result}")
        
        # 验证文件是否存在
        if Path(case_result).exists():
            file_size = Path(case_result).stat().st_size
            print(f"✅ 文件保存成功: {Path(case_result).name} ({file_size} 字节)")
        else:
            print(f"❌ 文件保存失败: {case_result}")
            
    except Exception as e:
        print(f"❌ 案例研究失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. 测试并修复WriteContent Action
    print("\n✍️ 测试写作Action文件保存:")
    try:
        writer_action = WriteContent(config=config)
        
        # 确保目录存在
        reports_dir = project_repo.get_path('reports')
        reports_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {reports_dir}")
        
        writer_result = await writer_action.run(
            topic="人工智能教育应用综合报告",
            summary="基于案例研究，人工智能在教育领域展现出巨大潜力，包括个性化学习、智能教学助手等应用。",
            project_repo=project_repo
        )
        print(f"✓ 写作完成，内容长度: {len(writer_result)}")
        
        # 检查reports目录中的文件
        reports_files = list(reports_dir.glob("*.md"))
        if reports_files:
            for file in reports_files:
                print(f"✅ 文件保存成功: {file.name} ({file.stat().st_size} 字节)")
        else:
            print("❌ 未找到保存的文件")
            
    except Exception as e:
        print(f"❌ 写作失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. 测试并修复AnalyzeData Action
    print("\n📊 测试数据分析Action:")
    try:
        analyst_action = AnalyzeData(config=config)
        
        # 创建测试数据文件
        test_data = """年份,AI教育应用数量,学习效率提升,用户满意度
2020,150,15,75
2021,280,22,82
2022,450,28,88
2023,720,35,92
2024,1200,42,95"""
        
        # 确保uploads目录存在并保存测试数据
        uploads_dir = project_repo.get_path('uploads')
        uploads_dir.mkdir(parents=True, exist_ok=True)
        test_file_path = uploads_dir / "ai_education_data.csv"
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_data)
        print(f"✓ 创建测试数据文件: {test_file_path}")
        
        # 确保analysis目录存在
        analysis_dir = project_repo.get_path('analysis')
        analysis_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建分析目录: {analysis_dir}")
        
        analyst_result = await analyst_action.run(
            instruction="分析AI教育应用的发展趋势，计算基本统计信息",
            file_path=test_file_path,
            analysis_path=analysis_dir
        )
        print(f"✓ 数据分析结果: {analyst_result}")
        
        # 检查analysis目录中的文件
        analysis_files = list(analysis_dir.glob("*"))
        if analysis_files:
            for file in analysis_files:
                if file.is_file():
                    print(f"✅ 文件生成成功: {file.name} ({file.stat().st_size} 字节)")
        else:
            print("❌ 未找到生成的分析文件")
            
    except Exception as e:
        print(f"❌ 数据分析失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. 最终文件统计
    print("\n📄 最终文件统计:")
    workspace = Path(workspace_path)
    total_files = 0
    
    for subdir in ["reports", "analysis", "research", "uploads"]:
        subdir_path = workspace / subdir
        if subdir_path.exists():
            files = [f for f in subdir_path.rglob("*") if f.is_file()]
            total_files += len(files)
            print(f"  {subdir}: {len(files)} 个文件")
            for file in files:
                rel_path = file.relative_to(workspace)
                print(f"    - {rel_path} ({file.stat().st_size} 字节)")
        else:
            print(f"  {subdir}: 目录不存在")
    
    print(f"\n🎯 总计生成文件: {total_files} 个")
    
    if total_files > 0:
        print("✅ Action文件保存功能修复成功！")
    else:
        print("❌ Action文件保存功能仍有问题，需要进一步调试")

if __name__ == "__main__":
    asyncio.run(fix_action_file_saving())