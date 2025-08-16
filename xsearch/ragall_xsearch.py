#!/usr/bin/env python3
"""
🧠 xsearch专用全局知识库管理工具 - 支持向量索引和知识图谱
用法: 
  python ragall_xsearch.py -f file1.md file2.pdf file3.txt                    # 构建向量索引
  python ragall_xsearch.py -f file1.md file2.pdf file3.txt --kg              # 构建知识图谱
  python ragall_xsearch.py -f file1.md file2.pdf file3.txt --kg --vector     # 同时构建
"""

import asyncio
import argparse
import sys
import json
import re
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from backend.services.global_knowledge import global_knowledge
    from backend.services.knowledge_graph import performance_kg
    BACKEND_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ backend服务不可用: {e}")
    BACKEND_SERVICES_AVAILABLE = False


def _infer_domain_tags(file_name: str) -> list:
    name = file_name.lower()
    tags = []
    if any(k in name for k in ["法", "规", "条例", "办法", "政策", "法规"]):
        tags.append("政策规范")
    if any(k in name for k in ["标准", "规范", "指南"]):
        tags.append("标准规范")
    if any(k in name for k in ["方法", "模型", "流程", "评价", "方法论"]):
        tags.append("方法论")
    if any(k in name for k in ["模板", "样例", "示例", "范本"]):
        tags.append("模板")
    if not tags:
        tags.append("通用")
    return tags


def _infer_year_and_version(file_name: str) -> tuple[int | None, str]:
    # 年份：匹配4位数字
    year_match = re.search(r"(20\d{2}|19\d{2})", file_name)
    year = int(year_match.group(1)) if year_match else None
    # 版本：中文"第X版"→ vX
    version = "v1"
    mapping = {"第一版": "v1", "第二版": "v2", "第三版": "v3", "第四版": "v4", "第五版": "v5"}
    for zh, v in mapping.items():
        if zh in file_name:
            version = v
            break
    return year, version


def _write_sidecar_meta(target_path: Path, meta: dict) -> None:
    try:
        meta_path = target_path.with_suffix(target_path.suffix + ".meta.json")
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"🧾 元数据已写入: {meta_path}")
    except Exception as e:
        print(f"⚠️ 写入元数据失败 {target_path.name}: {e}")


async def build_global_knowledge_base(file_paths: list, build_vector: bool = True, build_kg: bool = False, chunk_size: int = 512, overlap: int = 50):
    """🧠 从指定文件构建全局知识库（向量索引 + 知识图谱）"""
    if not BACKEND_SERVICES_AVAILABLE:
        print("❌ backend服务不可用，无法构建知识库")
        return False
    
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
            
            # 生成元数据并写入旁车文件（与原文件同目录）
            stem = Path(file_path).stem
            domain_tags = _infer_domain_tags(file_name)
            year, version = _infer_year_and_version(file_name)
            meta = {
                "source": "global",
                "doc_id": stem,
                "domain_tags": domain_tags,
                "year": year,
                "version": version,
                "chunk_size": chunk_size,
                "overlap": overlap,
                "category": category,
            }
            _write_sidecar_meta(Path(file_path), meta)

            success = global_knowledge.add_global_document(file_path, category)
            if success:
                print(f"📄 已添加: {file_name} -> {category}")
            else:
                print(f"❌ 添加失败: {file_name}")
        
        # 构建索引
        print("\n🔧 构建全局向量索引...")
        try:
            # 若全局知识实现支持，传入切分参数；否则回退
            success_vector = await global_knowledge.build_global_index(force_rebuild=True, chunk_size=chunk_size, overlap=overlap)
        except TypeError:
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
                # 同步写入KG侧元数据旁车文件
                stem = Path(file_path).stem
                domain_tags = _infer_domain_tags(file_name)
                year, version = _infer_year_and_version(file_name)
                meta = {
                    "source": "global",
                    "doc_id": stem,
                    "domain_tags": domain_tags,
                    "year": year,
                    "version": version,
                }
                _write_sidecar_meta(target_path, meta)
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
                    result = await performance_kg.query_knowledge_graph(query, mode="keyword", max_knowledge_sequence=3)
                    print(f"🧠 推理结果: {result[:200]}..." if len(result) > 200 else f"🧠 推理结果: {result}")
                except Exception as e:
                    print(f"❌ 查询失败: {e}")
        else:
            print("❌ 知识图谱构建失败")
    
    return success_vector and success_kg


async def main():
    parser = argparse.ArgumentParser(
        description="🧠 xsearch专用全局知识库管理工具 - 支持向量索引和知识图谱",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 使用示例:
  # 默认构建向量索引
  python ragall_xsearch.py -f workspace/vector_storage/*.md
  
  # 构建知识图谱（推荐！）
  python ragall_xsearch.py -f workspace/vector_storage/*.md --kg
  
  # 同时构建向量索引和知识图谱
  python ragall_xsearch.py -f workspace/vector_storage/*.md --kg --vector
  
  # 仅构建知识图谱，不构建向量索引
  python ragall_xsearch.py -f workspace/vector_storage/*.md --kg --no-vector
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
    
    parser.add_argument(
        '--chunk-size', type=int, default=512,
        help='向量索引切分块大小，默认512'
    )
    parser.add_argument(
        '--overlap', type=int, default=50,
        help='向量索引切分重叠，默认50'
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
    
    success = await build_global_knowledge_base(
        args.files,
        build_vector=build_vector,
        build_kg=build_kg,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    
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
