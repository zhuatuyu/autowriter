#!/usr/bin/env python3
"""
📄 文档结构化信息提取工具 - 基于LangExtract
专门用于从绩效评价报告中提取指标体系信息

用法: 
  python extradoc.py -f ZYCASE2024省级职业技能竞赛经费项目绩效评价报告.md
  python extradoc.py -f 文档1.md 文档2.pdf --output 提取结果.json
  python extradoc.py -f 文档.md --visualize  # 生成可视化HTML
"""

import asyncio
import argparse
import sys
import json
import textwrap
import os
import yaml
from pathlib import Path
from typing import List, Dict, Any

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False
    print("❌ LangExtract未安装，请运行: pip install langextract")


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    config_path = Path('config/config2.yaml')
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


def setup_ollama_environment():
    """设置Ollama环境变量"""
    # 设置Ollama相关环境变量
    os.environ['OLLAMA_HOST'] = 'http://localhost:11434'
    os.environ['OLLAMA_MODEL'] = 'gpt-oss:20b'
    
    print("🔧 已设置Ollama环境变量:")
    print(f"   OLLAMA_HOST: {os.environ['OLLAMA_HOST']}")
    print(f"   OLLAMA_MODEL: {os.environ['OLLAMA_MODEL']}")
    
    # 检查Ollama服务是否运行
    try:
        import requests
        response = requests.get(f"{os.environ['OLLAMA_HOST']}/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama服务运行正常")
            # 显示可用模型
            models = response.json().get('models', [])
            if models:
                print("📋 可用模型:")
                for model in models:
                    print(f"   - {model.get('name', 'Unknown')}")
        else:
            print("⚠️ Ollama服务响应异常")
    except Exception as e:
        print(f"⚠️ 无法连接到Ollama服务: {e}")
        print("💡 请确保Ollama服务正在运行: ollama serve")


def create_performance_metrics_extraction_prompt() -> str:
    """创建绩效指标提取的提示词"""
    return textwrap.dedent("""
    从绩效评价报告中提取完整的指标体系信息，包括以下内容：
    
    1. 绩效指标名称和定义
    2. 指标所属维度（决策、过程、产出、效益）
    3. 指标权重和分值
    4. 评价标准和计分方法
    5. 实际得分和评价意见
    6. 指标完成情况
    
    请严格按照以下JSON格式输出，确保每个指标包含完整信息：
    {
      "metric_id": "唯一标识符",
      "level1_name": "一级维度名称",
      "level2_name": "二级分类名称", 
      "name": "指标名称",
      "weight": "权重分值",
      "evaluation_type": "评价类型",
      "evaluation_points": "评价要点",
      "opinion": "评价意见",
      "score": "实际得分"
    }
    
    使用精确文本，不要改写或重叠实体。如果文档中没有某个字段的信息，请标注为null。
    """)


def create_performance_metrics_examples() -> List[lx.data.ExampleData]:
    """创建绩效指标提取的示例数据"""
    return [
        lx.data.ExampleData(
            text="决策指标：项目立项符合国家及地方政策要求，权重10分，评价要点：①项目立项文件引用相关政策；②项目目标与管理办法一致；③项目预算编制符合预算法原则。满足全部三项条件，得满分；每缺少一项扣3分，扣完为止。",
            extractions=[
                lx.data.Extraction(
                    extraction_class="metric",
                    extraction_text="项目立项符合国家及地方政策要求",
                    attributes={
                        "level1_name": "决策",
                        "level2_name": "政策符合性", 
                        "weight": "10",
                        "evaluation_type": "condition",
                        "evaluation_points": "①项目立项文件引用相关政策；②项目目标与管理办法一致；③项目预算编制符合预算法原则。满足全部三项条件，得满分；每缺少一项扣3分，扣完为止。"
                    }
                )
            ]
        ),
        lx.data.ExampleData(
            text="过程指标：财政奖补资金专款专用、使用合规，权重9分，评价要点：①设立专项资金账户或实行专账核算；②资金支出与项目内容直接对应；③无截留、挪用、套取资金行为。满足全部三项得满分；发现一项违规，得分=0。",
            extractions=[
                lx.data.Extraction(
                    extraction_class="metric",
                    extraction_text="财政奖补资金专款专用、使用合规",
                    attributes={
                        "level1_name": "过程",
                        "level2_name": "资金管理",
                        "weight": "9", 
                        "evaluation_type": "condition",
                        "evaluation_points": "①设立专项资金账户或实行专账核算；②资金支出与项目内容直接对应；③无截留、挪用、套取资金行为。满足全部三项得满分；发现一项违规，得分=0。"
                    }
                )
            ]
        )
    ]


