#!/usr/bin/env python
"""
案例研究Action集合
*完全* 模仿MetaGPT中 `research.py` 的设计，移植其成熟的逻辑和Prompt工程，
仅进行最小化改造以适应“案例研究”的特定需求。
"""
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Callable

from metagpt.actions import Action
from metagpt.logs import logger
from metagpt.tools.search_engine import SearchEngine
from metagpt.tools.web_browser_engine import WebBrowserEngine
# 引入research.py中使用的所有强大工具
from metagpt.utils.common import OutputParser
from metagpt.utils.parse_html import WebPage
from metagpt.utils.text import generate_prompt_chunk, reduce_message_length
from pydantic import TypeAdapter

# --- 为案例研究定制的Prompts (直接从research.py移植和微调) ---

CASE_RESEARCH_BASE_SYSTEM = """你是一名专业的AI案例研究员。你的唯一目标是根据给定的文本，撰写一份客观、结构清晰、论据充分的案例研究报告。"""
CASE_RESEARCH_TOPIC_SYSTEM = "你是一名AI案例研究员，你的研究主题是:\n#主题#\n{topic}"
SEARCH_TOPIC_PROMPT = """请根据你的研究主题，提供最多2个必要的关键词用于网络搜索。你的回应必须是JSON格式，例如：["关键词1", "关键词2"]。"""
SUMMARIZE_SEARCH_PROMPT = """### 要求
1. 你的研究主题和初步搜索结果展示在“参考信息”部分。
2. 请基于这些信息，生成最多 {decomposition_nums} 个与研究主题相关的、更具体的调查问题。
3. 你的回应必须是JSON格式：["问题1", "问题2", "问题3", ...]。

### 参考信息
{search_results}
"""
COLLECT_AND_RANKURLS_PROMPT = """### 主题
{topic}
### 具体问题
{query}
### 原始搜索结果
{results}
### 要求
请移除与具体问题或主题无关的搜索结果。
如果问题具有时效性，请移除过时的信息。当前时间是 {time_stamp}。
然后，根据链接的可信度和相关性对剩下的结果进行排序。
以JSON格式提供排序后结果的索引，例如 [0, 1, 3, 4, ...]，不要包含其他任何文字。
"""
WEB_BROWSE_AND_SUMMARIZE_PROMPT = """### 要求
1. 利用“参考信息”中的文本来回答问题“{query}”。
2. 如果无法直接回答，但内容与研究主题相关，请对文本进行全面总结。
3. 如果内容完全不相关，请回复“不相关”。
4. 包含所有相关的事实信息、数据、统计等。

### 参考信息
{content}
"""
CONDUCT_CASE_RESEARCH_PROMPT = """### 参考信息
{content}

### 要求
请根据以上参考信息，撰写一份关于主题“{topic}”的详细案例研究报告。报告必须满足以下要求：

- 聚焦于直接回应主题。
- 结构清晰，深度分析，论据充分。
- 如适用，使用特性对比表等形式直观展示数据。
- 报告应遵循APA格式，并以Markdown语法编写，最少2000字。
- 在报告末尾以APA格式附上所有信息来源的URL。
"""


