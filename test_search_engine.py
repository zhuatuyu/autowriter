#!/usr/bin/env python3
"""
测试修正后的阿里云OpenSearch搜索引擎配置
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.tools.search_engine_alibaba import AlibabaSearchWrapper


async def test_search_engine():
    """测试搜索引擎是否能正常工作"""
    print("🔍 测试阿里云OpenSearch搜索引擎...")
    
    # 使用正确的配置
    search_config = {
        "api_key": "OS-ykkz87t4q83335yl",
        "endpoint": "http://default-0t01.platform-cn-shanghai.opensearch.aliyuncs.com",
        "workspace": "default",
        "service_id": "ops-web-search-001"
    }
    
    try:
        # 创建搜索引擎实例
        search_engine = AlibabaSearchWrapper(
            api_key=search_config["api_key"],
            endpoint=search_config["endpoint"],
            workspace=search_config["workspace"],
            service_id=search_config["service_id"]
        )
        
        print(f"✅ 搜索引擎创建成功")
        print(f"📡 API端点: {search_engine.base_url}")
        
        # 执行测试搜索
        test_query = "养老院建设项目案例"
        print(f"🔍 执行测试搜索: {test_query}")
        
        results = await search_engine.run(test_query, max_results=3)
        
        if results:
            print(f"✅ 搜索成功！找到 {len(results)} 个结果:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.get('title', 'N/A')}")
                print(f"     链接: {result.get('link', 'N/A')}")
                print(f"     摘要: {result.get('snippet', 'N/A')[:100]}...")
                print()
            return True
        else:
            print("❌ 搜索返回空结果")
            return False
            
    except Exception as e:
        print(f"❌ 搜索引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("🚀 开始测试修正后的搜索引擎配置...")
    
    success = await test_search_engine()
    
    if success:
        print("🎉 搜索引擎配置修正成功！")
        return True
    else:
        print("⚠️  搜索引擎仍有问题，需要进一步检查")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)