async def extract_performance_metrics_from_document(
    document_path: str,
    output_path: str = None,
    visualize: bool = False
) -> Dict[str, Any]:
    """从文档中提取绩效指标体系"""
    
    if not LANGEXTRACT_AVAILABLE:
        return {"error": "LangExtract未安装"}
    
    try:
        print(f"📄 开始处理文档: {document_path}")
        
        # 读取文档内容
        with open(document_path, 'r', encoding='utf-8') as f:
            document_content = f.read()
        
        print(f"📊 文档长度: {len(document_content)} 字符")
        
        # 创建提取提示词和示例
        prompt = create_performance_metrics_extraction_prompt()
        examples = create_performance_metrics_examples()
        
        print("🧠 开始使用LangExtract提取绩效指标...")
        print("🔧 使用本地Ollama模型: gpt-oss:20b")
        
        # 使用本地Ollama模型
        try:
            result = lx.extract(
                text_or_documents=document_content,
                prompt_description=prompt,
                examples=examples,
                model_id="gpt-oss:20b",  # 直接使用Ollama模型名称
            )
            print("✅ 提取完成！")
        except Exception as e:
            # 如果直接使用模型名称失败，尝试使用Ollama的完整配置
            print(f"⚠️ 直接使用模型名称失败，尝试Ollama配置: {e}")
            try:
                result = lx.extract(
                    text_or_documents=document_content,
                    prompt_description=prompt,
                    examples=examples,
                    model_id="ollama/gpt-oss:20b",  # 使用ollama/前缀
                )
                print("✅ 使用Ollama配置提取完成！")
            except Exception as e2:
                print(f"⚠️ Ollama配置也失败，尝试其他方式: {e2}")
                # 最后尝试使用环境变量中的模型
                result = lx.extract(
                    text_or_documents=document_content,
                    prompt_description=prompt,
                    examples=examples,
                    model_id=os.environ.get('OLLAMA_MODEL', 'gpt-oss:20b'),
                )
                print("✅ 使用环境变量模型提取完成！")
        
        # 保存结果到JSON文件
        if output_path:
            output_file = Path(output_path)
        else:
            output_file = Path(document_path).with_suffix('.extracted_metrics.json')
        
        # 保存提取结果
        lx.io.save_annotated_documents([result], output_name=output_file.name, output_dir=output_file.parent)
        print(f"💾 提取结果已保存到: {output_file}")
        
        # 生成可视化HTML（如果需要）
        html_file = None
        if visualize:
            try:
                html_content = lx.visualize(str(output_file))
                html_file = output_file.with_suffix('.html')
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"🌐 可视化HTML已生成: {html_file}")
            except Exception as e:
                print(f"⚠️ 生成可视化HTML失败: {e}")
        
        # 返回提取结果摘要
        extraction_summary = {
            "document": document_path,
            "extractions_count": len(result.extractions) if hasattr(result, 'extractions') else 0,
            "output_file": str(output_file),
            "visualization_file": str(html_file) if html_file else None,
            "extractions": []
        }
        
        # 添加提取的指标信息
        if hasattr(result, 'extractions'):
            for extraction in result.extractions:
                extraction_summary["extractions"].append({
                    "class": extraction.extraction_class,
                    "text": extraction.extraction_text,
                    "attributes": extraction.attributes
                })
        
        return extraction_summary
        
    except Exception as e:
        error_msg = f"❌ 提取失败: {str(e)}"
        print(error_msg)
        return {"error": error_msg}


