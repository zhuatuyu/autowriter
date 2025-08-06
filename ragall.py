#!/usr/bin/env python3
"""
全局知识库管理工具
用法: python ragall.py -f file1.md file2.pdf file3.txt
"""

import asyncio
import argparse
import sys
from pathlib import Path

sys.path.append('.')

from backend.services.global_knowledge import global_knowledge


async def build_global_knowledge_base(file_paths: list):
    """从指定文件构建全局知识库"""
    print("🌍 构建全局知识库...")
    
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
    print("\n🔧 构建全局知识库索引...")
    success = await global_knowledge.build_global_index(force_rebuild=True)
    
    if success:
        # 显示统计信息
        stats = global_knowledge.get_global_stats()
        print(f"\n✅ 全局知识库构建完成!")
        print(f"📊 总文件数: {stats['total_files']}")
        print(f"📁 分类统计: {stats['categories']}")
        return True
    else:
        print("❌ 索引构建失败")
        return False


async def main():
    parser = argparse.ArgumentParser(
        description="全局知识库管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python ragall.py -f 预算法.md 绩效评价标准.pdf 报告模板.txt
  python ragall.py --files doc1.md doc2.pdf doc3.txt
        """
    )
    
    parser.add_argument(
        '-f', '--files', 
        nargs='+', 
        required=True,
        help='要添加到全局知识库的文件列表'
    )
    
    args = parser.parse_args()
    
    success = await build_global_knowledge_base(args.files)
    
    if success:
        print("\n🎉 全局知识库已准备就绪，可以开始使用混合检索功能！")
        sys.exit(0)
    else:
        print("\n💥 构建失败，请检查文件和配置")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())