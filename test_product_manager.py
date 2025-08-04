#!/usr/bin/env python
"""
产品经理功能测试
测试搜索引擎配置和产品经理的基本功能
"""
import sys
import os
import asyncio
from pathlib import Path

# 添加MetaGPT路径到系统路径
current_dir = Path(__file__).parent
metagpt_path = current_dir / "example" / "MetaGPT_bak"
sys.path.insert(0, str(metagpt_path))

# 现在可以导入MetaGPT相关模块
from metagpt.config2 import config
from metagpt.tools.search_engine import SearchEngine
from metagpt.actions.search_enhanced_qa import SearchEnhancedQA
from metagpt.actions.research import CollectLinks
from metagpt.logs import logger
from backend.roles.product_manager import ProductManager
from metagpt.schema import Message


async def test_search_engine_config():
    """测试搜索引擎配置"""
    print("=" * 50)
    print("🔍 测试搜索引擎配置")
    print("=" * 50)
    
    try:
        # 1. 检查配置
        print(f"搜索引擎类型: {config.search.api_type}")
        print(f"API Key: {config.search.api_key[:10]}..." if config.search.api_key else "未配置")
        print(f"Endpoint: {getattr(config.search, 'endpoint', '未配置')}")
        print(f"Workspace: {getattr(config.search, 'workspace', '未配置')}")
        print(f"Service ID: {getattr(config.search, 'service_id', '未配置')}")
        
        # 2. 创建搜索引擎实例
        search_engine = SearchEngine.from_search_config(config.search)
        print(f"✅ 搜索引擎实例创建成功: {search_engine.engine}")
        print(f"Run func: {search_engine.run_func is not None}")
        
        return search_engine
        
    except Exception as e:
        print(f"❌ 搜索引擎配置测试失败: {e}")
        return None


async def test_search_engine_basic():
    """测试搜索引擎基本功能"""
    print("\n" + "=" * 50)
    print("🔍 测试搜索引擎基本功能")
    print("=" * 50)
    
    try:
        search_engine = SearchEngine.from_search_config(config.search)
        
        # 简单搜索测试
        test_query = "小麦一喷三防项目"
        print(f"测试查询: {test_query}")
        
        results = await search_engine.run(test_query, max_results=3, as_string=False)
        print(f"✅ 搜索成功，返回 {len(results)} 个结果")
        
        for i, result in enumerate(results[:2], 1):  # 只显示前2个结果
            print(f"\n结果 {i}:")
            print(f"  标题: {result.get('title', 'N/A')}")
            print(f"  链接: {result.get('link', 'N/A')}")
            print(f"  摘要: {result.get('snippet', 'N/A')[:100]}...")
            
        return True
        
    except Exception as e:
        print(f"❌ 搜索引擎基本功能测试失败: {e}")
        return False


async def test_collect_links():
    """测试CollectLinks功能"""
    print("\n" + "=" * 50)
    print("🔗 测试CollectLinks功能")
    print("=" * 50)
    
    try:
        search_engine = SearchEngine.from_search_config(config.search)
        collect_links = CollectLinks(search_engine=search_engine)
        
        test_query = "小麦一喷三防项目财政绩效评价"
        print(f"测试查询: {test_query}")
        
        # 测试搜索和排序URL
        urls = await collect_links._search_and_rank_urls(test_query, max_results=3)
        print(f"✅ CollectLinks成功，返回 {len(urls)} 个URL")
        
        for i, url in enumerate(urls[:2], 1):
            print(f"  URL {i}: {url}")
            
        return True
        
    except Exception as e:
        print(f"❌ CollectLinks测试失败: {e}")
        return False


async def test_search_enhanced_qa():
    """测试SearchEnhancedQA功能"""
    print("\n" + "=" * 50)
    print("🤖 测试SearchEnhancedQA功能")
    print("=" * 50)
    
    try:
        search_engine = SearchEngine.from_search_config(config.search)
        collect_links = CollectLinks(search_engine=search_engine)
        search_qa = SearchEnhancedQA(collect_links_action=collect_links)
        
        test_query = "小麦一喷三防项目的主要内容是什么？"
        print(f"测试查询: {test_query}")
        
        # 运行搜索增强问答
        answer = await search_qa.run(test_query)
        print(f"✅ SearchEnhancedQA成功")
        print(f"回答长度: {len(answer)} 字符")
        print(f"回答预览: {answer[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ SearchEnhancedQA测试失败: {e}")
        return False


async def test_product_manager():
    """测试产品经理完整功能"""
    print("\n" + "=" * 50)
    print("👨‍💼 测试产品经理完整功能")
    print("=" * 50)
    
    try:
        # 创建产品经理实例
        pm = ProductManager()
        print(f"✅ 产品经理实例创建成功: {pm.name}")
        print(f"Actions数量: {len(pm.actions)}")
        
        # 模拟用户需求消息 - 修复引号问题
        user_message = Message(
            content='可以检索网络案例来辅助参考撰写 《祥符区2024年小麦"一喷三防"项目财政重点绩效评价报告》',
            role="user"
        )
        
        # 将消息添加到记忆中
        pm.rc.memory.add(user_message)
        
        # 执行思考
        await pm._think()
        print(f"✅ 产品经理思考完成")
        print(f"Todo action: {type(pm.rc.todo).__name__ if pm.rc.todo else 'None'}")
        
        # 如果有todo，尝试执行一步
        if pm.rc.todo:
            print("🚀 开始执行研究任务...")
            # 这里我们不完整执行，只是验证能够开始
            print("✅ 产品经理准备就绪，可以开始执行研究任务")
        
        return True
        
    except Exception as e:
        print(f"❌ 产品经理测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🎯 开始产品经理功能测试")
    print("测试目标: 验证搜索引擎配置和产品经理基本功能")
    
    # 测试步骤
    tests = [
        ("搜索引擎配置", test_search_engine_config),
        ("搜索引擎基本功能", test_search_engine_basic),
        ("CollectLinks功能", test_collect_links),
        ("SearchEnhancedQA功能", test_search_enhanced_qa),
        ("产品经理完整功能", test_product_manager),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results[test_name] = False
    
    # 输出测试总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！产品经理功能正常")
    else:
        print("⚠️  部分测试失败，需要进一步调试")


if __name__ == "__main__":
    asyncio.run(main())