async def batch_extract_documents(
    document_paths: List[str],
    output_dir: str = None,
    visualize: bool = False
) -> List[Dict[str, Any]]:
    """批量处理多个文档"""
    
    results = []
    
    for doc_path in document_paths:
        print(f"\n{'='*60}")
        print(f"📄 处理文档: {doc_path}")
        print(f"{'='*60}")
        
        # 确定输出路径
        if output_dir:
            output_path = Path(output_dir) / f"{Path(doc_path).stem}_extracted.json"
        else:
            output_path = None
        
        # 提取指标
        result = await extract_performance_metrics_from_document(
            doc_path, 
            output_path, 
            visualize
        )
        
        results.append(result)
        
        if "error" not in result:
            print(f"✅ 文档 {doc_path} 处理完成")
        else:
            print(f"❌ 文档 {doc_path} 处理失败")
    
    return results


async def main():
    parser = argparse.ArgumentParser(
        description="📄 文档结构化信息提取工具 - 基于LangExtract + 本地Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 使用示例:
  # 提取单个文档的绩效指标
  python extradoc.py -f ZYCASE2024省级职业技能竞赛经费项目绩效评价报告.md
  
  # 指定输出文件
  python extradoc.py -f 文档.md --output 提取结果.json
  
  # 生成可视化HTML
  python extradoc.py -f 文档.md --visualize
  
  # 批量处理多个文档
  python extradoc.py -f 文档1.md 文档2.pdf 文档3.txt
  
  # 批量处理并指定输出目录
  python extradoc.py -f 文档1.md 文档2.pdf --output-dir ./提取结果 --visualize
  
💡 前置条件:
  - 确保Ollama服务正在运行: ollama serve
  - 确保已拉取模型: ollama pull gpt-oss:20b
        """
    )
    
    parser.add_argument(
        '-f', '--files', 
        nargs='+', 
        required=True,
        help='要提取信息的文档文件列表'
    )
    
    parser.add_argument(
        '--output', 
        type=str,
        help='输出文件路径（单个文档时使用）'
    )
    
    parser.add_argument(
        '--output-dir', 
        type=str,
        help='输出目录路径（批量处理时使用）'
    )
    
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='生成交互式可视化HTML文件'
    )
    
    args = parser.parse_args()
    
    # 检查LangExtract是否可用
    if not LANGEXTRACT_AVAILABLE:
        print("❌ LangExtract未安装，请先运行: pip install langextract")
        sys.exit(1)
    
    # 设置Ollama环境变量
    print("🔧 设置Ollama环境变量...")
    setup_ollama_environment()
    
    # 验证文件存在
    valid_files = []
    for file_path in args.files:
        if Path(file_path).exists():
            valid_files.append(file_path)
            print(f"✅ 找到文件: {file_path}")
        else:
            print(f"❌ 文件不存在: {file_path}")
    
    if not valid_files:
        print("❌ 没有有效文件，退出")
        sys.exit(1)
    
    print(f"\n🎯 开始处理 {len(valid_files)} 个文档...")
    
    # 处理文档
    if len(valid_files) == 1:
        # 单个文档
        result = await extract_performance_metrics_from_document(
            valid_files[0],
            args.output,
            args.visualize
        )
        results = [result]
    else:
        # 批量处理
        results = await batch_extract_documents(
            valid_files,
            args.output_dir,
            args.visualize
        )
    
    # 输出处理结果摘要
    print(f"\n{'='*60}")
    print("📊 处理结果摘要")
    print(f"{'='*60}")
    
    success_count = 0
    for i, result in enumerate(results):
        if "error" not in result:
            success_count += 1
            print(f"✅ 文档 {i+1}: 成功提取 {result.get('extractions_count', 0)} 个指标")
            print(f"   输出文件: {result.get('output_file', 'N/A')}")
            if args.visualize:
                print(f"   可视化文件: {result.get('visualization_file', 'N/A')}")
        else:
            print(f"❌ 文档 {i+1}: {result.get('error', '未知错误')}")
    
    print(f"\n🎉 处理完成！成功: {success_count}/{len(results)}")
    
    if success_count > 0:
        print("\n💡 提示:")
        print("   - 提取的指标已保存为JSON格式")
        if args.visualize:
            print("   - 可视化HTML文件已生成，可在浏览器中查看")
        print("   - 可以使用提取的指标数据构建知识图谱或进行进一步分析")
    
    sys.exit(0 if success_count > 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
