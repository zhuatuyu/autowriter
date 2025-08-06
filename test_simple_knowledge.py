#!/usr/bin/env python3
"""
简单测试全局知识库基本功能
"""

import asyncio
import sys
sys.path.append('.')

from backend.services.global_knowledge import global_knowledge


async def simple_test():
    """简单测试"""
    print("🧪 开始简单测试...")
    
    # 直接在内存中构建，不持久化
    try:
        # 修改全局知识库管理器，暂时跳过持久化
        global_knowledge._global_engine = None
        
        # 获取全局文件
        global_files = global_knowledge.collect_global_files()
        print(f"📁 找到 {len(global_files)} 个全局文件")
        
        if global_files:
            print("✅ 全局知识库文件收集成功")
            for f in global_files:
                print(f"  - {f}")
        else:
            print("❌ 没有找到全局知识库文件")
            
        # 测试配置
        config = global_knowledge._get_config()
        print(f"✅ 配置加载成功: {type(config)}")
        
        # 测试LLM和embed模型创建
        llm, embed_model = global_knowledge._create_llm_and_embed_model()
        print(f"✅ LLM和嵌入模型创建成功")
        print(f"  - LLM: {type(llm)}")
        print(f"  - 嵌入模型: {type(embed_model)}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(simple_test())