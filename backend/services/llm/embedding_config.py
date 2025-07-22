"""
阿里云DashScope Embedding配置
用于MetaGPT长期记忆系统
"""
from llama_index.embeddings.dashscope import DashScopeEmbedding
from llama_index.core.embeddings import BaseEmbedding
from metagpt.config2 import config
from metagpt.logs import logger


def get_dashscope_embedding() -> BaseEmbedding:
    """
    获取阿里云DashScope的embedding模型
    使用与LLM相同的API Key
    """
    try:
        # 从MetaGPT配置中获取API Key
        llm_config = config.get_openai_llm()
        if llm_config is None:
            raise ValueError("LLM配置未找到，请检查config2.yaml中的llm配置")
        
        api_key = llm_config.api_key
        if not api_key:
            raise ValueError("API Key未配置，请检查config2.yaml中的api_key")
        
        # 创建DashScope Embedding实例
        embedding = DashScopeEmbedding(
            model_name="text-embedding-v1",  # 阿里云默认的embedding模型
            api_key=api_key,
            # 可以根据需要调整其他参数
            # text_type="document",  # 可选: "query" 或 "document"
        )
        
        logger.info("✅ 阿里云DashScope Embedding配置成功")
        return embedding
        
    except Exception as e:
        logger.error(f"❌ 配置阿里云DashScope Embedding失败: {e}")
        # 如果配置失败，返回None，让系统使用默认配置
        return None


def get_embedding_for_memory() -> BaseEmbedding:
    """
    为MetaGPT记忆系统获取embedding模型
    优先使用阿里云DashScope，失败时使用默认配置
    """
    try:
        # 尝试使用阿里云DashScope
        dashscope_embedding = get_dashscope_embedding()
        if dashscope_embedding is not None:
            return dashscope_embedding
        
        logger.warning("⚠️ 阿里云DashScope Embedding配置失败，尝试使用默认OpenAI Embedding")
        
        # 备用方案：使用原始的OpenAI Embedding配置
        from metagpt.utils.embedding import get_embedding
        return get_embedding()
        
    except Exception as e:
        logger.error(f"❌ 所有embedding配置都失败了: {e}")
        logger.info("💡 提示：请检查config2.yaml中的LLM配置，确保api_key正确设置")
        raise


# 测试函数
async def test_embedding():
    """测试embedding配置是否正常工作"""
    try:
        embedding = get_embedding_for_memory()
        
        # 测试embedding
        test_text = "这是一个测试文本"
        result = await embedding.aget_text_embedding(test_text)
        
        logger.info(f"✅ Embedding测试成功，向量维度: {len(result)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Embedding测试失败: {e}")
        return False


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_embedding())