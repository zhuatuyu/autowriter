#!/usr/bin/env python
"""
健壮的搜索Action - 解决LLM返回非标准JSON的问题
"""
import json
from metagpt.actions.search_enhanced_qa import SearchEnhancedQA
from metagpt.logs import logger
from metagpt.utils.common import CodeParser


class RobustSearchEnhancedQA(SearchEnhancedQA):
    """
    一个更健壮的搜索Action，专门处理LLM返回非标准JSON的情况。
    继承自SearchEnhancedQA，只重写容易出错的查询重写部分。
    """
    
    async def _rewrite_query(self, query: str) -> str:
        """
        重写查询，如果失败则使用原始查询。
        这是对父类方法的健壮化重写。
        
        Args:
            query (str): 原始搜索查询
            
        Returns:
            str: 重写后的查询，如果失败则返回原始查询
        """
        from metagpt.actions.search_enhanced_qa import REWRITE_QUERY_PROMPT
        
        prompt = REWRITE_QUERY_PROMPT.format(q=query)
        
        try:
            # 第一次尝试：使用原有逻辑（不注入项目配置，避免超长/不兼容参数问题）
            resp = await self._aask(prompt)
            rewritten_query = self._extract_rewritten_query_robust(resp)
            logger.info(f"查询成功改写: '{query}' -> '忽略过长的rewritten_query'")
            return rewritten_query
        except Exception as e:
            logger.warning(f"查询改写失败，错误: {e}. 使用原始查询进行搜索。")
            return query
    
    def _extract_rewritten_query_robust(self, response: str) -> str:
        """
        健壮地从LLM响应中提取重写后的查询。
        
        Args:
            response (str): LLM的原始响应
            
        Returns:
            str: 提取出的查询
            
        Raises:
            ValueError: 如果无法提取查询
        """
        try:
            # 方法1: 使用MetaGPT的CodeParser
            parsed_code = CodeParser.parse_code(response, lang="json")
            if parsed_code:
                resp_json = json.loads(parsed_code)
                if "query" in resp_json:
                    return resp_json["query"]
            
            # 如果CodeParser返回空或没有query字段，继续尝试其他方法
            raise ValueError("CodeParser解析失败或没有query字段")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"方法1失败: {e}, 尝试方法2")
            
            try:
                # 方法2: 直接尝试解析整个response为JSON
                resp_json = json.loads(response)
                if "query" in resp_json:
                    return resp_json["query"]
                else:
                    raise ValueError("JSON中没有'query'字段")
                    
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"方法2失败: {e}, 尝试方法3")
                
                try:
                    # 方法3: 手动修复常见的JSON问题
                    import re
                    
                    # 清理response，移除代码块标记
                    cleaned_response = response.strip()
                    
                    # 移除 ```json 和 ``` 标记
                    cleaned_response = re.sub(r'```json\s*', '', cleaned_response)
                    cleaned_response = re.sub(r'```\s*$', '', cleaned_response)
                    
                    # 找到JSON部分
                    json_match = re.search(r'\{[^}]*\}', cleaned_response, re.DOTALL)
                    if json_match:
                        json_part = json_match.group(0)
                        
                        # 修复末尾多余的逗号问题 (如: "key": "value",})
                        json_part = re.sub(r',\s*}', '}', json_part)
                        json_part = re.sub(r',\s*]', ']', json_part)
                        
                        # 修复单引号问题
                        json_part = json_part.replace("'", '"')
                        
                        # 修复缺少键引号的问题
                        json_part = re.sub(r'(\w+):', r'"\1":', json_part)
                        
                        logger.debug(f"清理后的JSON: {json_part}")
                        
                        resp_json = json.loads(json_part)
                        if "query" in resp_json:
                            return resp_json["query"]
                    
                    raise ValueError(f"无法解析JSON，原始响应: {response[:200]}...")
                    
                except Exception as e2:
                    logger.debug(f"方法3也失败: {e2}")
                    raise ValueError(f"所有JSON解析方法都失败了，原始响应: {response[:200]}...")

    async def run(self, query: str, rewrite_query: bool = True) -> str:
        """
        执行搜索，并处理查询重写的错误。
        
        Args:
            query (str): 原始用户查询
            rewrite_query (bool): 是否尝试重写查询
            
        Returns:
            str: 基于网络搜索的详细答案
        """
        async with self._reporter:
            await self._reporter.async_report({"type": "search", "stage": "init"})
            self._validate_query(query)

            # 使用我们的健壮方法处理查询
            processed_query = await self._process_query_robust(query, rewrite_query)
            context = await self._build_context(processed_query)

            return await self._generate_answer(processed_query, context)
    
    async def _process_query_robust(self, query: str, should_rewrite: bool) -> str:
        """健壮地处理查询，即使重写失败也能继续"""
        if should_rewrite:
            try:
                return await self._rewrite_query(query)
            except Exception as e:
                logger.warning(f"查询重写完全失败: {e}, 使用原始查询")
                return query
        else:
            return query