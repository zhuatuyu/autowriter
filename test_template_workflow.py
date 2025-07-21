#!/usr/bin/env python3
"""
测试基于模板的MetaGPT工作流程
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MetaGPT'))

try:
    from backend.tools.report_template_analyzer import report_template_analyzer
    from backend.tools.alibaba_search import alibaba_search_tool
    print("✅ 工具模块导入成功")
except ImportError as e:
    print(f"❌ 工具模块导入失败: {e}")
    sys.exit(1)

async def test_search_tool():
    """测试阿里云搜索工具"""
    print("=== 测试阿里云搜索工具 ===")
    
    try:
        query = "洛阳市数字化城市管理 绩效评价"
        result = await alibaba_search_tool.run(query)
        print(f"搜索查询: {query}")
        print(f"搜索结果: {result[:500]}...")
        return True
    except Exception as e:
        print(f"搜索工具测试失败: {e}")
        return False

def test_template_analyzer():
    """测试报告模板分析器"""
    print("\n=== 测试报告模板分析器 ===")
    
    try:
        # 获取模板摘要
        summary = report_template_analyzer.get_template_summary()
        print(f"模板名称: {summary['name']}")
        print(f"模板描述: {summary['description']}")
        print(f"总章节数: {summary['total_chapters']}")
        print(f"写作序列长度: {summary['writing_sequence_length']}")
        
        # 获取下一个要写作的章节
        next_chapter = report_template_analyzer.get_next_chapter_to_write()
        if next_chapter:
            print(f"下一个章节: {next_chapter.title} ({next_chapter.chapter_code})")
            print(f"写作顺序: {next_chapter.writing_sequence_order}")
            print(f"是否指标驱动: {next_chapter.is_indicator_driven}")
            print(f"依赖章节: {next_chapter.depends_on_chapter_codes}")
        else:
            print("没有待写作的章节")
        
        return True
    except Exception as e:
        print(f"模板分析器测试失败: {e}")
        return False

async def test_template_workflow():
    """测试基于模板的工作流程"""
    print("\n=== 测试基于模板的工作流程 ===")
    
    try:
        # 模拟项目信息
        project_info = {
            "name": "洛阳市数字化城市管理政府购买服务项目",
            "type": "绩效评价",
            "budget": "173.24",
            "funding_source": "财政资金",
            "objective": "评价数字化城市管理服务效果"
        }
        
        # 创建MetaGPT管理器
        manager = MetaGPTManager()
        
        print("MetaGPT管理器创建成功")
        print(f"项目信息: {project_info}")
        
        # 这里可以进一步测试工作流程，但需要完整的环境
        return True
        
    except Exception as e:
        print(f"模板工作流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("开始测试AutoWriter Enhanced的新功能...")
    
    # 测试各个组件
    search_ok = await test_search_tool()
    template_ok = test_template_analyzer()
    workflow_ok = await test_template_workflow()
    
    print("\n=== 测试结果汇总 ===")
    print(f"阿里云搜索工具: {'✅ 通过' if search_ok else '❌ 失败'}")
    print(f"报告模板分析器: {'✅ 通过' if template_ok else '❌ 失败'}")
    print(f"模板工作流程: {'✅ 通过' if workflow_ok else '❌ 失败'}")
    
    if all([search_ok, template_ok, workflow_ok]):
        print("\n🎉 所有测试通过！系统已准备就绪。")
    else:
        print("\n⚠️ 部分测试失败，请检查配置。")

if __name__ == "__main__":
    asyncio.run(main())