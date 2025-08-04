#!/usr/bin/env python
"""
研究Action集合 - ProductManager专用
整合MetaGPT原生ProductManager的优秀实践和CaseExpert的研究能力
完全整合case_research.py中的精细化提示词和研究逻辑
"""
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Tuple
import hashlib
import time
from pathlib import Path

from pydantic import BaseModel, Field, TypeAdapter
from metagpt.actions import Action
from metagpt.logs import logger
from metagpt.tools.search_engine import SearchEngine
from metagpt.tools.web_browser_engine import WebBrowserEngine
from metagpt.utils.project_repo import ProjectRepo
from metagpt.utils.common import OutputParser


# --- 整合case_research.py中的精细化提示词 ---
COMPREHENSIVE_RESEARCH_BASE_SYSTEM = """你是一名专业的AI研究分析师和产品经理。你的目标是：
1. 深入理解用户需求和业务背景
2. 进行全面的市场和案例研究
3. 生成高质量的研究简报，为后续的架构设计和内容生成提供坚实基础
"""

RESEARCH_TOPIC_SYSTEM = "你是一名AI研究分析师，你的研究主题是:\n#主题#\n{topic}"

SEARCH_KEYWORDS_PROMPT = """请根据你的研究主题，提供最多3个必要的关键词用于网络搜索。
这些关键词应该能够帮助收集到最相关和最有价值的信息。
你的回应必须是JSON格式，例如：["关键词1", "关键词2", "关键词3"]。"""

DECOMPOSE_RESEARCH_PROMPT = """### 要求
1. 你的研究主题和初步搜索结果展示在"参考信息"部分。
2. 请基于这些信息，生成最多 {decomposition_nums} 个与研究主题相关的、更具体的调查问题。
3. 这些问题应该能够帮助深入了解主题的不同方面，包括市场趋势、最佳实践、技术方案等。
4. 你的回应必须是JSON格式：["问题1", "问题2", "问题3", ...]。

### 参考信息
{search_results}
"""

RANK_URLS_PROMPT = """### 主题
{topic}
### 具体问题
{query}
### 原始搜索结果
{results}
### 要求
请移除与具体问题或主题无关的搜索结果。
如果问题具有时效性，请移除过时的信息。当前时间是 {time_stamp}。
然后，根据链接的可信度和相关性对剩下的结果进行排序。
优先考虑：官方文档、权威机构、知名企业案例、学术研究等。
以JSON格式提供排序后结果的索引，例如 [0, 1, 3, 4, ...]，不要包含其他任何文字。
"""

WEB_CONTENT_ANALYSIS_PROMPT = """### 要求
1. 利用"参考信息"中的文本来回答问题"{query}"。
2. 如果无法直接回答，但内容与研究主题相关，请对文本进行全面总结。
3. 如果内容完全不相关，请回复"不相关"。
4. 重点提取：关键数据、统计信息、最佳实践、技术方案、市场趋势等。
5. 保持客观性，注明信息来源的可信度。

### 参考信息
{content}
"""

GENERATE_RESEARCH_BRIEF_PROMPT = """### 参考信息
{content}

### 要求
请根据以上参考信息，生成一份关于主题"{topic}"的综合性研究简报。简报必须满足以下要求：

**结构要求：**
1. **执行摘要** - 核心发现和关键洞察
2. **市场背景** - 行业现状和趋势分析  
3. **最佳实践** - 成功案例和经验总结
4. **技术方案** - 相关技术和实施方法
5. **关键指标** - 重要的量化数据和KPI
6. **风险与挑战** - 潜在问题和应对策略
7. **建议与结论** - 基于研究的专业建议

**质量要求：**
- 内容客观、准确、有据可查
- 结构清晰，逻辑严密
- 重点突出关键信息和数据
- 为后续的架构设计和内容生成提供有价值的参考
- 使用Markdown格式，长度不少于1500字

**引用要求：**
- 在简报末尾列出所有信息来源的URL
- 对关键数据和观点进行适当的引用标注
"""


class Document(BaseModel):
    """单个文档的结构化模型"""
    filename: str
    content: str


class Documents(BaseModel):
    """文档集合的结构化模型"""
    docs: List[Document] = Field(default_factory=list)


class ResearchData(BaseModel):
    """研究成果的结构化数据模型"""
    brief: str = Field(..., description="基于研究生成的综合性简报")
    vector_store_path: str = Field(..., description="存储研究内容向量索引的路径")


