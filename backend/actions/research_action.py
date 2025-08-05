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

# MetaGPT 原生 RAG 组件 - 强制使用，不再提供简化版本


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

### 指令
你是一名顶级的AI研究分析师，你的目标是为下游的报告架构师提供一份充满洞察力的前期调研简报。
请根据以上参考信息（包含网络案例和本地知识库），围绕主题“{topic}”生成一份高质量的研究简报。

简报标题格式应为：**《当前项目绩效评价报告前期调研简报》**

### 简报结构要求 (请严格遵循)

**1. 项目立项背景及目的分析**
   - **分析要求**: 综合网络案例和本地资料，分析此类项目通常在何种背景下立项，其核心目的是什么。
   - **给架构师的建议**: 指出在撰写最终报告的“项目概述”章节时，应重点突出哪些背景因素和项目目的，以彰显其必要性和重要性。

**2. 项目主要内容洞察**
   - **分析要求**: 剖析不同行业的类似绩效报告通常包含哪些核心内容。结合本地资料，提炼出本次报告应重点关注的几个方面。
   - **给架构师的建议**: 为报告的“项目概述”部分提供内容建议，指出哪些是必须包含的关键模块。

**3. 资金投入和使用情况分析**
   - **分析要求**: 总结网络案例中关于资金管理和使用的经验与教训。
   - **给架构师的建议**: 提醒架构师在设计“资金使用”相关章节时，应引导写作者重点关注哪些数据（如预算执行率、资金到位及时性等），并可以从哪些角度进行分析。

**4. 项目实施与组织管理经验借鉴**
   - **分析要求**: 从参考信息中提炼出项目实施和组织管理方面的最佳实践或常见问题。
   - **给架构师的建议**: 为报告的“组织管理”部分提供写作方向，例如可以借鉴哪些管理模式，或者需要规避哪些常见风险。

**5. 绩效目标设定要点**
   - **分析要求**: 基于对四个维度（决策、过程、产出、效益）的理解，分析网络案例中是如何设定绩效目标的。
   - **给架构师的建议**: 指出在设计报告的“绩效目标”部分时，四个维度分别可以从哪些角度进行目标设定，并提供可以借鉴的目标描述方式。**这不是最终的指标，而是目标设定的思路和方向**。

**6. 存在的问题和原因分析**
   - **分析要求**: 基于网络案例和本地资料，归纳总结类似项目在实施过程中普遍存在的问题（如资金使用效率低、目标达成率不足、监管缺位等）。
   - **给架构师的建议**: 预测当前项目可能面临的潜在风险和挑战。这部分内容将作为报告中“存在的问题”章节的重要参考，使得最终报告不仅能总结成绩，更能体现前瞻性的风险思考。

**7. 改进建议与经验借鉴**
   - **分析要求**: 深入分析成功案例是如何解决上述普遍问题的，提炼出可操作、可借鉴的改进措施和管理经验。
   - **给架构师的建议**: 为报告的“改进建议”章节提供素材。这些基于真实案例的建议，将比泛泛而谈的通用建议更具说服力和可操作性。

**8. 绩效评价体系推荐 (核心内容)**
   - **分析要求**: 基于所有研究，为当前项目推荐一套绩效评价指标体系。
   - **给架构师的建议**: 为“决策、过程、产出、效益”四个维度，**每个维度推荐5个具体、可衡量的评价指标**。指标应清晰，并简要说明推荐理由。这将是架构师设计指标体系的重要输入。

