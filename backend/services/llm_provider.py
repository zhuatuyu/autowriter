"""
LLM Provider
封装与大语言模型的交互，统一调用接口
"""
import os
from metagpt.provider.base_llm import BaseLLM
from metagpt.config2 import config
from metagpt.llm import LLM

class LLMProvider:
    """大语言模型提供者"""
    
    def __init__(self):
        self._configure_metagpt()
        # 直接使用MetaGPT的全局LLM实例，而不是自己创建一个
        self.llm: BaseLLM = LLM()

    def _configure_metagpt(self):
        """配置MetaGPT以便使用其LLM能力"""
        try:
            # 从环境变量或配置文件加载
            # 确保你的配置文件 (config2.yaml) 或环境变量设置正确
            # 例如: anyscale, open_llm, ollama, fireworks, openai, anthropic, zhipuai, tongyi, gemini
            # 这里我们假设使用的是qwen(通义千问)
            
            # 一个示例配置, 实际中会由metagpt.config2自动加载
            if not config.llm or not config.llm.api_key:
                 print("⚠️ LLM配置信息不完整，将使用默认或环境变量配置")

            print(f"✅ MetaGPT LLM已配置: {config.llm.model}")
            print(f"   API类型: {config.llm.api_type}")
            print(f"   API地址: {config.llm.base_url}")

        except Exception as e:
            print(f"❌ MetaGPT配置失败: {e}")
            raise

    async def acreate_text(self, prompt: str, stream: bool = False) -> str:
        """
        异步调用LLM生成文本。
        :param prompt: 输入的提示词
        :param stream: 是否流式输出 (当前实现为非流式)
        :return: LLM生成的文本
        """
        # 对于非流式，直接调用并返回结果
        if not stream:
            # MetaGPT的acompletion_text封装了完整的调用逻辑
            # **修复**: 将prompt字符串包装成OpenAI API要求的消息格式
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.acompletion_text(messages, stream=False)
            return response
        else:
            # 流式逻辑暂不实现
            raise NotImplementedError("流式输出当前未实现")

# 全局LLM提供者实例
llm = LLMProvider() 