class CollectCaseLinks(Action):
    """
    Action: 从搜索引擎收集与案例研究主题相关的链接。
    完全复刻自 metagpt.actions.research.CollectLinks
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def run(
        self,
        topic: str,
        search_engine: SearchEngine,
        decomposition_nums: int = 2,  # 测试阶段降低到2
        url_per_query: int = 2,      # 测试阶段降低到2
    ) -> Dict[str, List[str]]:
        system_text = CASE_RESEARCH_TOPIC_SYSTEM.format(topic=topic)
        keywords = await self._aask(SEARCH_TOPIC_PROMPT, [system_text])
        try:
            keywords = OutputParser.extract_struct(keywords, list)
            keywords = TypeAdapter(list[str]).validate_python(keywords)
        except Exception as e:
            logger.exception(f"解析关键词失败 '{topic}' for {e}, 使用主题作为关键词")
            keywords = [topic]
        
        results = await asyncio.gather(*(search_engine.run(i, as_string=False) for i in keywords))

        # 直接构造prompt，避免复杂的生成器逻辑
        search_results = "\n".join(
            f"#### 关键词: {i}\n 搜索结果: {j}\n" for (i, j) in zip(keywords, results)
        )
        prompt = SUMMARIZE_SEARCH_PROMPT.format(
            decomposition_nums=decomposition_nums, search_results=search_results
        )
        
        # 直接使用prompt，跳过reduce_message_length
        queries = await self._aask(prompt, [system_text])
        try:
            queries = OutputParser.extract_struct(queries, list)
            queries = TypeAdapter(list[str]).validate_python(queries)
        except Exception as e:
            logger.exception(f"解析具体调查问题失败: {e}")
            queries = keywords

        ret = {}
        for query in queries:
            ret[query] = await self._search_and_rank_urls(topic, query, search_engine, url_per_query)
        return ret

    async def _search_and_rank_urls(
        self, topic: str, query: str, search_engine: SearchEngine, num_results: int = 2  # 测试阶段降低
    ) -> List[str]:
        max_results = max(num_results * 2, 4)  # 也相应降低
        results = await search_engine.run(query, max_results=max_results, as_string=False)
        if len(results) == 0:
            return []
        _results = "\n".join(f"{i}: {j}" for i, j in zip(range(max_results), results))
        time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt = COLLECT_AND_RANKURLS_PROMPT.format(topic=topic, query=query, results=_results, time_stamp=time_stamp)
        indices_str = await self._aask(prompt)
        try:
            indices = OutputParser.extract_struct(indices_str, list)
            assert all(isinstance(i, int) for i in indices)
        except Exception as e:
            logger.exception(f"排序URL失败: {e}")
            indices = list(range(len(results)))
        results = [results[i] for i in indices]
        return [i["link"] for i in results[:num_results]]


class WebBrowseAndSummarizeCase(Action):
    """
    Action: 浏览网页内容并进行总结。
    完全复刻自 metagpt.actions.research.WebBrowseAndSummarize
    """
    async def run(
        self,
        links: Dict[str, List[str]],
        system_text: str = CASE_RESEARCH_BASE_SYSTEM,
    ) -> Dict[str, str]:
        
        browser = WebBrowserEngine()
        tasks = []
        for query, urls in links.items():
            for url in urls:
                tasks.append(self._summarize_content(url, query, browser, system_text))

        summaries = await asyncio.gather(*tasks)
        
        result = {url: summary for url, summary in summaries if summary}
        return result

    async def _summarize_content(self, url: str, query: str, browser: WebBrowserEngine, system_text: str) -> Tuple[str, str]:
        try:
            page = await browser.run(url)
            content = page.inner_text

            if any(content.strip().startswith(phrase) for phrase in ["Fail to load page", "Access Denied"]):
                logger.warning(f"无效内容: {content[:100]}")
                return url, None

            # 简化逻辑：直接总结内容，避免复杂的分块处理
            # 如果内容太长，截取前5000字符
            if len(content) > 5000:
                content = content[:5000] + "..."
            
            summary_prompt = WEB_BROWSE_AND_SUMMARIZE_PROMPT.format(query=query, content=content)
            final_summary = await self._aask(summary_prompt, [system_text])
            return url, final_summary

        except Exception as e:
            logger.error(f"总结URL {url} 失败: {e}")
            return url, None


class ConductCaseResearch(Action):
    """
    Action: 撰写最终的案例研究报告并保存到文件。
    复刻自 metagpt.actions.research.ConductResearch 并增加了保存逻辑。
    """
    async def run(self, topic: str, summaries: Dict[str, str], output_dir: Path) -> Path:
        summary_text = "\n\n---\n\n".join(f"**来源链接**: {url}\n\n**内容摘要**:\n{summary}" for url, summary in summaries.items())
        
        prompt = CONDUCT_CASE_RESEARCH_PROMPT.format(topic=topic, content=summary_text)
        
        self.llm.auto_max_tokens = True
        content = await self._aask(prompt, [CASE_RESEARCH_BASE_SYSTEM])
        
        # 实现您的定制化需求：保存到指定工作区
        safe_filename = re.sub(r'[\\/:"*?<>|]+', "_", topic)[:50]
        report_file = output_dir / f"case_report_{safe_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            report_file.write_text(content, encoding='utf-8')
            logger.info(f"案例报告已保存至: {report_file}")
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            return content  # 即使保存失败，也返回内容

        return report_file 