class PrepareDocuments(Action):
    """扫描本地目录，加载用户提供的文档作为研究材料"""
    
    async def run(self, uploads_path: Path) -> Documents:
        """扫描uploads目录，读取所有文档内容"""
        docs = []
        if not uploads_path.exists():
            logger.warning(f"上传目录不存在: {uploads_path}")
            return Documents(docs=docs)

        logger.info(f"开始扫描文档目录: {uploads_path}")
        
        # 支持的文件类型
        supported_extensions = {'.txt', '.md', '.csv', '.json', '.yaml', '.yml'}
        
        for file_path in uploads_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    content = file_path.read_text(encoding='utf-8')
                    docs.append(Document(filename=file_path.name, content=content))
                    logger.info(f"成功读取文档: {file_path.name}")
                except Exception as e:
                    logger.error(f"读取文档失败 {file_path}: {e}")
        
        logger.info(f"文档扫描完成，共读取 {len(docs)} 个文档")
        return Documents(docs=docs)


class WriteReport(Action):
    """
    生成最终研究报告的Action
    """
    async def run(
        self, 
        topic: str, 
        research_data: ResearchData,
        project_repo: ProjectRepo = None
    ) -> str:
        """根据研究简报生成最终报告"""
        logger.info(f"开始生成关于 '{topic}' 的最终报告")

        prompt = f"""
        ### 指令
        你是一名顶级的行业分析师和报告撰写专家。
        请根据以下提供的研究简报，撰写一份全面、深入、专业的最终分析报告。

        ### 研究简报
        {research_data.brief}

        ### 报告要求
        1.  **标题**: 报告标题应清晰、准确，例如："关于'{topic}'的综合分析报告"。
        2.  **结构**: 报告应包含摘要、引言、主体分析（可分多章节）、数据洞察、结论与建议等部分，确保结构完整、逻辑清晰。
        3.  **深度**: 在研究简报的基础上进行深化和扩展，提供更深层次的分析、见解和商业建议，而仅仅是重复简报内容。
        4.  **专业性**: 使用专业、客观的商业语言，图文并茂（可用Markdown表格或Mermaid图表），增强报告的可读性和专业性。
        5.  **完整性**: 确保报告内容的完整性和连贯性，最终成为一份可以直接交付的成品。
        6.  **格式**: 使用Markdown格式撰写。

        请开始撰写最终报告：
        """

        final_report = await self._aask(prompt)

        if project_repo:
            report_path = project_repo.docs_path / f"{topic}_final_report.md"
            await project_repo.save(
                filename=str(report_path.relative_to(project_repo.workdir)),
                content=final_report
            )
            logger.info(f"最终报告已保存到: {report_path}")
        
        return final_report


