#!/usr/bin/env python3
"""
🧠 全局知识库管理工具 - 支持向量索引和知识图谱
用法: 
  python ragall.py -f file1.md file2.pdf file3.txt                    # 构建向量索引
  python ragall.py -f file1.md file2.pdf file3.txt --kg              # 构建知识图谱
  python ragall.py -f file1.md file2.pdf file3.txt --kg --vector     # 同时构建
"""

import asyncio
import argparse
import sys
from pathlib import Path

sys.path.append('.')

from backend.services.global_knowledge import global_knowledge
from backend.services.knowledge_graph import performance_kg


async def build_global_knowledge_base(file_paths: list, build_vector: bool = True, build_kg: bool = False):
    """🧠 从指定文件构建全局知识库（向量索引 + 知识图谱）"""
    print(f"🌍 构建全局知识库... 向量索引: {build_vector}, 知识图谱: {build_kg}")
    
    # 验证文件存在
    valid_files = []
    for file_path in file_paths:
        path = Path(file_path)
        if path.exists():
            valid_files.append(str(path.absolute()))
            print(f"✅ 找到文件: {file_path}")
        else:
            print(f"❌ 文件不存在: {file_path}")
    
    if not valid_files:
        print("❌ 没有有效文件，退出")
        return False
    
    success_vector = True
    success_kg = True
    
    # 构建向量索引
    if build_vector:
        print("\n📊 构建向量索引知识库...")
        # 添加文件到全局知识库
        for file_path in valid_files:
            file_name = Path(file_path).name
            # 根据文件类型自动分类
            if any(keyword in file_name.lower() for keyword in ['法', '规', '条例', '办法']):
                category = "laws"
            elif any(keyword in file_name.lower() for keyword in ['标准', '规范', '指南']):
                category = "standards"  
            elif any(keyword in file_name.lower() for keyword in ['模板', '样例', '示例']):
                category = "templates"
            else:
                category = "general"
            
            success = global_knowledge.add_global_document(file_path, category)
            if success:
                print(f"📄 已添加: {file_name} -> {category}")
            else:
                print(f"❌ 添加失败: {file_name}")
        
        # 构建索引
        print("\n🔧 构建全局向量索引...")
        success_vector = await global_knowledge.build_global_index(force_rebuild=True)
        
        if success_vector:
            # 显示统计信息
            stats = global_knowledge.get_global_stats()
            print(f"✅ 全局向量索引构建完成!")
            print(f"📊 总文件数: {stats['total_files']}")
            print(f"📁 分类统计: {stats['categories']}")
        else:
            print("❌ 向量索引构建失败")
    
    # 构建知识图谱
    if build_kg:
        print("\n🧠 构建知识图谱...")
        
        # 为知识图谱准备全局存储路径
        global_kg_path = "workspace/vector_storage/global"
        Path(global_kg_path).mkdir(parents=True, exist_ok=True)
        
        # 复制文件到全局知识图谱目录
        for file_path in valid_files:
            file_name = Path(file_path).name
            target_path = Path(global_kg_path) / file_name
            
            try:
                import shutil
                shutil.copy2(file_path, target_path)
                print(f"📄 已复制文件到知识图谱目录: {file_name}")
            except Exception as e:
                print(f"❌ 复制文件失败 {file_name}: {e}")
        
        # 构建知识图谱
        success_kg = await performance_kg.build_knowledge_graph(global_kg_path)
        
        if success_kg:
            print("✅ 全局知识图谱构建完成!")
            
            # 🧠 演示知识图谱的推理能力
            print("\n🧠 知识图谱推理能力演示:")
            test_queries = [
                "绩效评价指标体系应该包含哪些维度？",
                "项目实施过程中常见的风险有哪些？",
                "如何确保项目资金使用的合规性？"
            ]
            
            for query in test_queries:
                print(f"\n🤔 查询: {query}")
                try:
                    result = await performance_kg.query_knowledge_graph(query, mode="hybrid", max_knowledge_sequence=3)
                    print(f"🧠 推理结果: {result[:200]}..." if len(result) > 200 else f"🧠 推理结果: {result}")
                except Exception as e:
                    print(f"❌ 查询失败: {e}")
        else:
            print("❌ 知识图谱构建失败")
    
    return success_vector and success_kg


async def main():
    parser = argparse.ArgumentParser(
        description="🧠 全局知识库管理工具 - 支持向量索引和知识图谱",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 使用示例:
  # 默认构建向量索引
  python ragall.py -f 预算法.md 绩效评价标准.pdf 报告模板.txt
  
  # 构建知识图谱（推荐！）
  python ragall.py -f 预算法.md 绩效评价标准.pdf --kg
  
  # 同时构建向量索引和知识图谱
  python ragall.py -f 预算法.md 绩效评价标准.pdf --kg --vector
  
  # 仅构建知识图谱，不构建向量索引
  python ragall.py -f 预算法.md 绩效评价标准.pdf --kg --no-vector
        """
    )
    
    parser.add_argument(
        '-f', '--files', 
        nargs='+', 
        required=True,
        help='要添加到全局知识库的文件列表'
    )
    
    parser.add_argument(
        '--kg', '--knowledge-graph',
        action='store_true',
        help='🧠 构建知识图谱（推荐！支持推理式查询）'
    )
    
    parser.add_argument(
        '--vector',
        action='store_true',
        help='📊 构建向量索引（传统RAG检索）'
    )
    
    parser.add_argument(
        '--no-vector',
        action='store_true',
        help='🚫 不构建向量索引（仅知识图谱）'
    )
    
    args = parser.parse_args()
    
    # 确定构建选项
    if args.no_vector:
        build_vector = False
        build_kg = args.kg or True  # 如果禁用vector，默认启用kg
    elif args.vector and args.kg:
        build_vector = True
        build_kg = True
    elif args.kg:
        build_vector = False
        build_kg = True
    else:
        # 默认行为：仅构建向量索引
        build_vector = True
        build_kg = False
    
    print(f"🎯 构建配置: 向量索引={build_vector}, 知识图谱={build_kg}")
    
    success = await build_global_knowledge_base(args.files, build_vector=build_vector, build_kg=build_kg)
    
    if success:
        print("\n🎉 全局知识库已准备就绪！")
        if build_vector:
            print("📊 向量检索功能可用")
        if build_kg:
            print("🧠 知识图谱推理功能可用")
        sys.exit(0)
    else:
        print("\n💥 构建失败，请检查文件和配置")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())