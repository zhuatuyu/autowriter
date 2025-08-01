#!/usr/bin/env python
"""
测试阿里云搜索引擎的原生集成
"""
import asyncio
from metagpt.tools.search_engine import SearchEngine
from metagpt.configs.search_config import SearchEngineType


async def test_alibaba_search():
    """测试阿里云搜索引擎"""
    print("🚀 开始测试阿里云搜索引擎...")
    
    # 创建阿里云搜索引擎实例
    search_engine = SearchEngine(
        engine=SearchEngineType.ALIBABA,
        api_key="OS-ykkz87t4q83335yl",
        endpoint="http://default-0t01.platform-cn-shanghai.opensearch.aliyuncs.com",
        workspace="default",
        service_id="ops-web-search-001"
    )
    
    # 测试搜索
    query = "小麦一喷三防项目绩效评价"
    print(f"🔍 搜索查询: {query}")
    
    try:
        # 测试字符串格式结果
        result_str = await search_engine.run(query, max_results=3, as_string=True)
        print(f"✅ 字符串格式结果:\n{result_str[:500]}...")
        
        # 测试字典格式结果
        result_dict = await search_engine.run(query, max_results=3, as_string=False)
        print(f"✅ 字典格式结果:")
        for i, item in enumerate(result_dict):
            print(f"  结果 {i+1}:")
            print(f"    标题: {item.get('title', 'N/A')}")
            print(f"    链接: {item.get('link', 'N/A')}")
            print(f"    摘要: {item.get('snippet', 'N/A')[:100]}...")
            print()
            
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()


async def test_default_search():
    """测试默认搜索引擎（应该也是阿里云）"""
    print("\n🔍 测试默认搜索引擎...")
    
    # 使用默认配置（这里也显式传递参数，避免无参构造报错）
    search_engine = SearchEngine(
        engine=SearchEngineType.ALIBABA,
        api_key="OS-ykkz87t4q83335yl",
        endpoint="http://default-0t01.platform-cn-shanghai.opensearch.aliyuncs.com",
        workspace="default",
        service_id="ops-web-search-001"
    )
    
    query = "绩效评价报告"
    print(f"🔍 搜索查询: {query}")
    
    try:
        result = await search_engine.run(query, max_results=2, as_string=False)
        print(f"✅ 默认搜索引擎结果:")
        for i, item in enumerate(result):
            print(f"  结果 {i+1}: {item.get('title', 'N/A')}")
            
    except Exception as e:
        print(f"❌ 默认搜索失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_alibaba_search())
    asyncio.run(test_default_search()) 