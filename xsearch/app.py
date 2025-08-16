#!/usr/bin/env python3
"""
🧠 智能分析系统 - 端到端验证
基于向量检索 + LangExtract + 知识图谱 + LLM的完整分析流程
"""

import asyncio
import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from xsearch.intelligent_analyzer import IntelligentAnalyzer
from xsearch.config_loader import ConfigLoader


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="🧠 智能分析系统 - 端到端验证",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-f', '--config',
        required=True,
        help='项目配置文件路径'
    )
    
    parser.add_argument(
        '--query',
        default="分析项目质量控制体系的有效性，找出薄弱环节",
        help='自定义查询语句'
    )
    
    parser.add_argument(
        '--output',
        help='输出文件名（不包含扩展名）'
    )
    
    args = parser.parse_args()
    
    # 检查配置文件
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)
    
    print(f"🔧 加载配置文件: {config_path}")
    
    # 加载配置
    config_loader = ConfigLoader(config_path)
    project_config = config_loader.load_project_config()
    
    print(f"✅ 项目配置加载完成: {project_config['project_name']}")
    
    # 创建智能分析器
    analyzer = IntelligentAnalyzer(project_config)
    
    # 执行智能分析
    print(f"\n🧠 开始智能分析...")
    print(f"查询: {args.query}")
    
    try:
        result = await analyzer.analyze_query(args.query)
        
        # 确定输出文件名
        if args.output:
            output_name = args.output
        else:
            output_name = f"intelligent_analysis_{project_config['project_id']}"
        
        # 保存结果
        output_file = Path("output") / f"{output_name}.json"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 分析完成！结果已保存到: {output_file}")
        
        # 打印关键信息
        print(f"\n📊 分析结果摘要:")
        print(f"   - 查询意图: {result['intent_analysis']['core_topic']}")
        
        # 安全地访问search_strategy字段
        search_strategy = result.get('search_strategy', {})
        if 'search_keywords' in search_strategy:
            print(f"   - 检索策略: {len(search_strategy['search_keywords'])} 个关键词")
        if 'extraction_fields' in search_strategy:
            print(f"   - 提取字段: {len(search_strategy['extraction_fields'])} 个字段")
        if 'evaluation_structure' in search_strategy:
            print(f"   - 评价结构: {len(search_strategy['evaluation_structure'])} 个要点")
        
        print(f"   - 数据源: 项目{result['data_sources']['project_docs']}条，全局{result['data_sources']['global_methods']}条")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
