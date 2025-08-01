#!/usr/bin/env python
"""
调试阿里云搜索引擎 - 查看完整API响应
"""
import asyncio
import json
import aiohttp
from metagpt.tools.search_engine import SearchEngine
from metagpt.configs.search_config import SearchEngineType


async def debug_alibaba_search():
    """调试阿里云搜索引擎"""
    print("🔍 开始调试阿里云搜索引擎...")
    
    # 测试不同的搜索词
    test_queries = [
        "小麦一喷三防项目绩效评价",
        "绩效评价",
        "小麦",
        "农业项目",
        "政府项目",
        "test",  # 英文测试
        "绩效",   # 简单中文
    ]
    
    for query in test_queries:
        print(f"\n🔍 测试搜索词: '{query}'")
        
        # 创建搜索引擎实例
        search_engine = SearchEngine(
            engine=SearchEngineType.ALIBABA,
            api_key="OS-ykkz87t4q83335yl",
            endpoint="http://default-0t01.platform-cn-shanghai.opensearch.aliyuncs.com",
            workspace="default",
            service_id="ops-web-search-001"
        )
        
        try:
            # 测试搜索
            result = await search_engine.run(query, max_results=3, as_string=False)
            print(f"✅ 搜索结果数量: {len(result)}")
            
            if result:
                print("📄 搜索结果:")
                for i, item in enumerate(result):
                    print(f"  结果 {i+1}:")
                    print(f"    标题: {item.get('title', 'N/A')}")
                    print(f"    链接: {item.get('link', 'N/A')}")
                    print(f"    摘要: {item.get('snippet', 'N/A')[:100]}...")
            else:
                print("❌ 没有搜索结果")
                
        except Exception as e:
            print(f"❌ 搜索失败: {e}")


async def debug_raw_api():
    """直接调用阿里云API，查看原始响应"""
    print("\n🔧 直接调用阿里云API...")
    
    api_key = "OS-ykkz87t4q83335yl"
    endpoint = "http://default-0t01.platform-cn-shanghai.opensearch.aliyuncs.com"
    workspace = "default"
    service_id = "ops-web-search-001"
    
    # 构建URL
    if endpoint.endswith('/'):
        endpoint = endpoint[:-1]
    url = f"{endpoint}/v3/openapi/workspaces/{workspace}/web-search/{service_id}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 测试不同的搜索参数
    test_payloads = [
        {
            "query": "小麦一喷三防项目绩效评价",
            "start": 0,
            "hit": 5,
            "format": "json"
        },
        {
            "query": "绩效评价",
            "start": 0,
            "hit": 5,
            "format": "json"
        },
        {
            "query": "test",
            "start": 0,
            "hit": 5,
            "format": "json"
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, payload in enumerate(test_payloads):
            print(f"\n🔧 测试API调用 {i+1}:")
            print(f"  URL: {url}")
            print(f"  Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    print(f"  Status: {response.status}")
                    print(f"  Headers: {dict(response.headers)}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"  Response: {json.dumps(data, ensure_ascii=False, indent=2)}")
                        
                        # 分析响应结构
                        if 'result' in data:
                            if 'items' in data['result']:
                                print(f"  ✅ 找到 {len(data['result']['items'])} 个结果")
                            else:
                                print(f"  ⚠️ result中没有items字段")
                        else:
                            print(f"  ⚠️ 响应中没有result字段")
                    else:
                        error_text = await response.text()
                        print(f"  ❌ 错误响应: {error_text}")
                        
            except Exception as e:
                print(f"  ❌ API调用失败: {e}")


if __name__ == "__main__":
    asyncio.run(debug_alibaba_search())
    asyncio.run(debug_raw_api()) 