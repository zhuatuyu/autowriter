"""
阿里云OpenSearch Web搜索工具
集成到MetaGPT框架中
"""
import asyncio
import json
from typing import List, Dict, Optional
import aiohttp
from metagpt.logs import logger

class AlibabaSearchTool:
    """阿里云OpenSearch Web搜索工具"""
    
    def __init__(self):
        self.api_key = "OS-ykkz87t4q83335yl"
        self.endpoint = "http://default-0t01.platform-cn-shanghai.opensearch.aliyuncs.com"
        self.workspace = "default"
        self.service_id = "ops-web-search-001"
        self.base_url = f"{self.endpoint}/v3/openapi/workspaces/{self.workspace}/web-search/{self.service_id}"
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """执行搜索"""
        if not query:
            return []
        
        logger.info(f"[AlibabaSearch] 搜索查询: {query}")
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }
        
        payload = {
            "query": query,
            "top_k": top_k,
            "content_type": "snippet",
            "query_rewrite": False
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"[AlibabaSearch] API错误: {response.status} - {error_text}")
                        return []
                    
                    data = await response.json()
                    
                    if data.get('code') or not data.get('result') or not data.get('result', {}).get('search_result'):
                        logger.error(f"[AlibabaSearch] 响应格式错误: {data}")
                        return []
                    
                    search_results = data['result']['search_result']
                    
                    # 过滤和格式化结果
                    formatted_results = []
                    for item in search_results:
                        formatted_item = {
                            'title': item.get('title', ''),
                            'link': item.get('link', ''),
                            'content': self._filter_content(item.get('content', '') or item.get('snippet', '')),
                            'source': item.get('link', '').split('/')[2] if item.get('link') else ''
                        }
                        formatted_results.append(formatted_item)
                    
                    logger.info(f"[AlibabaSearch] 找到 {len(formatted_results)} 个结果")
                    return formatted_results
                    
        except asyncio.TimeoutError:
            logger.error(f"[AlibabaSearch] 搜索超时: {query}")
            return []
        except Exception as e:
            logger.error(f"[AlibabaSearch] 搜索异常: {e}")
            return []
    
    def _filter_content(self, content: str) -> str:
        """过滤敏感内容"""
        if not content:
            return content
        
        # 限制内容长度
        if len(content) > 1000:
            content = content[:1000] + '...'
        
        return content
    
    async def run(self, query: str, **kwargs) -> str:
        """MetaGPT Tool接口"""
        results = await self.search(query, kwargs.get('top_k', 5))
        
        if not results:
            return f"未找到关于 '{query}' 的相关信息"
        
        # 格式化搜索结果为文本
        formatted_text = f"关于 '{query}' 的搜索结果：\n\n"
        
        for i, result in enumerate(results, 1):
            formatted_text += f"{i}. **{result['title']}**\n"
            formatted_text += f"   来源: {result['source']}\n"
            formatted_text += f"   链接: {result['link']}\n"
            formatted_text += f"   内容: {result['content']}\n\n"
        
        return formatted_text

# 全局搜索工具实例
alibaba_search_tool = AlibabaSearchTool()