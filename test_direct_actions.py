#!/usr/bin/env python3
"""
直接测试Action执行脚本
绕过复杂的智能体协作机制，直接测试各个Action的执行效果
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

async def test_direct_actions():
    """直接测试各个Action的执行"""
    print("🧪 直接测试Action执行")
    
    # 1. 创建工作空间
    workspace_path = "workspaces/direct_action_test"
    os.makedirs(workspace_path, exist_ok=True)
    project_repo = ProjectRepo(workspace_path)
    
    print(f"📁 工作空间路径: {workspace_path}")
    
    # 2. 配置MetaGPT
    config = Config.default()
    config.llm.model = "qwen-max-latest"
    
    # 3. 测试ConductCaseResearch Action
    print("\n🔍 测试案例研究Action:")
    try:
        case_action = ConductCaseResearch(config=config)
        
        # 准备测试内容
        test_content = """
        案例1: AI教育应用案例1
        人工智能在个性化学习中的应用，通过机器学习算法分析学生学习行为，提供定制化学习路径。
        
        案例2: AI教育应用案例2
        智能教学助手在课堂中的应用，能够实时回答学生问题，提供学习建议。
        """
        
        case_result = await case_action.run(
            topic="人工智能在教育领域的应用案例研究",
            content=test_content,
            project_repo=project_repo
        )
        print(f"✓ 案例研究完成，保存路径: {case_result}")
        
        # 检查文件是否生成
        research_dir = Path(workspace_path) / "research" / "cases"
        if research_dir.exists():
            files = list(research_dir.glob("*.md"))
            print(f"✓ 生成文件数: {len(files)}")
            for file in files:
                print(f"  - {file.name} ({file.stat().st_size} 字节)")
        else:
            print("❌ research/cases 目录不存在")
            
    except Exception as e:
        print(f"❌ 案例研究失败: {e}")
    
    # 4. 测试WriteContent Action
    print("\n✍️ 测试写作Action:")
    try:
        writer_action = WriteContent(config=config)
        
        writer_result = await writer_action.run(
            topic="人工智能教育应用综合报告",
            summary="基于案例研究，人工智能在教育领域展现出巨大潜力，包括个性化学习、智能教学助手等应用。数据分析显示，AI教育应用能够提升学习效率30%，改善学习体验。",
            project_repo=project_repo
        )
        print(f"✓ 写作完成，结果长度: {len(writer_result) if writer_result else 0}")
        
        # 检查文件是否生成
        reports_dir = Path(workspace_path) / "reports"
        if reports_dir.exists():
            files = list(reports_dir.glob("*.md"))
            print(f"✓ 生成文件数: {len(files)}")
            for file in files:
                print(f"  - {file.name} ({file.stat().st_size} 字节)")
        else:
            print("❌ reports 目录不存在")
            
    except Exception as e:
        print(f"❌ 写作失败: {e}")
    
    # 5. 测试AnalyzeData Action
    print("\n📊 测试数据分析Action:")
    try:
        analyst_action = AnalyzeData(config=config)
        
        # 创建测试数据文件
        test_data = """年份,AI教育应用数量,学习效率提升(%),用户满意度(%)
2020,150,15,75
2021,280,22,82
2022,450,28,88
2023,720,35,92
2024,1200,42,95"""
        
        # 保存测试数据
        uploads_dir = Path(workspace_path) / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        test_file_path = uploads_dir / "ai_education_data.csv"
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_data)
        
        # 创建分析目录
        analysis_dir = Path(workspace_path) / "analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        analyst_result = await analyst_action.run(
            instruction="分析AI教育应用的发展趋势和效果，生成统计图表",
            file_path=test_file_path,
            analysis_path=analysis_dir
        )
        print(f"✓ 数据分析完成，结果: {analyst_result}")
        
        # 检查文件是否生成
        if analysis_dir.exists():
            files = list(analysis_dir.glob("*"))
            print(f"✓ 生成文件数: {len(files)}")
            for file in files:
                if file.is_file():
                    print(f"  - {file.name} ({file.stat().st_size} 字节)")
        else:
            print("❌ analysis 目录不存在")
            
    except Exception as e:
        print(f"❌ 数据分析失败: {e}")
    
    # 6. 最终文件统计
    print("\n📄 最终文件统计:")
    workspace = Path(workspace_path)
    for subdir in ["reports", "analysis", "research", "cases", "drafts"]:
        subdir_path = workspace / subdir
        if subdir_path.exists():
            files = [f for f in subdir_path.rglob("*") if f.is_file()]
            print(f"  {subdir}: {len(files)} 个文件")
            for file in files:
                print(f"    - {file.relative_to(workspace)} ({file.stat().st_size} 字节)")
        else:
            print(f"  {subdir}: 目录不存在")

if __name__ == "__main__":
    asyncio.run(test_direct_actions())