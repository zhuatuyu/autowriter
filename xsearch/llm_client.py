#!/usr/bin/env python3
"""
LLM客户端
与Google Gemini API交互
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# 不再需要Google Generative AI，直接使用阿里云
GOOGLE_AI_AVAILABLE = False


class LLMClient:
    """LLM客户端"""
    
    def __init__(self, project_config: Dict[str, Any]):
        self.project_config = project_config
        self._load_llm_config()
    
    def _load_llm_config(self):
        """加载LLM配置"""
        try:
            # 尝试加载项目配置
            config_path = Path(self.project_config['project_root']) / 'config' / 'config2.yaml'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    import yaml
                    config = yaml.safe_load(f)
                
                llm_config = config.get('llm', {})
                self.api_key = llm_config.get('api_key', '')
                self.base_url = llm_config.get('base_url', '')
                self.model_name = llm_config.get('model', 'qwen-plus-latest')
                
                print(f"✅ 加载LLM配置: {self.model_name}")
                
                # 使用阿里云配置创建LLM
                if self.api_key and self.base_url:
                    self.model = self._create_aliyun_llm()
                else:
                    self.model = None
                    print("⚠️ LLM配置不完整，将使用模拟响应")
            else:
                self.model = None
                print("⚠️ 配置文件不存在，将使用模拟响应")
                
        except Exception as e:
            print(f"⚠️ 加载LLM配置失败: {e}")
            self.model = None
    
    def _create_aliyun_llm(self):
        """创建阿里云LLM客户端"""
        try:
            from llama_index.llms.openai_like import OpenAILike
            
            llm = OpenAILike(
                model=self.model_name,
                api_base=self.base_url,
                api_key=self.api_key,
                is_chat_model=True
            )
            
            print(f"✅ 阿里云LLM客户端创建成功: {self.model_name}")
            return llm
            
        except Exception as e:
            print(f"⚠️ 创建阿里云LLM客户端失败: {e}")
            return None
    
    async def analyze_intent(self, prompt: str) -> Dict[str, Any]:
        """分析查询意图"""
        if self.model:
            try:
                response = await self._async_generate(prompt)
                return response
            except Exception as e:
                print(f"⚠️ LLM意图分析失败: {e}")
                return self._get_default_intent()
        else:
            return self._get_default_intent()
    
    async def generate_evaluation(self, prompt: str) -> str:
        """生成评价结果"""
        if self.model:
            try:
                response = await self._async_generate(prompt)
                return response
            except Exception as e:
                print(f"⚠️ LLM评价生成失败: {e}")
                return self._get_default_evaluation()
        else:
            return self._get_default_evaluation()
    
    async def _async_generate(self, prompt: str) -> str:
        """异步生成文本"""
        if not self.model:
            return self._get_default_response()
        
        try:
            loop = asyncio.get_event_loop()
            
            def generate():
                # 使用阿里云LLM
                if hasattr(self.model, 'complete'):
                    # OpenAILike格式
                    response = self.model.complete(prompt)
                    return response.text
                else:
                    # 其他格式
                    return "LLM响应格式不支持"
            
            return await loop.run_in_executor(None, generate)
            
        except Exception as e:
            print(f"⚠️ LLM调用失败: {e}")
            return self._get_default_response()
    
    def _get_default_response(self) -> str:
        """获取默认响应"""
        return "LLM服务不可用，使用默认响应"
    
    def _get_default_intent(self) -> Dict[str, Any]:
        """获取默认的意图分析结果"""
        return {
            "core_topic": "项目分析",
            "data_requirements": ["项目数据", "评价标准"],
            "analysis_dimensions": ["有效性", "合理性"],
            "evaluation_structure": ["现状分析", "问题识别", "改进建议"],
            "search_keywords": ["项目", "分析", "评价"],
            "extraction_fields": ["基本信息", "关键指标", "问题描述"]
        }
    
    def _get_default_evaluation(self) -> str:
        """获取默认的评价结果"""
        return """
        基于当前可用的项目数据和评价标准，给出以下分析评价：

        1. 现状分析
        由于数据有限，建议进一步收集项目相关信息进行分析。

        2. 问题识别
        需要更多项目具体数据来识别潜在问题。

        3. 改进建议
        建议完善项目数据收集和整理，为后续分析提供基础。
        """
