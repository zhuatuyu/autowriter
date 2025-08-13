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
import json
import time
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field, TypeAdapter
from metagpt.actions import Action
from metagpt.logs import logger
from metagpt.tools.search_engine import SearchEngine
from metagpt.tools.web_browser_engine import WebBrowserEngine
from metagpt.utils.project_repo import ProjectRepo
from metagpt.utils.common import OutputParser
from backend.tools.search_utils import normalize_keywords
from backend.tools.json_utils import extract_json_from_llm_response
from backend.tools.project_info import get_project_info_text
from backend.config.research_prompts import (
    COMPREHENSIVE_RESEARCH_BASE_SYSTEM,  # 综合研究基础系统提示（事实密度/质量要求）
    RESEARCH_TOPIC_SYSTEM,               # 主题设定模板
    SEARCH_KEYWORDS_PROMPT,              # 关键词生成提示
    DECOMPOSE_RESEARCH_PROMPT,           # 研究问题分解提示
    RANK_URLS_PROMPT,                    # URL 排序提示（白名单约束）
    WEB_CONTENT_ANALYSIS_PROMPT,         # 网页内容分析提取提示
    select_generate_research_brief_prompt,
    ENHANCEMENT_QUERIES,                 # 研究增强查询模板
    RESEARCH_DECOMPOSITION_NUMS,         # 问题分解数量
    RESEARCH_URLS_PER_QUERY,             # 每问题URL数量
    FALLBACK_KEYWORDS,                   # 回退关键词
    MAX_INPUT_TOKENS,                    # LLM输入长度限制
    METRIC_DECOMPOSITION_DIMENSIONS,     # 指标维度分解
    SECTION_DECOMPOSITION_DIMENSIONS,    # 章节维度分解
)

# MetaGPT 原生 RAG 组件 - 强制使用，不再提供简化版本


# --- 提示词改为配置驱动，移除硬编码 ---


class Document(BaseModel):
    """单个文档的结构化模型"""
    filename: str
    content: str


class Documents(BaseModel):
    """文档集合的结构化模型"""
    docs: List[Document] = Field(default_factory=list)


