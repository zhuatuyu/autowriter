#!/usr/bin/env python3
"""
📄 文档结构化信息提取工具 - 基于LangExtract + Google API
专门用于从任何文档中提取结构化信息，按照research_brief.md的格式输出

用法: 
  python extradoc_research.py -f 文档.md
  python extradoc_research.py -f 文档1.md 文档2.pdf --output 提取结果.json
  python extradoc_research.py -f 文档.md --visualize  # 生成可视化HTML
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

def setup_google_api_environment():
    """设置Google API环境变量"""
    # 设置Google API key - 使用LangExtract支持的环境变量名称
    os.environ['GOOGLE_API_KEY'] = 'AIzaSyA-gjWRxk6Y4DUQxIuKtF3R_tp8cjF28gs'
    
    # LangExtract可能需要的其他环境变量
    os.environ['GOOGLE_GENERATIVE_AI_API_KEY'] = 'AIzaSyA-gjWRxk6Y4DUQxIuKtF3R_tp8cjF28gs'
    os.environ['GEMINI_API_KEY'] = 'AIzaSyA-gjWRxk6Y4DUQxIuKtF3R_tp8cjF28gs'
    
    print("🔑 已设置Google API配置:")
    print(f"   GOOGLE_API_KEY: {os.environ['GOOGLE_API_KEY'][:8]}...")
    print(f"   GOOGLE_GENERATIVE_AI_API_KEY: {os.environ['GOOGLE_GENERATIVE_AI_API_KEY'][:8]}...")
    print(f"   GEMINI_API_KEY: {os.environ['GEMINI_API_KEY'][:8]}...")
    print("💡 使用Google Gemini模型进行文档信息提取")

def get_research_brief_prompt():
    """获取研究简报提取的专门提示词"""
    return """
    从文档中提取一个完整的摘要，包含以下字段：
    - 项目情况: 项目基本信息（名称、地点、内容、资金来源、参建单位等）
    - 资金情况: 资金详细信息（预算、决算、支付、审计等）
    - 重要事件: 关键时间节点和重要事件
    - 政策引用: 相关法律法规、政策文件、标准规范等
    - 推荐方法: 可推荐的方法、标准、工具、模型、流程等
    - 可借鉴网络案例: 相关网络案例或参考资料
    
    每个文档只提取一个完整摘要。尽可能使用原文内容,所有量化信息均应该保留。
    """

def get_research_brief_examples():
    """获取研究简报提取的示例"""
    return [
        lx.data.ExampleData(
            text="项目名称：李口镇道路建设项目。项目地点：河南省商丘市睢阳区李口镇。建设内容：新建混凝土道路5000平方米。资金来源：财政奖补资金。中标单位：河南建设公司。开工日期：2024年1月。竣工日期：2024年3月。",
            extractions=[
                lx.data.Extraction(
                    extraction_class="document_summary",
                    extraction_text="李口镇道路建设项目摘要",
                    attributes={
                        "项目情况": "项目名称：李口镇道路建设项目。项目地点：河南省商丘市睢阳区李口镇。建设内容：新建混凝土道路5000平方米。资金来源：财政奖补资金。中标单位：河南建设公司。开工日期：2024年1月。竣工日期：2024年3月。",
                        "资金情况": "合同金额：100万元。资金来源：财政奖补资金。",
                        "重要事件": "2024年1月：项目开工。2024年3月：项目竣工。",
                        "政策引用": "财政奖补资金政策",
                        "推荐方法": "采用招投标方式确定施工单位，按合同约定执行项目。",
                        "可借鉴网络案例": "无相关信息"
                    }
                )
            ]
        )
    ]

async def extract_research_brief_from_document(document_path: str, output_file: Path, visualize: bool = False) -> Dict[str, Any]:
    """从单个文档中提取研究简报信息"""
    print(f"📖 正在处理文档: {Path(document_path).name}")
    
    try:
        # 读取文档内容
        with open(document_path, 'r', encoding='utf-8') as f:
            document_text = f.read()
        
        print(f"📄 文档长度: {len(document_text):,} 字符")
        
        # 使用专门的研究简报提取提示词和示例
        prompt = get_research_brief_prompt()
        examples = get_research_brief_examples()
        
        print("🔍 开始提取研究简报信息...")
        
        # 调用LangExtract进行提取
        try:
            result = lx.extract(
                text_or_documents=document_text,
                prompt_description=prompt,
                examples=examples,
                model_id="gemini-1.5-flash",  # 使用兼容的模型
                extraction_passes=1,  # 减少提取次数避免配额限制
                max_workers=3,        # 减少并行处理
                max_char_buffer=2000  # 优化上下文长度
            )
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("⚠️ API配额超限，等待30秒后重试...")
                await asyncio.sleep(30)
                result = lx.extract(
                    text_or_documents=document_text,
                    prompt_description=prompt,
                    examples=examples,
                    model_id="gemini-1.5-flash",
                    extraction_passes=1,
                    max_workers=2,        # 进一步减少并行处理
                    max_char_buffer=2000
                )
            elif "400" in str(e) and "JSON mode" in str(e):
                print("⚠️ 模型不支持JSON模式，尝试使用gemini-1.5-pro...")
                result = lx.extract(
                    text_or_documents=document_text,
                    prompt_description=prompt,
                    examples=examples,
                    model_id="gemini-1.5-pro",
                    extraction_passes=1,
                    max_workers=2,
                    max_char_buffer=2000
                )
            else:
                raise e
        
        print(f"✅ 提取完成！共提取 {len(result.extractions)} 个信息块")
        
        # 保存提取结果
        lx.io.save_annotated_documents([result], output_name=output_file.name, output_dir=output_file.parent)
        
        # 生成可视化HTML（如果请求）
        visualization_file = None
        if visualize:
            try:
                print("🎨 生成交互式可视化HTML...")
                # 使用LangExtract的可视化功能
                html_output = lx.visualize(
                    result,  # 直接传入result对象
                    animation_speed=1.0,
                    show_legend=True,
                    gif_optimized=False
                )
                
                # 保存HTML文件
                html_file = output_file.with_suffix('.visualization.html')
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(str(html_output))  # 转换为字符串
                
                visualization_file = str(html_file)
                print(f"✅ 可视化HTML已生成: {visualization_file}")
                print("🌐 请在浏览器中打开此文件查看交互式可视化")
                
            except Exception as e:
                print(f"⚠️ 可视化生成失败: {e}")
                print("💡 但JSON结果已成功保存")
        
        return {
            "success": True,
            "extractions_count": len(result.extractions) if result.extractions else 0,
            "output_file": str(output_file),
            "visualization_file": visualization_file
        }
        
    except Exception as e:
        print(f"❌ 处理文档失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="📄 文档结构化信息提取工具 - 基于LangExtract + Google API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
示例用法:
  python extradoc_research.py -f 文档.md
  python extradoc_research.py -f 文档1.md 文档2.pdf --output 结果.json
  python extradoc_research.py -f 文档.md --visualize
        """)
    )
    
    parser.add_argument(
        '-f', '--files', 
        nargs='+', 
        required=True,
        help='要处理的文档文件路径（支持多个文件）'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='输出文件名（不包含扩展名）'
    )
    
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='生成交互式可视化HTML文件'
    )
    
    args = parser.parse_args()
    
    # 检查LangExtract是否可用
    if not LANGEXTRACT_AVAILABLE:
        print("❌ LangExtract未安装，请运行: pip install langextract")
        sys.exit(1)
    
    # 设置Google API环境
    setup_google_api_environment()
    
    # 处理文档
    results = []
    total_success = 0
    
    for i, document_path in enumerate(args.files):
        if not Path(document_path).exists():
            print(f"❌ 文档不存在: {document_path}")
            continue
        
        # 确定输出文件名
        if args.output:
            if len(args.files) == 1:
                output_name = args.output
            else:
                output_name = f"{args.output}_{i+1}"
        else:
            output_name = Path(document_path).stem + ".research_brief"
        
        output_file = Path("global-docs") / f"{output_name}.json"
        output_file.parent.mkdir(exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"📄 处理文档 {i+1}/{len(args.files)}: {Path(document_path).name}")
        print(f"{'='*60}")
        
        result = await extract_research_brief_from_document(
            document_path, 
            output_file, 
            args.visualize
        )
        
        results.append({
            "document": document_path,
            "result": result
        })
        
        if result["success"]:
            total_success += 1
            print(f"✅ 文档 {i+1} 处理成功")
        else:
            print(f"❌ 文档 {i+1} 处理失败")
    
    # 输出总结
    print(f"\n{'='*60}")
    print("📊 处理结果摘要")
    print(f"{'='*60}")
    
    for i, item in enumerate(results):
        doc_name = Path(item["document"]).name
        if item["result"]["success"]:
            print(f"✅ 文档 {i+1}: 成功提取 {item['result']['extractions_count']} 个信息块")
            print(f"   输出文件: {item['result']['output_file']}")
            if item['result']['visualization_file']:
                print(f"   可视化文件: {item['result']['visualization_file']}")
        else:
            print(f"❌ 文档 {i+1}: 处理失败 - {item['result']['error']}")
    
    print(f"\n🎉 处理完成！成功: {total_success}/{len(args.files)}")
    
    if total_success > 0:
        print("\n💡 提示:")
        print("   - 提取的研究简报信息已保存为JSON格式")
        if args.visualize:
            print("   - 可视化HTML文件已生成，可在浏览器中查看")
        print("   - 可以使用提取的结构化信息进行进一步分析或生成报告")

if __name__ == "__main__":
    asyncio.run(main())
