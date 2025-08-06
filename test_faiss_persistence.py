#!/usr/bin/env python3
"""
测试FAISS持久化的正确用法
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.append('.')

from metagpt.rag.engines.simple import SimpleEngine
from metagpt.rag.factories.embedding import get_rag_embedding
from metagpt.rag.schema import FAISSRetrieverConfig, FAISSIndexConfig
from metagpt.config2 import Config
from llama_index.llms.openai import OpenAI as LlamaOpenAI


async def test_faiss_basic():
    """测试基本的FAISS功能"""
    print("🧪 测试FAISS基本功能...")
    
    try:
        # 准备测试文件
        test_dir = Path("test_faiss")
        test_dir.mkdir(exist_ok=True)
        
        test_file = test_dir / "test.md"
        test_file.write_text("""
# 测试文档

这是一个测试文档，用于验证FAISS向量存储功能。

## 内容1
预算法是中华人民共和国的重要法律。

## 内容2  
绩效评价是财政管理的重要手段。

## 内容3
项目管理需要遵循相关规定。
""", encoding='utf-8')
        
        persist_dir = test_dir / "faiss_index"
        persist_dir.mkdir(exist_ok=True)
        
        # 加载配置
        config = Config.from_yaml_file(Path('config/config2.yaml'))
        llm_config = config.llm
        
        llm = LlamaOpenAI(
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            model="gpt-3.5-turbo"
        )
        
        embed_model = get_rag_embedding(config=config)
        embed_model.embed_batch_size = 8
        
        print("✅ 配置加载成功")
        
        # 🚀 方法1：尝试使用FAISSRetrieverConfig
        print("\n📝 方法1：使用FAISSRetrieverConfig")
        try:
            engine = SimpleEngine.from_docs(
                input_files=[str(test_file)],
                llm=llm,
                embed_model=embed_model,
                retriever_configs=[FAISSRetrieverConfig(dimensions=1024)]
            )
            
            # 测试检索
            results = await engine.aretrieve("预算法")
            print(f"✅ 检索成功，找到 {len(results)} 条结果")
            if results:
                print(f"   第一条: {results[0].text[:50]}...")
            
            # 尝试持久化
            try:
                engine.persist(str(persist_dir / "method1"))
                print("✅ 持久化成功（方法1）")
                
                # 尝试加载
                try:
                    loaded_engine = SimpleEngine.from_index(
                        index_config=FAISSIndexConfig(
                            persist_path=str(persist_dir / "method1"),
                            embed_model=embed_model
                        ),
                        embed_model=embed_model,
                        llm=llm
                    )
                    
                    # 测试加载后的检索
                    loaded_results = await loaded_engine.aretrieve("绩效评价")
                    print(f"✅ 加载后检索成功，找到 {len(loaded_results)} 条结果")
                    
                except Exception as e:
                    print(f"❌ 加载失败: {e}")
                    
            except Exception as e:
                print(f"❌ 持久化失败: {e}")
                
        except Exception as e:
            print(f"❌ 方法1失败: {e}")
        
        # 🚀 方法2：尝试不指定retriever_configs（默认方式）
        print("\n📝 方法2：默认方式")
        try:
            engine2 = SimpleEngine.from_docs(
                input_files=[str(test_file)],
                llm=llm,
                embed_model=embed_model
            )
            
            # 测试检索
            results2 = await engine2.aretrieve("项目管理")
            print(f"✅ 检索成功，找到 {len(results2)} 条结果")
            
            # 检查retriever类型
            print(f"🔍 Retriever类型: {type(engine2.retriever)}")
            
            # 尝试持久化
            try:
                engine2.persist(str(persist_dir / "method2"))
                print("✅ 持久化成功（方法2）")
            except Exception as e:
                print(f"❌ 持久化失败（方法2）: {e}")
                print(f"   原因: {type(e).__name__}: {e}")
                
        except Exception as e:
            print(f"❌ 方法2失败: {e}")
        
        # 清理
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)
        print("\n🗑️ 测试文件已清理")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_faiss_basic())