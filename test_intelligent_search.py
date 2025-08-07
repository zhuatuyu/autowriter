#!/usr/bin/env python3
"""
🧠 智能检索系统测试脚本
测试知识图谱、FLARE、混合检索的完整功能
"""
import asyncio
import sys
sys.path.append('.')

from backend.services.intelligent_search import intelligent_search

async def test_intelligent_search():
    """测试智能检索的各种模式"""
    
    print("🧠 智能检索系统测试开始...")
    
    # 测试查询
    test_queries = [
        {
            "query": "绩效评价指标体系应该包含哪些维度？",
            "mode": "knowledge_graph",
            "description": "知识图谱推理模式 - 关系推理查询"
        },
                {
            "query": "项目实施过程中的风险因素分析",
            "mode": "hybrid",
            "description": "双核心混合检索模式 - 深度探索查询"
        },
        {
            "query": "财政资金使用效率评价方法",
            "mode": "hybrid",
            "description": "混合智能检索模式 - 自动选择最佳方法"
        },
        {
            "query": "政策法规合规性检查要点",
            "mode": "vector",
            "description": "传统向量检索模式 - 基础相似度匹配"
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"🧪 测试 {i}: {test_case['description']}")
        print(f"🔍 查询: {test_case['query']}")
        print(f"🤖 模式: {test_case['mode']}")
        print(f"{'='*60}")
        
        try:
            result = await intelligent_search.intelligent_search(
                query=test_case['query'],
                project_vector_storage_path="",  # 使用全局知识库
                mode=test_case['mode'],
                enable_global=True,
                max_results=3
            )
            
            print(f"✅ 检索成功")
            print(f"🎯 使用模式: {result.get('mode_used', 'unknown')}")
            print(f"📊 结果数量: {len(result.get('results', []))}")
            
            if result.get('insights'):
                print(f"💡 智能洞察:")
                for insight in result['insights']:
                    print(f"   • {insight}")
            
            if result.get('results'):
                print(f"📝 检索结果:")
                for j, res in enumerate(result['results'][:2], 1):
                    print(f"   {j}. {res[:200]}..." if len(res) > 200 else f"   {j}. {res}")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
    
    print(f"\n{'='*60}")
    print("🎉 智能检索系统测试完成!")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(test_intelligent_search())