### 质量要求
- **深度洞察**: 不要简单罗列信息，要提炼观点、总结经验、给出建议。
- **强力支持**: 简报的每一部分都应为下游的架构师提供清晰的、可操作的指导。
- **格式清晰**: 使用Markdown格式，结构分明。


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
    content_chunks: List[str] = Field(default_factory=list, description="分块的内容列表，供RAG检索使用")


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
        decomposition_nums: int = 1,  # 测试模式: 3->2
        url_per_query: int = 1,       # 测试模式: 3->2
        project_repo: ProjectRepo = None,
        local_docs: Documents = None
    ) -> ResearchData:
        """执行全面的研究，整合网络搜索和本地文档，构建向量知识库"""
        logger.info(f"开始对主题 '{topic}' 进行全面研究，包括向量化处理...")

        # 1. 【优先】构建基础向量知识库（如果提供本地文档）
        base_engine = None
        if local_docs and local_docs.docs:
            logger.info("检测到本地文档，优先构建基础向量知识库...")
            vector_store_path, content_chunks, base_engine = await self._build_vector_knowledge_base_native(
                topic, "", local_docs, "", project_repo
            )
            logger.info(f"✅ 基础向量库构建成功: {vector_store_path}")
            logger.info("✅ 向量检索引擎已准备就绪。")
        
        # 2. 网络研究 (整合RAG检索)
        online_research_content = await self._conduct_online_research(
            topic, 
            decomposition_nums, 
            url_per_query,
            rag_engine=base_engine  # 传入RAG引擎
        )

        # 3. 整合内容并生成研究简报 (暂时保持不变，后续优化)
        combined_content = online_research_content
        if local_docs and local_docs.docs:
            local_docs_content = "\n\n--- 本地知识库 ---\n"
            for doc in local_docs.docs:
                local_docs_content += f"### 文档: {doc.filename}\n{doc.content}\n\n"
            combined_content += local_docs_content

        prompt = GENERATE_RESEARCH_BRIEF_PROMPT.format(content=combined_content, topic=topic)
        brief = await self._aask(prompt, [COMPREHENSIVE_RESEARCH_BASE_SYSTEM])
        
        logger.info(f"研究简报生成完毕。")

        # 4. 【更新】向量知识库 (将网络内容加入) - 强制使用原生RAG
        final_vector_store_path, final_content_chunks, final_engine = await self._build_vector_knowledge_base_native(
            topic, online_research_content, local_docs, combined_content, project_repo
        )
        logger.info(f"🔥 最终向量库已更新: {final_vector_store_path}")


        # 5. 创建并返回ResearchData
        research_data = ResearchData(
            brief=brief, 
            vector_store_path=final_vector_store_path,
            content_chunks=final_content_chunks
        )

        if project_repo:
            docs_filename = "research_brief.md"  # 使用固定的文件名
            await project_repo.docs.save(filename=docs_filename, content=brief)
            brief_path = project_repo.docs.workdir / docs_filename
            logger.info(f"研究简报已保存到: {brief_path}")

        return research_data
    async def _build_vector_knowledge_base_native(
        self,
        topic: str,
        online_content: str,
        local_docs: List[Document],
        combined_content: str,
        project_repo: ProjectRepo = None
    ) -> Tuple[str, List[str], "SimpleEngine"]:
        """
        使用MetaGPT原生RAG引擎构建向量知识库
        
        Returns:
            Tuple[str, List[str], SimpleEngine]: (vector_store_path, content_chunks, engine)
        """
        try:
            from metagpt.rag.engines.simple import SimpleEngine
            # from metagpt.rag.schema import FAISSRetrieverConfig, VectorIndexConfig
            import tempfile
            import os
            
            # 创建临时存储目录
            if project_repo:
                base_dir = os.path.join(project_repo.workdir, "vector_storage")
            else:
                base_dir = tempfile.mkdtemp(prefix="rag_storage_")
            
            # 安全的目录名称
            safe_topic = "".join(c for c in topic if c.isalnum() or c in "()[]{},.!?;:@#$%^&*+=_-")[:100]
            vector_store_path = os.path.join(base_dir, safe_topic)
            os.makedirs(vector_store_path, exist_ok=True)
            
            # 准备文档内容
            all_content = []
            
            # 添加在线研究内容
            if online_content and online_content.strip():
                all_content.append(("在线研究内容", online_content))
            
            # 添加本地文档内容
            if local_docs:  # 检查local_docs不为None
                for doc in local_docs.docs:  # 正确访问docs属性
                    if doc.content and doc.content.strip():
                        all_content.append((f"本地文档: {doc.filename}", doc.content))
            
            if not all_content:
                logger.warning("没有可用内容构建向量知识库")
                return vector_store_path, [], None
            
            # 将内容转换为临时文件
            temp_files = []
            content_chunks = []
            
            for title, content in all_content:
                # 将内容分块
                chunks = self._split_content_to_chunks(content)
                content_chunks.extend(chunks)
                
                # 创建临时文件
                temp_file = os.path.join(vector_store_path, f"{len(temp_files)}.txt")
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {title}\n\n{content}")
                temp_files.append(temp_file)
            
            # 使用MetaGPT原生的RAG embedding工厂 - 这是正确的方式！
            from llama_index.llms.openai import OpenAI as LlamaOpenAI
            from pathlib import Path
            from metagpt.config2 import Config
            from metagpt.rag.factories.embedding import get_rag_embedding
            
            # 手动加载完整配置，确保embedding配置被正确读取
            full_config = Config.from_yaml_file(Path('config/config2.yaml'))
            
            # 获取LLM配置 - 使用兼容的模型名
            llm_config = full_config.llm
            llm = LlamaOpenAI(
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                model="gpt-3.5-turbo"  # 使用llama_index认识的模型名，实际会调用阿里云API
            )
            
            # 使用MetaGPT原生embedding工厂 - 这会正确处理model_name参数
            embed_model = get_rag_embedding(config=full_config)
            # 阿里云DashScope embedding API限制批处理大小不能超过10
            embed_model.embed_batch_size = 10
            
            engine = SimpleEngine.from_docs(
                input_files=temp_files,  # 提供文件列表
                llm=llm,  # 真实的LLM配置
                embed_model=embed_model  # 真实的嵌入模型
            )
            
            logger.info(f"✅ 向量知识库已构建，共 {len(content_chunks)} 个内容块")
            logger.info(f"📁 向量库存储路径: {vector_store_path}")
            
            return vector_store_path, content_chunks, engine
            
        except Exception as e:
            logger.error(f"原生RAG引擎构建失败: {e}")
            # 不再降级，让错误暴露出来
            raise e
    

    
    def _split_content_to_chunks(self, content: str, max_chunk_size: int = 1000) -> List[str]:
        """将内容分割成块"""
        # 简单的分块策略：按段落和长度分割
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # 如果当前块加上新段落会超出限制，保存当前块
            if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += ("\n\n" if current_chunk else "") + paragraph
        
        # 添加最后一个块
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks

    async def _conduct_online_research(self, topic: str, decomposition_nums: int, url_per_query: int, rag_engine=None) -> str:
        """执行在线研究"""
        if not self.search_engine:
            logger.warning("搜索引擎未初始化，将返回模拟研究内容")
            return f"""### 模拟研究内容
            
主题: {topic}

这是一个模拟的在线研究结果。由于搜索引擎未配置，我们提供以下模拟内容：

1. **背景信息**: 该项目属于农业领域的绩效评价项目
2. **行业趋势**: 当前农业项目越来越注重科学化管理和绩效评估
3. **最佳实践**: 综合性评价体系应包括经济效益、社会效益和环境效益
4. **技术方案**: 使用数据分析和专业评估方法
5. **关键指标**: 成本控制、项目完成度、用户满意度等

这是一个测试用的模拟研究内容，实际部署时应配置有效的搜索引擎。
"""
        
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
        
        # RAG增强：使用关键词查询本地向量库
        rag_results_str = ""
        if rag_engine:
            logger.info("...同时查询本地向量知识库...")
            rag_results = await rag_engine.aretrieve(query=" ".join(keywords))
            if rag_results:
                rag_results_str = "\n\n### 本地知识库相关信息\n" + "\n".join([r.text for r in rag_results])
        
        search_results_str = "\n".join([f"#### 关键词: {kw}\n{res}\n" for kw, res in zip(keywords, search_results)])
        
        # 将RAG结果和网络搜索结果合并
        combined_search_results = search_results_str + rag_results_str

        logger.info("步骤 2: 分解研究问题")
        decompose_prompt = DECOMPOSE_RESEARCH_PROMPT.format(
            decomposition_nums=decomposition_nums, 
            search_results=combined_search_results
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