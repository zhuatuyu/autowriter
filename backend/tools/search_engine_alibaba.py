"""
阿里云OpenSearch Web搜索工具的MetaGPT标准化封装
"""
import asyncio
import json
from typing import List, Dict, Union
import aiohttp
from metagpt.logs import logger
from metagpt.tools.search_engine import SearchEngine, SearchEngineType


class AlibabaSearchWrapper:
    """
    模仿MetaGPT原生搜索工具（如SerperWrapper）的结构，封装阿里云OpenSearch API
    """
    def __init__(self, api_key: str, endpoint: str, workspace: str, service_id: str):
        self.api_key = api_key
        self.base_url = f"{endpoint}/v3/openapi/workspaces/{workspace}/web-search/{service_id}"

    async def run(self, query: str, max_results: int = 5, as_string: bool = False) -> Union[str, List[Dict]]:
        """
        执行搜索并返回MetaGPT标准格式的结果
        :param query: 搜索查询
        :param max_results: 返回结果数量
        :param as_string: 是否返回字符串（我们主要用False，返回结构化数据）
        :return: 搜索结果
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }
        payload = {
            "query": query,
            "top_k": max_results,
            "content_type": "snippet",
            "query_rewrite": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()

            if data.get('code') or not data.get('result') or not data.get('result', {}).get('search_result'):
                logger.error(f"[AlibabaSearch] 响应格式错误: {data}")
                return []

            search_results = data['result']['search_result']
            
            # 格式化为MetaGPT标准格式: {'title': '...', 'link': '...', 'snippet': '...'}
            formatted_results = [
                {
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'snippet': item.get('content', '') or item.get('snippet', '')
                }
                for item in search_results
            ]
            
            logger.info(f"[AlibabaSearch] 找到 {len(formatted_results)} 个结果")
            return formatted_results

        except Exception as e:
            logger.error(f"[AlibabaSearch] 搜索异常: {e}")
            return []


def alibaba_search_engine(config: dict) -> SearchEngine:
    """
    一个工厂函数，用于创建和配置阿里巴巴搜索引擎实例
    """
    api_key = config.get("api_key")
    endpoint = config.get("endpoint")
    workspace = config.get("workspace")
    service_id = config.get("service_id")

    # 创建一个继承自SearchEngine的临时类，以集成我们的自定义逻辑
    class AlibabaSearch(SearchEngine):
        def __init__(self, **kwargs):
            super().__init__(engine=SearchEngineType.CUSTOM_ENGINE, **kwargs)
            self.engine_class = AlibabaSearchWrapper(
                api_key=api_key, 
                endpoint=endpoint, 
                workspace=workspace, 
                service_id=service_id
            )
            self.run_func = self.engine_class.run
    
    return AlibabaSearch() 