class ConductComprehensiveResearch(Action):
    """
    综合研究Action - 整合本地文档和网络研究
    完全整合case_research.py中的精细化研究逻辑和提示词
    """
    
    def __init__(self, search_engine: SearchEngine = None, **kwargs):
        super().__init__(**kwargs)
        self.search_engine = search_engine

    async def run(
        self, 
        topic: str,
        decomposition_nums: int = 3,
        url_per_query: int = 3,
        project_repo: ProjectRepo = None,
        local_docs: Documents = None
    ) -> ResearchData:
        """执行全面的研究，整合网络搜索和本地文档"""
        logger.info(f"开始对主题 '{topic}' 进行全面研究...")

        # 1. 网络研究
        online_research_content = await self._conduct_online_research(topic, decomposition_nums, url_per_query)

        # 2. 本地文档分析 (如果提供)
        local_docs_content = ""
        if local_docs and local_docs.docs:
            local_docs_content = "\n\n--- 本地知识库 ---\n"
            for doc in local_docs.docs:
                local_docs_content += f"### 文档: {doc.filename}\n{doc.content}\n\n"

        # 3. 整合内容并生成研究简报
        combined_content = online_research_content + local_docs_content
        prompt = GENERATE_RESEARCH_BRIEF_PROMPT.format(content=combined_content, topic=topic)
        brief = await self._aask(prompt, [COMPREHENSIVE_RESEARCH_BASE_SYSTEM])
        
        logger.info(f"研究简报生成完毕")

        # 4. 创建并返回ResearchData
        # 注意：这里的vector_store_path只是一个示例，实际应用中需要实现向量化逻辑
        vector_store_path = f"workspace/research_data/{topic.replace(' ', '_')}.faiss"
        research_data = ResearchData(brief=brief, vector_store_path=vector_store_path)

        if project_repo:
            brief_path = project_repo.docs_path / f"{topic}_research_brief.md"
            await project_repo.save(
                filename=str(brief_path.relative_to(project_repo.workdir)),
                content=brief
            )
            logger.info(f"研究简报已保存到: {brief_path}")

        return research_data

    async def _conduct_online_research(self, topic: str, decomposition_nums: int, url_per_query: int) -> str:
        """执行在线研究"""
        logger.info("步骤 1: 生成搜索关键词")
        keywords_prompt = RESEARCH_TOPIC_SYSTEM.format(topic=topic)
        keywords_str = await self._aask(SEARCH_KEYWORDS_PROMPT, [keywords_prompt])
        try:
            keywords = OutputParser.extract_struct(keywords_str, list)
        except Exception as e:
            logger.warning(f"关键词解析失败: {e}, 使用主题作为关键词")
            keywords = [topic]

        logger.info(f"关键词: {keywords}")

        # 串行搜索关键词，避免并发请求触发频率限制
        search_results = []
        for i, kw in enumerate(keywords):
            try:
                if i > 0:  # 第一个请求不需要延迟
                    await asyncio.sleep(2)  # 每个请求间隔2秒
                result = await self.search_engine.run(kw, as_string=False)
                search_results.append(result)
                logger.info(f"成功搜索关键词: {kw}")
            except Exception as e:
                logger.error(f"搜索关键词失败 {kw}: {e}")
                search_results.append([])  # 添加空结果保持索引一致
        
        search_results_str = "\n".join([f"#### 关键词: {kw}\n{res}\n" for kw, res in zip(keywords, search_results)])

        logger.info("步骤 2: 分解研究问题")
        decompose_prompt = DECOMPOSE_RESEARCH_PROMPT.format(
            decomposition_nums=decomposition_nums, 
            search_results=search_results_str
        )
        queries_str = await self._aask(decompose_prompt, [keywords_prompt])
        try:
            queries = OutputParser.extract_struct(queries_str, list)
        except Exception as e:
            logger.warning(f"问题分解失败: {e}, 使用关键词作为问题")
            queries = keywords
        
        logger.info(f"研究问题: {queries}")

        # 串行处理每个问题，避免并发搜索
        summaries = []
        for i, q in enumerate(queries):
            if i > 0:  # 第一个请求不需要延迟
                await asyncio.sleep(1)  # 每个问题处理间隔1秒
            summary = await self._search_and_summarize_query(topic, q, url_per_query)
            summaries.append(summary)

        return "\n\n".join(summaries)

    async def _search_and_summarize_query(self, topic: str, query: str, url_per_query: int) -> str:
        """搜索、排序并总结单个问题的URL"""
        logger.info(f"处理问题: {query}")
        urls = await self._search_and_rank_urls(topic, query, url_per_query)
        
        if not urls:
            return f"### 问题: {query}\n\n未能找到相关信息。\n"

        # 串行浏览和分析URL，避免并发请求
        contents = []
        for i, url in enumerate(urls):
            if i > 0:  # 第一个请求不需要延迟
                await asyncio.sleep(1)  # 每个URL处理间隔1秒
            content = await self._web_browse_and_summarize(url, query)
            contents.append(content)

        # 过滤掉不相关的内容
        relevant_contents = [c for c in contents if "不相关" not in c]
        
        summary = f"### 问题: {query}\n\n" + "\n\n".join(relevant_contents)
        return summary

    async def _search_and_rank_urls(self, topic: str, query: str, num_results: int) -> List[str]:
        """搜索并排序URL"""
        max_results = max(num_results * 2, 6)
        try:
            results = await self.search_engine.run(query, max_results=max_results, as_string=False)
            if not results:
                logger.warning(f"搜索引擎未返回任何结果: {query}")
                return []
        except Exception as e:
            logger.error(f"搜索失败 {query}: {e}")
            return []
    
        _results_str = "\n".join(f"{i}: {res}" for i, res in enumerate(results))
        time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt = RANK_URLS_PROMPT.format(topic=topic, query=query, results=_results_str, time_stamp=time_stamp)
        
        logger.debug(f"URL排序提示词: {prompt}")  # 添加调试日志
        
        indices_str = await self._aask(prompt)
        logger.debug(f"LLM返回的排序结果: {indices_str}")  # 添加调试日志
        
        try:
            indices = OutputParser.extract_struct(indices_str, list)
            if not indices:
                logger.warning(f"LLM返回空的排序索引，使用原始顺序")
                indices = list(range(min(len(results), num_results)))
            ranked_results = [results[i] for i in indices if i < len(results)]
        except Exception as e:
            logger.warning(f"URL排序失败: {e}, 使用原始顺序")
            ranked_results = results[:num_results]
    
        final_urls = [res['link'] for res in ranked_results[:num_results]]
        logger.info(f"最终获得 {len(final_urls)} 个URL用于查询: {query}")
        
        return final_urls

    async def _web_browse_and_summarize(self, url: str, query: str) -> str:
        """浏览网页并总结内容"""
        try:
            content = await WebBrowserEngine().run(url)
            prompt = WEB_CONTENT_ANALYSIS_PROMPT.format(content=content, query=query)
            summary = await self._aask(prompt)
            return f"#### 来源: {url}\n{summary}"
        except Exception as e:
            logger.error(f"浏览URL失败 {url}: {e}")
            return f"#### 来源: {url}\n\n无法访问或处理此页面。"