class ResearchData(BaseModel):
    """研究成果的结构化数据模型（已对齐新知识库逻辑，仅保留必要字段）"""
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
        decomposition_nums: int = RESEARCH_DECOMPOSITION_NUMS,
        url_per_query: int = RESEARCH_URLS_PER_QUERY,
        project_repo: ProjectRepo = None,
        local_docs: Documents = None
    ) -> ResearchData:
        """执行全面的研究，整合网络搜索和本地文档，构建向量知识库"""
        logger.info(f"开始对主题 '{topic}' 进行全面研究，包括向量化处理...")

        # 1. 【优先】使用统一混合检索服务构建项目知识库（如果提供本地文档）
        vector_store_path = ""
        if local_docs and local_docs.docs:
            logger.info("检测到本地文档，使用统一服务构建项目知识库...")
            vector_store_path, _ = await self._build_project_knowledge_base_unified(
                topic, local_docs, project_repo
            )
            logger.info(f"✅ 项目知识库构建成功: {vector_store_path}")
            logger.info("✅ 统一检索服务已准备就绪。")
        
        # 2. 网络研究 (如果有项目知识库，将用于RAG增强)
        # SOP 推断：用于控制问题分解是否走指标维度
        sop = "sop1"
        try:
            if project_repo and "sop2" in str(project_repo.workdir).lower():
                sop = "sop2"
        except Exception:
            pass

        online_research_content = await self._conduct_online_research(
            topic, 
            decomposition_nums, 
            url_per_query,
            project_vector_path=vector_store_path,  # 传递项目知识库路径用于RAG增强
            sop=sop
        )

        # 3. 将网络研究内容也添加到项目知识库（实现共建共享）
        if online_research_content and vector_store_path:
            logger.info("🔄 将网络研究内容添加到项目知识库...")
            await self._add_online_content_to_project(online_research_content, vector_store_path, topic, project_repo)
        elif online_research_content and not vector_store_path:
            # 如果没有本地文档，为网络内容创建项目知识库
            logger.info("📁 为网络研究内容创建项目知识库...")
            vector_store_path, _ = await self._build_project_knowledge_base_unified(
                topic, Documents(), project_repo, online_content=online_research_content
            )

        # 4. 🧠 智能检索增强内容整合
        combined_content = online_research_content
        if local_docs and local_docs.docs:
            local_docs_content = "\n\n--- 本地知识库 ---\n"
            for doc in local_docs.docs:
                local_docs_content += f"### 文档: {doc.filename}\n{doc.content}\n\n"
            combined_content += local_docs_content
        
        # 🧠 使用智能检索增强研究简报生成
        enhanced_content = await self._enhance_research_with_intelligent_search(
            topic, combined_content, vector_store_path
        )

        # 收集允许引用的来源白名单
        allowed_web_urls: List[str] = []
        try:
            # 从研究内容中提取浏览过的URL（#### 来源: <url>）
            if online_research_content:
                for line in online_research_content.splitlines():
                    if line.startswith("#### 来源:"):
                        url = line.split("#### 来源:", 1)[1].strip()
                        if url.startswith("http"):
                            allowed_web_urls.append(url)
        except Exception:
            pass
        # 去重
        allowed_web_urls = list(dict.fromkeys(allowed_web_urls))

        allowed_project_docs: List[str] = []
        try:
            if vector_store_path:
                p = Path(vector_store_path)
                if p.exists() and p.is_dir():
                    for fp in p.glob("*.md"):
                        allowed_project_docs.append(fp.name)
            # 同时纳入本轮本地文档文件名
            if local_docs and local_docs.docs:
                for d in local_docs.docs:
                    allowed_project_docs.append(d.filename)
            allowed_project_docs = list(dict.fromkeys(allowed_project_docs))
        except Exception:
            pass

        # 使用安全占位符替换，避免 JSON 花括号与 str.format 冲突导致 KeyError
        # 基于SOP选择不同的扁平化研究简报模板（默认sop1）
        sop = "sop1"
        try:
            # 从项目路径推断或未来从env/flag注入
            if project_repo and "sop2" in str(project_repo.workdir).lower():
                sop = "sop2"
        except Exception:
            pass
        prompt_template = select_generate_research_brief_prompt(sop)
        time_stamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        prompt = (
            prompt_template
            .replace("{content}", enhanced_content)
            .replace("{topic}", topic)
            .replace("{time_stamp}", time_stamp)
            .replace("{allowed_web_urls}", json.dumps(allowed_web_urls, ensure_ascii=False))
            .replace("{allowed_project_docs}", json.dumps(allowed_project_docs, ensure_ascii=False))
        )
        # 防止超长输入触发底层提供商长度限制：截断到安全长度
        safe_prompt = prompt[:MAX_INPUT_TOKENS]
        # 注入项目配置信息作为系统级提示，统一对齐上下文
        project_info_text = get_project_info_text()
        brief = await self._aask(safe_prompt, [COMPREHENSIVE_RESEARCH_BASE_SYSTEM, project_info_text])
        
        logger.info(f"研究简报生成完毕。")

        # 5. 确保最终向量库路径存在（必须）
        if not vector_store_path:
            raise ValueError("项目知识库构建失败，无法继续研究流程")

        # 6. 创建并返回ResearchData
        research_data = ResearchData(
            brief=brief,
            vector_store_path=vector_store_path,
        )

        if project_repo:
            docs_filename = "research_brief.md"  # 使用固定的文件名
            await project_repo.docs.save(filename=docs_filename, content=brief)
            brief_path = project_repo.docs.workdir / docs_filename
            logger.info(f"研究简报已保存到: {brief_path}")

        return research_data

    # ========== 🚀 新的统一知识库管理方法 ==========
    
    async def _build_project_knowledge_base_unified(
        self, 
        topic: str, 
        local_docs: Documents, 
        project_repo=None, 
        online_content: str = ""
    ) -> tuple[str, List[str]]:
        """
        🚀 使用统一的混合检索服务构建项目知识库
        """
        try:
            from backend.services.hybrid_search import hybrid_search
            
            # 确定项目ID
            project_id = project_repo.workdir.name if project_repo else f"research_{hash(topic) % 10000}"
            
            # 创建项目知识库
            project_vector_path = hybrid_search.create_project_knowledge_base(project_id)
            
            # 准备要添加的内容
            contents_to_add = []
            
            # 添加本地文档
            if local_docs and local_docs.docs:
                for doc in local_docs.docs:
                    contents_to_add.append({
                        "content": doc.content,
                        "filename": doc.filename
                    })
                logger.info(f"📄 准备添加 {len(local_docs.docs)} 个本地文档")
            
            # 添加网络研究内容
            if online_content:
                contents_to_add.append({
                    "content": online_content,
                    "filename": f"网络研究_{topic}.md"
                })
                logger.info("🌐 准备添加网络研究内容")
            
            # 批量添加到项目知识库
            if contents_to_add:
                success = hybrid_search.add_multiple_contents_to_project(contents_to_add, project_vector_path)
                if not success:
                    logger.warning("⚠️ 部分内容添加失败")
            
            logger.info(f"✅ 统一项目知识库构建完成: {project_vector_path}")
            return project_vector_path, []
            
        except Exception as e:
            logger.error(f"❌ 统一项目知识库构建失败: {e}")
            # 不降级，让错误暴露出来，强制使用统一架构
            raise e
    
    async def _add_online_content_to_project(self, online_content: str, project_vector_path: str, topic: str, project_repo=None):
        """将网络研究内容添加到现有项目知识库"""
        try:
            from backend.services.hybrid_search import hybrid_search
            from datetime import datetime
            
            # 固定更友好的文件名并追加时间戳，避免过长/含特殊字符与覆盖
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            success = hybrid_search.add_content_to_project(
                content=online_content,
                filename=f"网络案例深度研究报告{ts}.md",
                project_vector_storage_path=project_vector_path
            )
            
            if success:
                logger.info("✅ 网络研究内容已添加到项目知识库")
            else:
                logger.warning("⚠️ 网络研究内容添加失败")
                
        except Exception as e:
            logger.error(f"❌ 添加网络内容失败: {e}")
    
    # 已对齐统一检索逻辑：不再手工读取内容块
    
    
    async def _enhance_research_with_intelligent_search(
        self, 
        topic: str, 
        combined_content: str, 
        vector_store_path: str
    ) -> str:
        """
        🧠 使用智能检索增强研究内容
        """
        try:
            from backend.services.intelligent_search import intelligent_search
            
            # 🧠 针对研究简报生成的专门查询（配置驱动）
            enhancement_queries = [q.replace('{topic}', topic) for q in ENHANCEMENT_QUERIES] if ENHANCEMENT_QUERIES else []
            
            enhanced_sections = []
            
            for query in enhancement_queries:
                logger.info(f"🧠 智能检索增强: {query}")
                search_result = await intelligent_search.intelligent_search(
                    query=query,
                    project_vector_storage_path=vector_store_path,
                    mode="hybrid",  # 由权重与意图路由决定是否走KG
                    enable_global=True,
                    max_results=5
                )
                
                if search_result.get("results"):
                    enhanced_sections.append(f"### 🧠 智能检索: {query}\n")
                    enhanced_sections.extend(search_result["results"])
                    enhanced_sections.append("\n")
            
            if enhanced_sections:
                enhanced_content = combined_content + "\n\n--- 🧠 智能检索增强内容 ---\n" + "\n".join(enhanced_sections)
                logger.info(f"✅ 智能检索增强完成，新增 {len(enhanced_sections)} 个内容段")
                return enhanced_content
            else:
                logger.info("ℹ️ 智能检索未发现额外内容")
                return combined_content
                
        except Exception as e:
            logger.warning(f"⚠️ 智能检索增强失败: {e}")
            return combined_content
    
    async def _conduct_online_research(self, topic: str, decomposition_nums: int, url_per_query: int, project_vector_path: str = "", sop: str = "sop1") -> str:
        """执行在线研究"""
        if not self.search_engine:
            logger.error("❌ 搜索引擎未初始化！无法进行在线研究")
            raise ValueError("搜索引擎未初始化，无法执行在线研究。请检查config/config2.yaml中的search配置")
        
        logger.info("步骤 1: 生成搜索关键词")
        keywords_prompt = RESEARCH_TOPIC_SYSTEM.format(topic=topic)
        try:
            keywords_str = await self._aask(
                SEARCH_KEYWORDS_PROMPT[:MAX_INPUT_TOKENS],
                [keywords_prompt[:MAX_INPUT_TOKENS]]
            )
        except Exception as e:
            logger.warning(f"⚠️ 关键词生成调用失败，将使用回退关键词: {e}")
            fallback = FALLBACK_KEYWORDS or []
            if not fallback:
                fallback = [topic[:50]]
            import json as _json
            keywords_str = _json.dumps(fallback, ensure_ascii=False)
        
        # 添加LLM调用后的延迟，避免频率限制
        await asyncio.sleep(1)

        # 使用统一JSON提取工具，兼容代码块/包裹文本/非严格JSON
        try:
            parsed = extract_json_from_llm_response(keywords_str)
            if isinstance(parsed, list):
                raw_keywords = parsed
            elif isinstance(parsed, dict):
                raw_keywords = parsed.get('keywords', []) or list(parsed.values())
            else:
                raise ValueError('parsed keywords not list/dict')
        except Exception as e:
            logger.warning(f"⚠️ 关键词解析失败，使用回退关键词: {e}")
            raw_keywords = FALLBACK_KEYWORDS or [topic[:50]]

        # 统一将关键词规范为字符串列表（通用工具）
        keywords = normalize_keywords(raw_keywords, topic)

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
        
        # 🧠 智能检索增强：使用智能检索服务查询项目知识库
        rag_results_str = ""
        if project_vector_path:
            try:
                from backend.services.intelligent_search import intelligent_search
                logger.info("...🧠 启动智能检索查询项目知识库...")
                
                # 使用混合智能检索
                search_result = await intelligent_search.intelligent_search(
                    query=" ".join(keywords),
                    project_vector_storage_path=project_vector_path,
                    mode="hybrid",  # 使用混合智能检索
                    enable_global=True,
                    max_results=3
                )
                
                if search_result.get("results"):
                    rag_results_str = "\n\n### 🧠 智能检索相关信息\n" + "\n".join(search_result["results"])
                    
                    # 添加智能洞察
                    if search_result.get("insights"):
                        rag_results_str += "\n\n### 💡 智能分析洞察\n" + "\n".join(search_result["insights"])
                        
            except Exception as e:
                logger.warning(f"智能检索查询失败: {e}")
        
        search_results_str = "\n".join([f"#### 关键词: {kw}\n{res}\n" for kw, res in zip(keywords, search_results)])
        
        # 将RAG结果和网络搜索结果合并
        combined_search_results = search_results_str + rag_results_str

        logger.info("步骤 2: 分解研究问题")
        # 指标构建（SOP1）场景：按 METRIC_DECOMPOSITION_DIMENSIONS 生成维度化的子问题
        if (sop or "sop1").lower() == "sop1" and METRIC_DECOMPOSITION_DIMENSIONS:
            # 将维度转为指导性子问题，数量仍受 decomposition_nums 约束
            dims = METRIC_DECOMPOSITION_DIMENSIONS[:max(1, decomposition_nums)]
            dim_queries = [f"围绕‘{d}’提出一个与主题‘{topic}’强相关且可检索的具体问题" for d in dims]
            # 直接作为 queries（跳过LLM再次分解，显著提升稳定性与速度）
            queries = dim_queries
        # 章节写作（SOP2）场景：按 SECTION_DECOMPOSITION_DIMENSIONS 生成与章节侧对齐的子问题
        elif (sop or "sop1").lower() == "sop2" and SECTION_DECOMPOSITION_DIMENSIONS:
            dims = SECTION_DECOMPOSITION_DIMENSIONS[:max(1, decomposition_nums)]
            queries = [f"围绕‘{d}’提出一个与主题‘{topic}’强相关且可检索的具体问题" for d in dims]
        else:
            decompose_prompt = DECOMPOSE_RESEARCH_PROMPT.format(
                decomposition_nums=decomposition_nums,
                url_per_query=url_per_query,
                search_results=combined_search_results
            )
            # 注入项目配置信息作为系统级提示
            project_info_text = get_project_info_text()
            queries_str = await self._aask(
                decompose_prompt[:MAX_INPUT_TOKENS],
                [keywords_prompt[:MAX_INPUT_TOKENS], project_info_text]
            )
            
            # 添加LLM调用后的延迟，避免频率限制
            await asyncio.sleep(1)
            # 统一使用通用JSON解析，兼容代码块/字典/列表
            try:
                parsed = extract_json_from_llm_response(queries_str)
                if isinstance(parsed, list):
                    queries = parsed
                elif isinstance(parsed, dict):
                    # 常见键名兜底
                    for key in ("queries", "questions", "items"):
                        if key in parsed and isinstance(parsed[key], list):
                            queries = parsed[key]
                            break
                    else:
                        # 将字典值中可用的字符串收集
                        queries = [v for v in parsed.values() if isinstance(v, str) and v.strip()]
                else:
                    raise ValueError("parsed queries not list/dict")
            except Exception as e:
                logger.warning(f"问题分解失败: {e}, 使用关键词作为问题")
                queries = keywords
        logger.info(f"研究问题: {queries}")

        # 串行处理每个问题，避免并发搜索
        summaries = []
        for i, q in enumerate(queries):
            if i > 0:  # 第一个请求不需要延迟
                await asyncio.sleep(2)  # 每个问题处理间隔2秒，增加延迟
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
                logger.error(f"❌ 搜索引擎未返回任何结果: {query}")
                raise ValueError(f"搜索引擎对查询'{query}'未返回任何结果，可能是网络问题或API配置错误")
        except Exception as e:
            logger.error(f"❌ 搜索失败 {query}: {e}")
            raise e  # 直接抛出异常，不隐藏
    
        # 以机器可读JSON形式提供候选，便于LLM进行域名白名单筛选
        candidates = []
        for i, res in enumerate(results):
            link = res.get("link", "")
            parsed = urlparse(link) if link else None
            candidates.append({
                "index": i,
                "link": link,
                "domain": (parsed.netloc if parsed else ""),
                "title": res.get("title", ""),
            })
        _results_str = json.dumps(candidates, ensure_ascii=False)
        time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt = RANK_URLS_PROMPT.format(topic=topic, query=query, results=_results_str, time_stamp=time_stamp)
        
        logger.debug(f"URL排序提示词: {prompt}")  # 添加调试日志
        
        # 注入项目配置信息作为系统级提示
        project_info_text = get_project_info_text()
        indices_str = await self._aask(prompt[:MAX_INPUT_TOKENS], [project_info_text])
        
        # 添加LLM调用后的延迟，避免频率限制
        await asyncio.sleep(0.5)
        
        logger.debug(f"LLM返回的排序结果: {indices_str}")  # 添加调试日志
        
        try:
            indices = OutputParser.extract_struct(indices_str, list)
        except Exception:
            indices = []

        ranked_results = []
        if indices:
            ranked_results = [results[i] for i in indices if isinstance(i, int) and i < len(results)]
        
        # 当LLM因白名单过严或解析失败返回空索引时，采用代码级白名单回退，避免流程中断
        if not ranked_results:
            logger.warning("⚠️ LLM URL排序返回空，启用程序化白名单回退")
            def is_whitelisted(url: str) -> bool:
                try:
                    host = urlparse(url).netloc.lower()
                    if not host:
                        return False
                    from backend.config.global_prompts import URL_WHITELIST
                    suffixes = URL_WHITELIST.get("suffix", []) or []
                    hosts = URL_WHITELIST.get("hosts", []) or []
                    for suf in suffixes:
                        if host.endswith(suf.lower()):
                            return True
                    if host in {h.lower() for h in hosts}:
                        return True
                    return False
                except Exception:
                    return False

            filtered = [res for res in results if is_whitelisted(res.get("link", ""))]
            ranked_results = filtered[:num_results] if filtered else results[:num_results]
    
        final_urls = [res['link'] for res in ranked_results[:num_results]]
        logger.info(f"最终获得 {len(final_urls)} 个URL用于查询: {query}")
        
        return final_urls

    async def _web_browse_and_summarize(self, url: str, query: str) -> str:
        """浏览网页并总结内容"""
        try:
            content = await WebBrowserEngine().run(url)
            prompt = WEB_CONTENT_ANALYSIS_PROMPT.format(content=content, query=query)
            # 注入项目配置信息作为系统级提示
            project_info_text = get_project_info_text()
            summary = await self._aask(prompt[:MAX_INPUT_TOKENS], [project_info_text])
            
            # 添加LLM调用后的延迟，避免频率限制
            await asyncio.sleep(1)
            return f"#### 来源: {url}\n{summary}"
        except Exception as e:
            logger.error(f"浏览URL失败 {url}: {e}")
            return f"#### 来源: {url}\n\n无法访问或处理此页面。"