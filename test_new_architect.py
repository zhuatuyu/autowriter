#!/usr/bin/env python
"""
测试新的Architect设计逻辑
验证是否能基于标准模板和项目特点生成正确的报告结构和动态指标
"""
import asyncio
import os
import tempfile
import shutil
from pathlib import Path

from metagpt.utils.project_repo import ProjectRepo
from backend.roles.product_manager import ProductManager
from backend.roles.architect import Architect


async def test_new_architect():
    """测试新的Architect设计逻辑"""
    
    # 创建临时测试目录
    test_project_dir = Path(tempfile.mkdtemp(prefix="test_new_architect_"))
    print(f"📁 测试项目目录: {test_project_dir}")
    
    try:
        # 设置ProjectRepo
        project_repo = ProjectRepo(test_project_dir)
        
        # 准备测试文档
        uploads_dir = test_project_dir / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        
        test_doc_content = """
# 2024年开封市小麦"一喷三防"实施方案

## 项目背景
为提高小麦产量和品质，减少病虫害损失，实施绿色防控技术推广项目。

## 项目目标
1. 推广绿色防控技术，覆盖面积10万亩
2. 减少化学农药使用量30%
3. 提高小麦产量5-8%
4. 培训农户1000人次

## 预算安排
总预算：500万元
- 技术推广费：300万元
- 培训费：100万元
- 农药补贴：100万元

## 实施内容
1. 生物防控技术推广
2. 农户技术培训
3. 示范基地建设
4. 效果监测评价
"""
        
        test_doc_path = uploads_dir / "绿色农业项目方案.md"
        test_doc_path.write_text(test_doc_content, encoding='utf-8')
        
        # 初始化ProductManager并运行
        print("🔬 初始化ProductManager...")
        product_manager = ProductManager()
        product_manager._project_repo = project_repo
        
        # 手动设置ProductManager的待办事项为第一个action
        product_manager.rc.todo = product_manager.actions[0]  # PrepareDocuments
        
        # 构造用户消息
        user_msg = "根据上传的项目文档，设计一个绿色农业技术推广项目的绩效评价报告结构"
        
        # 执行ProductManager的第一个action (PrepareDocuments)
        print("📋 执行PrepareDocuments...")
        pm_result_1 = await product_manager._act()
        print(f"✅ PrepareDocuments完成: {pm_result_1.content[:100]}...")
        
        # 执行ProductManager的第二个action (ConductComprehensiveResearch)
        product_manager.rc.todo = product_manager.actions[1]  # ConductComprehensiveResearch
        print("🔍 执行ConductComprehensiveResearch...")
        pm_result_2 = await product_manager._act()
        print(f"✅ ConductComprehensiveResearch完成")
        
        # 检查ResearchData
        if hasattr(product_manager, '_last_research_data'):
            research_data = product_manager._last_research_data
            print(f"📊 ResearchData包含 {len(research_data.content_chunks)} 个内容块")
        else:
            print("⚠️  未找到ResearchData")
            research_data = None
        
        # 初始化Architect
        print("🏗️ 初始化Architect...")
        architect = Architect()
        architect._project_repo = project_repo
        architect.rc.todo = architect.actions[0]  # DesignReportStructure
        
        # 模拟ProductManager的消息
        from metagpt.schema import Message
        if research_data:
            pm_message = Message(
                content="ProductManager研究完成",
                instruct_content=research_data,
                role="ProductManager"
            )
        else:
            pm_message = Message(
                content="测试研究简报：绿色农业技术推广项目需要进行绩效评价，重点关注生态效益、经济效益和社会效益。",
                role="ProductManager"
            )
        
        # 将消息添加到Architect的记忆中
        architect.rc.memory.add(pm_message)
        
        # 执行Architect的设计工作
        print("🎯 执行Architect设计...")
        architect_result = await architect._act()
        
        print("✅ Architect设计完成!")
        print(f"📄 输出内容长度: {len(architect_result.content)} 字符")
        
        # 检查生成的文件
        docs_dir = test_project_dir / "docs"
        if docs_dir.exists():
            print("\n📁 生成的文件:")
            for file_path in docs_dir.rglob("*.md"):
                print(f"  - {file_path.name}")
                if file_path.stat().st_size > 0:
                    content = file_path.read_text(encoding='utf-8')
                    print(f"    内容长度: {len(content)} 字符")
                    print(f"    前100字符: {content[:100]}...")
                else:
                    print(f"    ⚠️  文件为空")
        
        # 检查指标文件
        metric_files = list(docs_dir.glob("*metric*.md")) if docs_dir.exists() else []
        if metric_files:
            print("\n📊 指标分析文件:")
            for metric_file in metric_files:
                content = metric_file.read_text(encoding='utf-8')
                print(f"  - {metric_file.name}: {len(content)} 字符")
                
                # 检查是否包含动态生成的内容
                if "决策" in content and "过程" in content and "产出" in content and "效益" in content:
                    print("    ✅ 包含标准四个一级指标")
                else:
                    print("    ⚠️  缺少标准一级指标")
                    
                if "绿色" in content or "农业" in content or "小麦" in content:
                    print("    ✅ 包含项目特色内容")
                else:
                    print("    ⚠️  缺少项目特色内容")
        
        print(f"\n🎉 测试完成！详细结果请查看: {test_project_dir}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理临时目录（可选）
        # shutil.rmtree(test_project_dir)
        pass


if __name__ == "__main__":
    asyncio.run(test_new_architect())