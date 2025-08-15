#!/usr/bin/env python3
"""
📄 文档结构化信息提取工具 - 基于LangExtract + Google API
专门用于从绩效评价报告中提取指标体系信息，按照特定JSON结构输出

用法: 
  python extradoc_useapi.py -f ZYCASE2024省级职业技能竞赛经费项目绩效评价报告.md
  python extradoc_useapi.py -f 文档1.md 文档2.pdf --output 提取结果.json
  python extradoc_useapi.py -f 文档.md --visualize  # 生成可视化HTML
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


def get_performance_metrics_prompt():
    """获取绩效指标提取的专门提示词"""
    return """
    请从绩效评价报告中提取绩效指标信息，严格按照以下层级结构：

    **层级结构说明**：
    - 一级指标：决策、过程、产出、效益（4个固定分类）
    - 二级指标：每个一级指标下的主要评价维度（名称不固定）
    - 三级指标：具体的评价指标（名称不固定，但这是我们要提取的目标）

    **提取要求**：
    1. 只提取三级指标，不要提取一级和二级分类标题
    2. 每个三级指标必须包含完整的评价信息
    3. 根据文档内容自动识别二级指标名称
    4. 权重、得分、得分率等信息必须准确

    **输出格式**：严格按照指定的JSON结构输出，包含所有必需字段
    """

def get_performance_metrics_examples():
    """获取绩效指标提取的示例"""
    return [
        lx.data.ExampleData(
            text='A101立项依据充分性：根据人力资源和社会保障部关于印发《"技能中国行动"实施方案的通知》（人社部发〔2021〕48号），人力资源和社会保障部、教育部、发展改革委、财政部关于印发《"十四五"职业技能培训规划的通知》（人社部发〔2021〕102号），中共中央办公厅、国务院办公厅印发《关于加强新时代高技能人才队伍建设的意见》（中办发〔2022〕58号），中共河南省委办公厅、河南省人民政府办公厅关于印发《高质量推进"人人持证、技能河南"建设工作方案》（豫办〔2021〕29号），河南省全民技能振兴工程领导小组关于印发《河南省职业技能大赛组织工作方案》的通知（豫技领〔2021〕2号），河南省人民政府办公厅关于印发《河南省职业技能竞赛管理办法的通知》（豫政办〔2024〕42号），项目立项符合国家和省技能人才工作法律法规和相关政策；项目立项与省人社厅部门职责范围相符，属于部门履职所需；项目属于公共财政支持范围，符合中央、地方事权支出责任划分原则；该指标得2分。',
            extractions=[
                lx.data.Extraction(
                    extraction_class="metric",
                    extraction_text="A101立项依据充分性",
                    attributes={
                        "metric_id": "A101",
                        "level1_name": "决策",
                        "level2_name": "项目立项",
                        "name": "立项依据充分性",
                        "weight": "2.00",
                        "evaluation_type": "condition",
                        "evaluation_points": "项目立项符合国家和省技能人才工作法律法规和相关政策；项目立项与省人社厅部门职责范围相符，属于部门履职所需；项目属于公共财政支持范围，符合中央、地方事权支出责任划分原则",
                        "opinion": "项目立项依据充分，符合政策要求",
                        "score": "2.00"
                    }
                )
            ]
        ),
        lx.data.ExampleData(
            text="C101一次性竞赛补贴项目指标完成数量：2021年计划安排补贴26个赛事146个赛项，实际补贴131个赛项，偏差率为10.27%；2022年计划安排补贴29个赛事101个赛项，实际补贴65个赛项，偏差率为35.64%；2023年计划安排补贴24个赛事168个赛项，实际补贴完成161个赛项，偏差率为4.17%；2024年计划安排补贴31个赛事174个赛项，实际补贴168个赛项，偏差率为3.45%；该指标得6.94分。",
            extractions=[
                lx.data.Extraction(
                    extraction_class="metric",
                    extraction_text="C101一次性竞赛补贴项目指标完成数量",
                    attributes={
                        "metric_id": "C101",
                        "level1_name": "产出",
                        "level2_name": "产出数量",
                        "name": "一次性竞赛补贴项目指标完成数量",
                        "weight": "8.00",
                        "evaluation_type": "formula",
                        "evaluation_points": "2021年偏差率10.27%，2022年偏差率35.64%，2023年偏差率4.17%，2024年偏差率3.45%",
                        "opinion": "各年度完成情况良好，偏差率控制在合理范围内",
                        "score": "6.94"
                    }
                )
            ]
        )
    ]

async def extract_performance_metrics_from_document(document_path: str, output_file: Path, visualize: bool = False) -> Dict[str, Any]:
    """从单个文档中提取绩效指标"""
    print(f"📖 正在处理文档: {Path(document_path).name}")
    
    try:
        # 读取文档内容
        with open(document_path, 'r', encoding='utf-8') as f:
            document_text = f.read()
        
        print(f"📄 文档长度: {len(document_text):,} 字符")
        
        # 使用专门的绩效指标提取提示词和示例
        prompt = get_performance_metrics_prompt()
        examples = get_performance_metrics_examples()
        
        print("🔍 开始提取绩效指标...")
        
        # 调用LangExtract进行提取
        result = lx.extract(
            text_or_documents=document_text,
            prompt_description=prompt,
            examples=examples,
            model_id="gemini-2.0-flash-exp",
            extraction_passes=2,  # 使用多次提取提高准确性
            max_workers=10,       # 并行处理
            max_char_buffer=2000  # 优化上下文长度
        )
        
        print(f"✅ 提取完成！共提取 {len(result.extractions)} 个指标")
        
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
  python extradoc_useapi.py -f 文档.md
  python extradoc_useapi.py -f 文档1.md 文档2.pdf --output 结果.json
  python extradoc_useapi.py -f 文档.md --visualize
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
            output_name = Path(document_path).stem + ".extracted_metrics"
        
        output_file = Path("global-docs") / f"{output_name}.json"
        output_file.parent.mkdir(exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"📄 处理文档 {i+1}/{len(args.files)}: {Path(document_path).name}")
        print(f"{'='*60}")
        
        result = await extract_performance_metrics_from_document(
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
            print(f"✅ 文档 {i+1}: 成功提取 {item['result']['extractions_count']} 个指标")
            print(f"   输出文件: {item['result']['output_file']}")
            if item['result']['visualization_file']:
                print(f"   可视化文件: {item['result']['visualization_file']}")
        else:
            print(f"❌ 文档 {i+1}: 处理失败 - {item['result']['error']}")
    
    print(f"\n🎉 处理完成！成功: {total_success}/{len(args.files)}")
    
    if total_success > 0:
        print("\n💡 提示:")
        print("   - 提取的指标已保存为JSON格式")
        if args.visualize:
            print("   - 可视化HTML文件已生成，可在浏览器中查看")
        print("   - 可以使用提取的指标数据构建知识图谱或进行进一步分析")

if __name__ == "__main__":
    asyncio.run(main())
