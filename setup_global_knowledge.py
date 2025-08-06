#!/usr/bin/env python3
"""
简化版全局知识库设置工具
专门用于添加国家级文档（a1.md, a2.md）到全局知识库并测试
"""

import asyncio
import sys
import shutil
from pathlib import Path

# 确保能导入我们的模块
sys.path.append('.')

from backend.services.global_knowledge import global_knowledge
from backend.services.hybrid_search import hybrid_search


async def setup_national_documents():
    """设置国家级文档到全局知识库"""
    
    print("🇨🇳 开始设置国家级知识文档...")
    
    # 确保全局存储目录存在
    global_storage = Path("workspace/vector_storage/global")
    laws_dir = global_storage / "laws"
    laws_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制a1.md和a2.md到全局知识库
    source_files = ["a1.md", "a2.md"]
    copied_files = []
    
    for source_file in source_files:
        source_path = Path(source_file)
        if source_path.exists():
            target_path = laws_dir / source_path.name
            shutil.copy2(source_path, target_path)
            copied_files.append(str(target_path))
            print(f"✅ 已复制: {source_file} → {target_path}")
        else:
            print(f"⚠️  文件不存在: {source_file}")
    
    if not copied_files:
        print("❌ 没有找到要添加的文件!")
        return False
    
    print(f"\n📊 全局知识库统计:")
    stats = global_knowledge.get_global_stats()
    print(f"  总文件数: {stats['total_files']}")
    print(f"  存储路径: {stats['storage_path']}")
    
    # 强制重新构建索引
    print("\n🔧 开始构建全局知识库索引...")
    success = await global_knowledge.build_global_index(force_rebuild=True)
    
    if success:
        print("✅ 全局知识库索引构建成功!")
        return True
    else:
        print("❌ 全局知识库索引构建失败!")
        return False


async def test_global_search():
    """测试全局知识库搜索功能"""
    
    print("\n🔍 测试全局知识库搜索功能...")
    
    test_queries = [
        "预算法",
        "绩效评价",
        "财政管理",
        "项目评价指标"
    ]
    
    for query in test_queries:
        print(f"\n🔍 搜索: {query}")
        results = await global_knowledge.search_global(query, top_k=2)
        
        if results:
            print(f"✅ 找到 {len(results)} 条结果:")
            for i, result in enumerate(results, 1):
                # 显示前100个字符
                preview = result[:100].replace('\n', ' ').strip()
                print(f"  {i}. {preview}...")
        else:
            print("❌ 未找到相关结果")


async def test_hybrid_search():
    """测试混合检索功能"""
    
    print("\n🔍 测试混合检索功能...")
    
    # 创建一个测试项目目录
    test_project_dir = Path("workspace/test_project")
    test_vector_storage = test_project_dir / "vector_storage"
    test_vector_storage.mkdir(parents=True, exist_ok=True)
    
    # 创建测试项目文档
    test_doc = test_vector_storage / "项目文档.md"
    test_doc.write_text("""
# 测试项目文档

## 项目概况
这是一个测试项目，用于验证混合检索功能。

## 预算信息
项目总预算：100万元
资金来源：财政拨款

## 实施计划
按照国家相关法律法规执行，严格遵守预算法要求。
""", encoding='utf-8')
    
    print(f"📄 创建测试项目文档: {test_doc}")
    
    # 测试混合检索
    test_query = "预算法要求"
    print(f"\n🔍 混合检索测试: {test_query}")
    
    results = await hybrid_search.hybrid_search(
        query=test_query,
        project_vector_storage_path=str(test_vector_storage),
        enable_global=True,
        global_top_k=2,
        project_top_k=2
    )
    
    if results:
        print(f"✅ 混合检索成功，找到 {len(results)} 条结果:")
        for i, result in enumerate(results, 1):
            preview = result[:150].replace('\n', ' ').strip()
            print(f"  {i}. {preview}...")
    else:
        print("❌ 混合检索未找到结果")
    
    # 清理测试目录
    shutil.rmtree(test_project_dir, ignore_errors=True)
    print("🗑️  已清理测试目录")


def show_final_stats():
    """显示最终统计信息"""
    
    print("\n📊 最终全局知识库统计:")
    stats = global_knowledge.get_global_stats()
    
    print(f"  存储路径: {stats['storage_path']}")
    print(f"  索引路径: {stats['index_path']}")
    print(f"  索引状态: {'✅ 已构建' if stats['index_exists'] else '❌ 未构建'}")
    print(f"  总文件数: {stats['total_files']}")
    
    if stats['categories']:
        print("\n📁 文档分类统计:")
        for category, count in stats['categories'].items():
            print(f"  {category}: {count} 个文件")


async def main():
    """主函数"""
    
    print("=" * 60)
    print("🏛️  国家级知识库设置工具")
    print("=" * 60)
    
    try:
        # 1. 设置国家级文档
        success = await setup_national_documents()
        if not success:
            print("❌ 设置失败，退出程序")
            return
        
        # 2. 测试全局搜索
        await test_global_search()
        
        # 3. 测试混合检索
        await test_hybrid_search()
        
        # 4. 显示最终统计
        show_final_stats()
        
        print("\n" + "=" * 60)
        print("🎉 全局知识库设置完成!")
        print("💡 现在所有智能体都可以同时使用:")
        print("   - 🌍 全局知识库 (国家法规、标准)")
        print("   - 📁 项目知识库 (项目特定文档)")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())