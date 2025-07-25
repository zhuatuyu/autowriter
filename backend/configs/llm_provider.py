"""
LLM Provider
封装与大语言模型的交互，统一调用接口
"""
import os
from metagpt.provider.base_llm import BaseLLM
from metagpt.config2 import config
from metagpt.llm import LLM
from metagpt.provider import OpenAILLM
from metagpt.config2 import Config

class LLMProvider:
    """大语言模型提供者"""
    
    def __init__(self):
        self._configure_metagpt()
        # 默认的LLM实例
        self.llm: BaseLLM = LLM()
        # 为特定任务（如摘要）优化的LLM实例
        self.summary_llm: BaseLLM = self._initialize_summary_llm()

    def _configure_metagpt(self):
        """配置MetaGPT以便使用其LLM能力"""
        try:
            if not config.llm or not config.llm.api_key:
                 print("⚠️ 默认LLM配置信息不完整，将使用默认或环境变量配置")

            print(f"✅ 默认LLM已配置: {config.llm.model}")
        except Exception as e:
            print(f"❌ MetaGPT默认配置失败: {e}")
            raise

    def _initialize_summary_llm(self) -> BaseLLM:
        """根据配置初始化用于摘要的长文本LLM"""
        try:
            # 仿照 `debate_simple.py` 的方式
            summary_config = Config.default()
            # 从主配置中获取api_key和base_url，但指定新的模型
            if config.llm and config.llm.api_key:
                summary_config.llm.api_key = config.llm.api_key
                summary_config.llm.base_url = config.llm.base_url
                summary_config.llm.model = "qwen-long-latest" # 摘要专用模型
                
                print(f"✅ 摘要LLM已配置: {summary_config.llm.model}")
                return OpenAILLM(summary_config.llm)
            else:
                print("⚠️ 摘要LLM配置所需的基础信息（api_key）不完整，将回退到使用默认LLM")
                return self.llm
        except Exception as e:
            print(f"❌ 初始化摘要LLM失败: {e}，将回退到使用默认LLM")
            return self.llm

    async def acreate_text(self, prompt: str, stream: bool = False, use_summary_llm: bool = False) -> str:
        """
        异步调用LLM生成文本。
        :param prompt: 输入的提示词
        :param stream: 是否流式输出 (当前实现为非流式)
        :param use_summary_llm: 是否使用专用的摘要LLM
        :return: LLM生成的文本
        """
        target_llm = self.summary_llm if use_summary_llm else self.llm
        
        if not stream:
            messages = [{"role": "user", "content": prompt}]
            response = await target_llm.acompletion_text(messages, stream=False)
            return response
        else:
            raise NotImplementedError("流式输出当前未实现")

# 全局LLM提供者实例
llm = LLMProvider() 