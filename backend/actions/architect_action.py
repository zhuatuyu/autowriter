#!/usr/bin/env python
"""
架构师Action集合 - 报告结构设计和指标分析
重构实现三环节逻辑：分析简报 -> RAG检索 -> 综合设计
"""
import pandas as pd
import json
import re
from typing import List, Tuple, Optional
from pydantic import BaseModel, Field
from metagpt.actions import Action
from metagpt.logs import logger
from backend.actions.research_action import ResearchData


class Section(BaseModel):
    """报告章节的结构化模型"""
    section_title: str = Field(..., description="章节标题")
    metric_ids: List[str] = Field(default_factory=list, description="本章节关联的指标ID列表")
    description_prompt: str = Field(..., description="指导本章节写作的核心要点或问题")


class ReportStructure(BaseModel):
    """报告整体架构的结构化模型"""
    title: str = Field(..., description="报告主标题")
    sections: List[Section] = Field(..., description="报告的章节列表")


class MetricAnalysisTable(BaseModel):
    """指标分析表的结构化模型"""
    data_json: str = Field(..., description="存储指标分析结果的DataFrame (JSON格式)")


class ArchitectOutput(BaseModel):
    """Architect输出的复合数据结构"""
    report_structure: ReportStructure = Field(..., description="报告结构设计")
    metric_analysis_table: MetricAnalysisTable = Field(..., description="指标分析表")


class DesignReportStructure(Action):
    """
    设计报告结构Action - Architect的核心能力
    实现三环节逻辑：分析简报 -> RAG检索 -> 综合设计
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._research_data: Optional[ResearchData] = None
    
    async def run(self, enhanced_research_context: str, research_data: Optional[ResearchData] = None) -> Tuple[ReportStructure, MetricAnalysisTable]:
        """
        基于标准绩效评价模板设计报告结构，内容根据项目特点定制
        
        Args:
            enhanced_research_context: 可能已经经过RAG增强的研究上下文
            research_data: ProductManager提供的研究数据（包含向量知识库）
        """
        logger.info("🏗️ 开始基于标准模板的报告结构设计...")
        self._research_data = research_data
        
        # 从增强上下文中提取原始研究简报
        research_brief = self._extract_original_brief(enhanced_research_context)
        
        # 步骤一：项目信息提取 - 从研究简报和RAG中提取项目核心信息
        logger.info("📋 步骤一：提取项目核心信息...")
        project_info = await self._extract_project_info(research_brief)
        
        # 步骤二：RAG增强 - 查询详细资料丰富项目信息
        logger.info("🔍 步骤二：RAG检索增强项目信息...")
        enriched_info = await self._enrich_with_rag(project_info)
        
        # 步骤三：标准结构定制 - 基于固定模板生成定制化内容
        logger.info("🏗️ 步骤三：基于标准模板生成定制化内容...")
        report_structure, metric_table = await self._generate_customized_template(enriched_info)
        
        logger.info(f"✅ 报告蓝图设计完成: {report_structure.title}")
        logger.info(f"📊 指标体系: {len(json.loads(metric_table.data_json))} 个指标")
        
        return report_structure, metric_table
    
    def _extract_original_brief(self, enhanced_context: str) -> str:
        """从增强上下文中提取原始研究简报"""
        # 如果包含RAG增强内容，提取原始部分
        if "### RAG检索增强内容" in enhanced_context:
            parts = enhanced_context.split("### RAG检索增强内容")
            return parts[0].strip()
        return enhanced_context
    
    async def _extract_project_info(self, research_brief: str) -> dict:
        """
        步骤一：从研究简报中提取项目核心信息
        """
        extraction_prompt = f"""
你是绩效评价报告的架构师。请从以下研究简报中提取项目的核心信息，用于后续基于标准模板的报告结构设计。

研究简报：
{research_brief}

请返回JSON格式，包含以下字段：
1. project_name: 项目全称
2. project_type: 项目类型（如：财政支出项目、专项资金项目等）
3. budget_amount: 项目预算金额（如果有）
4. implementation_period: 实施期间
5. target_beneficiaries: 主要受益对象
6. main_objectives: 主要目标（列表形式）
7. key_activities: 主要活动内容（列表形式）
8. performance_focus: 绩效重点关注领域（如：经济效益、社会效益、生态效益等）

要求：
- 信息要准确、完整
- 如果某些信息不明确，标注为"待补充"
- 重点关注与绩效评价相关的信息
"""
        
        try:
            extraction_result = await self._aask(extraction_prompt)
            
            # 从LLM回复中提取JSON内容
            project_info = self._extract_json_from_llm_response(extraction_result)
            
            logger.info(f"📋 项目名称: {project_info.get('project_name', '未知项目')}")
            logger.info(f"📋 项目类型: {project_info.get('project_type', '待补充')}")
            return project_info
        except Exception as e:
            logger.error(f"项目信息提取失败，无法继续设计: {e}")
            raise ValueError(f"无法从研究简报中提取有效项目信息: {e}")
    
    def _extract_json_from_llm_response(self, response: str) -> dict:
        """
        从LLM回复中提取JSON内容，处理markdown格式和额外说明
        """
        try:
            # 方法1：尝试直接解析（如果是纯JSON）
            return json.loads(response)
        except:
            pass
        
        try:
            # 方法2：提取```json代码块中的内容
            import re
            json_pattern = r'```json\s*(.*?)\s*```'
            match = re.search(json_pattern, response, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                return json.loads(json_str)
        except:
            pass
        
        try:
            # 方法3：查找大括号包围的JSON内容
            start_idx = response.find('{')
            if start_idx != -1:
                # 找到第一个{，然后找到匹配的}
                brace_count = 0
                end_idx = start_idx
                for i, char in enumerate(response[start_idx:], start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break
                
                if brace_count == 0:
                    json_str = response[start_idx:end_idx+1]
                    return json.loads(json_str)
        except:
            pass
        
        # 如果所有方法都失败，抛出异常
        raise ValueError(f"无法从LLM回复中提取有效JSON: {response[:200]}...")
    
    async def _enrich_with_rag(self, project_info: dict) -> dict:
        """
        步骤二：通过RAG检索丰富项目信息 - 动态生成检索关键词
        """
        if not self._research_data or not self._research_data.content_chunks:
            logger.warning("向量知识库不可用，返回原始项目信息")
            return project_info
        
        # 动态生成检索关键词
        search_keywords = await self._generate_rag_search_keywords(project_info)
        
        enriched_info = project_info.copy()
        enriched_info["rag_evidence"] = {}
        
        logger.info(f"🔍 开始对 {len(search_keywords)} 个动态关键词进行RAG检索（请稍候）...")
        
        for keyword_group in search_keywords:
            category = keyword_group["category"]
            keywords = keyword_group["keywords"]
            
            # 对每个关键词组进行检索
            category_evidence = []
            for keyword in keywords:
                relevant_chunks = await self._search_chunks(keyword, self._research_data.content_chunks)
                if relevant_chunks:
                    category_evidence.extend(relevant_chunks[:2])  # 每个关键词取前2个最相关的
            
            if category_evidence:
                enriched_info["rag_evidence"][category] = category_evidence
                # 简化单个类别的日志输出
                logger.debug(f"📋 {category}: 检索到 {len(category_evidence)} 条相关证据")
        
        logger.info(f"📋 RAG检索完成，丰富了 {len(enriched_info['rag_evidence'])} 个信息类别")
        return enriched_info
    
    async def _generate_rag_search_keywords(self, project_info: dict) -> List[dict]:
        """
        动态生成RAG检索关键词（类似PM的关键词生成逻辑）
        """
        project_name = project_info.get('project_name', '项目')
        
        keyword_generation_prompt = f"""
你是架构师的RAG检索助手。基于以下项目信息，生成用于检索向量知识库的关键词组。

项目信息：
{json.dumps(project_info, ensure_ascii=False, indent=2)}

请生成6个类别的检索关键词，每个类别包含3-5个具体的检索词：

返回JSON格式：
[
  {{
    "category": "项目背景与目标",
    "keywords": ["项目立项背景", "主要目标", "预期成果"]
  }},
  {{
    "category": "资金与预算",
    "keywords": ["预算总额", "资金来源", "资金分配"]
  }},
  {{
    "category": "实施方案",
    "keywords": ["实施步骤", "技术方案", "管理措施"]
  }},
  {{
    "category": "效果与成效",
    "keywords": ["实施效果", "产出指标", "效益分析"]
  }},
  {{
    "category": "政策依据",
    "keywords": ["政策文件", "法规依据", "标准规范"]
  }},
  {{
    "category": "风险与挑战",
    "keywords": ["存在问题", "风险因素", "改进建议"]
  }}
]

要求：关键词要具体、准确，能在{project_name}相关资料中找到对应信息。
"""
        
        try:
            keywords_result = await self._aask(keyword_generation_prompt)
            
            # 使用同样的JSON提取逻辑
            search_keywords = self._extract_json_from_llm_response(keywords_result)
            
            logger.info(f"🔍 动态生成了 {len(search_keywords)} 个关键词组")
            return search_keywords
        except Exception as e:
            logger.warning(f"动态关键词生成失败，使用基础关键词: {e}")
            # 基础关键词作为备用
            return [
                {"category": "项目基本信息", "keywords": ["项目名称", "项目背景", "主要目标"]},
                {"category": "资金预算", "keywords": ["预算金额", "资金来源", "支出明细"]},
                {"category": "实施内容", "keywords": ["实施方案", "技术措施", "管理流程"]},
                {"category": "绩效指标", "keywords": ["评价指标", "成果产出", "效益分析"]}
            ]
    
    async def _search_chunks(self, query: str, content_chunks: List[str]) -> List[str]:
        """在内容块中搜索相关信息，尝试使用向量检索"""
        try:
            # 首先尝试使用向量检索
            if self._research_data and hasattr(self._research_data, 'vector_store_path'):
                vector_results = await self._vector_search(query, self._research_data.vector_store_path)
                if vector_results:
                    return vector_results[:3]  # 返回前3个最相关的
        except Exception as e:
            logger.warning(f"向量检索失败，降级到关键词检索: {e}")
        
        # 降级到关键词检索
        query_keywords = self._extract_search_keywords(query)
        
        # 计算每个块的相关度
        chunk_scores = []
        for chunk in content_chunks:
            score = self._calculate_chunk_relevance(chunk, query_keywords)
            if score > 0:
                chunk_scores.append((score, chunk))
        
        # 按相关度排序
        chunk_scores.sort(reverse=True)
        return [chunk for score, chunk in chunk_scores[:3]]  # 返回前3个最相关的
    
    async def _vector_search(self, query: str, vector_store_path: str) -> List[str]:
        """使用向量检索搜索相关内容"""
        try:
            from metagpt.rag.engines.simple import SimpleEngine
            from metagpt.rag.schema import FAISSRetrieverConfig, VectorIndexConfig
            import os
            
            if not os.path.exists(vector_store_path):
                logger.warning(f"向量库路径不存在: {vector_store_path}")
                return []
            
            # 检查并加载已有的向量库
            # 注意：这里需要使用PM创建的相同文件来初始化
            vector_files = []
            if os.path.isdir(vector_store_path):
                vector_files = [os.path.join(vector_store_path, f) for f in os.listdir(vector_store_path) if f.endswith('.txt')]
            
            if not vector_files:
                logger.warning(f"向量库目录为空: {vector_store_path}")
                return []
            
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
                input_files=vector_files,  # 使用已存在的文件
                llm=llm,  # 真实的LLM配置
                embed_model=embed_model  # 真实的嵌入模型
            )
            
            # 执行检索
            results = await engine.aretrieve(query)
            
            # 提取内容
            retrieved_texts = []
            for result in results:
                if hasattr(result, 'text') and result.text:
                    retrieved_texts.append(result.text.strip())
            
            logger.debug(f"🔍 向量检索找到 {len(retrieved_texts)} 条相关内容")
            return retrieved_texts
            
        except Exception as e:
            logger.error(f"向量检索执行失败: {e}")
            return []
    
    def _extract_search_keywords(self, query: str) -> List[str]:
        """从查询中提取关键词"""
        # 去除停用词，提取有意义的词汇
        stopwords = {'的', '了', '和', '与', '及', '以及', '如何', '什么', '哪些', '怎样'}
        words = re.findall(r'[\u4e00-\u9fff]+', query)
        keywords = [word for word in words if len(word) > 1 and word not in stopwords]
        return keywords
    
    def _calculate_chunk_relevance(self, chunk: str, keywords: List[str]) -> float:
        """计算内容块与关键词的相关度"""
        score = 0
        chunk_lower = chunk.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in chunk_lower:
                # 计算关键词在文本中的密度
                count = chunk_lower.count(keyword_lower)
                score += count * len(keyword)  # 长关键词权重更高
        
        # 标准化分数
        return score / max(len(chunk), 1)
    
    async def _generate_customized_template(self, enriched_info: dict) -> Tuple[ReportStructure, MetricAnalysisTable]:
        """
        步骤三：基于标准绩效评价模板生成定制化内容
        """
        # 标准绩效评价报告结构（基于reportmodel.yaml）
        standard_sections = [
            {
                "title": "一、项目概述",
                "key": "overview",
                "prompt_template": "请围绕以下方面详细描述项目概况：1. 项目立项背景及目的、项目主要内容；2. 资金投入和使用情况、项目实施情况；3. 项目组织管理；4. 项目绩效目标：通过知识库搜索绩效目标表复制相关内容，务必以表格形式展示项目绩效指标"
            },
            {
                "title": "二、综合绩效评价结论",
                "key": "conclusion", 
                "prompt_template": "请基于对项目决策、过程、产出和效益四个维度的全面绩效分析，给出项目的综合评价结论。应包含项目总得分、评价等级，并务必以表格形式清晰展示各一级指标（决策、过程、产出、效益）的计划分值、实际得分和得分率"
            },
            {
                "title": "三、主要成效及经验",
                "key": "achievements",
                "prompt_template": "请详细总结项目实施过程中所取得的各项主要成效，需结合具体数据和事实进行阐述。同时，提炼出项目在政策执行、资金管理、部门协同、服务优化等方面可供其他地区或类似项目借鉴的成功经验和有效做法"
            },
            {
                "title": "四、存在的问题和原因分析",
                "key": "problems",
                "prompt_template": "请根据调研（如问卷调查、访谈）和数据分析，客观、准确地指出项目在实施过程中存在的主要问题。对于每个识别出的问题，都应深入剖析其产生的内外部原因"
            },
            {
                "title": "五、改进建议",
                "key": "suggestions",
                "prompt_template": "针对在'存在的问题和原因分析'部分指出的各项主要问题，请逐条提出具体的、有针对性的、可操作的改进建议。建议应明确改进方向、责任主体和预期效果"
            }
        ]
        
        # 基于项目信息定制内容描述
        customized_sections = await self._customize_section_content(standard_sections, enriched_info)
        
        # 生成标准指标体系
        metric_table = await self._generate_standard_metrics(enriched_info)
        
        # 构造ReportStructure
        sections = []
        for section_data in customized_sections:
            section = Section(
                section_title=section_data["title"],
                metric_ids=section_data.get("metric_ids", []),
                description_prompt=section_data["description_prompt"]
            )
            sections.append(section)
        
        project_name = enriched_info.get('project_name', '项目')
        report_structure = ReportStructure(
            title=f"{project_name}绩效评价报告",
            sections=sections
        )
        
        return report_structure, metric_table
    
    async def _customize_section_content(self, standard_sections: List[dict], enriched_info: dict) -> List[dict]:
        """
        定制化章节内容描述
        """
        customized_sections = []
        project_name = enriched_info.get('project_name', '项目')
        
        for section in standard_sections:
            # 基于项目信息调整prompt
            customized_prompt = await self._generate_section_prompt(section, enriched_info)
            
            customized_section = {
                "title": section["title"],
                "description_prompt": customized_prompt,
                "metric_ids": []
            }
            
            # 为"项目概述"章节添加指标关联
            if "概述" in section["title"]:
                customized_section["metric_ids"] = ["project_scope", "budget_execution", "target_completion"]
            elif "评价结论" in section["title"]:
                customized_section["metric_ids"] = ["overall_score", "decision_score", "process_score", "output_score", "benefit_score"]
                
            customized_sections.append(customized_section)
        
        return customized_sections
    
    async def _generate_section_prompt(self, section: dict, enriched_info: dict) -> str:
        """
        生成特定章节的写作指导prompt - 基于RAG证据给出具体检索指导
        """
        base_prompt = section["prompt_template"]
        project_name = enriched_info.get('project_name', '项目')
        section_title = section["title"]
        
        # 根据章节特点生成具体的RAG检索指导
        rag_instructions = await self._generate_chapter_rag_instructions(section_title, enriched_info)
        
        customized_prompt = f"""
针对{project_name}，{base_prompt}

### 📋 具体写作指导与检索要求：

{rag_instructions}

### 🔍 RAG检索策略：
写作时请严格按照以下步骤进行：
1. 首先检索上述关键信息项，获取具体数据和事实
2. 基于检索到的真实信息进行分析和论述
3. 避免泛泛而谈，确保每个论点都有具体的数据支撑
4. 如果某项信息检索不到，明确标注"信息待补充"

### 📊 质量要求：
- 数据准确：所有数字、时间、名称必须来自检索到的原始资料
- 逻辑清晰：按照检索指导的顺序组织内容结构
- 深度分析：不仅要列出事实，还要分析原因和影响
"""
        
        return customized_prompt
    
    async def _generate_chapter_rag_instructions(self, section_title: str, enriched_info: dict) -> str:
        """
        为每个章节生成具体的RAG检索指导
        """
        rag_evidence = enriched_info.get("rag_evidence", {})
        
        # 根据章节标题生成具体的检索指导
        if "项目概述" in section_title:
            instructions = f"""
**1. 项目立项背景及目的**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "项目背景与目标")}
   - 重点查找：政策文件引用、立项依据、目标设定
   
**2. 资金投入和使用情况**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "资金与预算")}
   - 重点查找：预算总额、资金来源、分配明细、执行进度
   
**3. 项目组织管理**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "实施方案")}
   - 重点查找：管理机构、职责分工、流程制度
   
**4. 项目绩效目标**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "效果与成效")}
   - 重点查找：绩效目标表、指标设定、预期成果（务必以表格形式展示）
"""
        elif "综合绩效评价结论" in section_title:
            instructions = f"""
**决策、过程、产出、效益四个维度分析**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "效果与成效")}
   - 重点查找：各项指标完成情况、评分结果、综合得分
   - 必须输出：指标得分情况表（一级指标、分值、得分、得分率）
"""
        elif "主要成效及经验" in section_title:
            instructions = f"""
**具体成效数据**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "效果与成效")}
   - 重点查找：量化成果数据、受益人群统计、效果对比
   
**成功经验总结**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "实施方案")}
   - 重点查找：创新做法、管理经验、技术亮点
"""
        elif "存在的问题和原因分析" in section_title:
            instructions = f"""
**问题识别**
   - 检索关键词：{self._get_evidence_summary(rag_evidence, "风险与挑战")}
   - 重点查找：调研发现的问题、数据反映的不足、反馈意见
   
**原因深度分析**
   - 检索关键词：政策执行、管理制度、技术条件、外部环境
   - 重点查找：问题产生的内在机制和外部因素
"""
        elif "改进建议" in section_title:
            instructions = f"""
**针对性建议**
   - 基于前述问题分析，检索关键词：{self._get_evidence_summary(rag_evidence, "风险与挑战")}
   - 重点查找：改进措施、政策建议、技术优化方案
   
**可操作性验证**
   - 检索关键词：成功案例、最佳实践、政策支持
   - 重点查找：类似项目的改进经验、政策可行性分析
"""
        else:
            # 通用指导
            instructions = f"""
**通用检索指导**
   - 优先检索：项目相关的具体数据、政策文件、实施效果
   - 重点关注：数量化指标、时间节点、责任主体、具体措施
"""
        
        return instructions
    
    def _get_evidence_summary(self, rag_evidence: dict, category: str) -> str:
        """
        获取特定类别的RAG证据摘要，用于指导检索
        """
        if category in rag_evidence and rag_evidence[category]:
            # 从证据中提取关键词作为检索指导
            evidence_text = " ".join(rag_evidence[category][:2])  # 取前2条证据
            # 简单提取关键概念
            keywords = []
            if "预算" in evidence_text or "资金" in evidence_text:
                keywords.append("预算资金数据")
            if "目标" in evidence_text or "指标" in evidence_text:
                keywords.append("目标指标设定")
            if "实施" in evidence_text or "管理" in evidence_text:
                keywords.append("实施管理措施")
            if "效果" in evidence_text or "成果" in evidence_text:
                keywords.append("实施效果数据")
            
            return ", ".join(keywords) if keywords else "相关项目信息"
        return "项目相关信息（待检索）"
    
    async def _generate_standard_metrics(self, enriched_info: dict) -> MetricAnalysisTable:
        """
        基于项目特点动态生成绩效指标体系
        一级指标固定为：决策、过程、产出、效益
        二级、三级指标根据项目特点由LLM动态生成
        """
        project_name = enriched_info.get('project_name', '项目')
        project_type = enriched_info.get('project_type', '财政支出项目')
        
        # 构造指标设计prompt
        metrics_design_prompt = f"""
你是绩效评价指标体系的架构师。请基于以下项目信息，设计一套完整的绩效评价指标体系。

项目信息：
{json.dumps(enriched_info, ensure_ascii=False, indent=2)}

指标体系设计要求：
1. 一级指标固定为：决策、过程、产出、效益（每个一级指标下需要2-3个二级指标）
2. 每个二级指标下设置1-2个三级指标
3. 分值分配：决策(25分)、过程(25分)、产出(25分)、效益(25分)
4. 指标要符合项目特点，具体、可衡量
5. 评分规则要明确、可操作
6. 评分过程要给出具体的评价方法指导

请返回JSON格式，每个指标包含：
- metric_id: 唯一标识（英文）
- name: 指标名称（中文）
- category: 指标分类
- 一级指标: "决策"/"过程"/"产出"/"效益"
- 二级指标: 具体的二级指标名称
- 三级指标: 具体的三级指标名称
- 分值: 数值（总计100分）
- 评分规则: 该指标的评价标准和要求
- 评分过程: 该指标的评价方法指导（告诉Writer如何进行评价）

示例格式：
[
  {{
    "metric_id": "project_necessity",
    "name": "项目立项必要性",
    "category": "决策指标",
    "一级指标": "决策",
    "二级指标": "立项决策",
    "三级指标": "立项必要性",
    "分值": 8.0,
    "评分规则": "评估项目立项的必要性和迫切性，是否符合政策导向和实际需求",
    "评分过程": "Writer需检查项目背景分析、需求调研报告、政策依据等材料的完整性和充分性进行评分"
  }}
]

请为{project_name}（{project_type}）设计8-12个指标，确保覆盖四个一级指标维度。
"""
        
        try:
            metrics_result = await self._aask(metrics_design_prompt)
            
            # 从LLM回复中提取JSON内容
            metrics_data = self._extract_json_from_llm_response(metrics_result)
            
            # 验证数据完整性和一级指标分布
            validated_metrics = self._validate_metrics_structure(metrics_data)
            
            logger.info(f"📊 动态生成了 {len(validated_metrics)} 个绩效指标")
            logger.info(f"📊 指标分布 - 决策:{self._count_metrics_by_level1(validated_metrics, '决策')}个, "
                       f"过程:{self._count_metrics_by_level1(validated_metrics, '过程')}个, "
                       f"产出:{self._count_metrics_by_level1(validated_metrics, '产出')}个, "
                       f"效益:{self._count_metrics_by_level1(validated_metrics, '效益')}个")
            
            return MetricAnalysisTable(data_json=json.dumps(validated_metrics, ensure_ascii=False))
            
        except Exception as e:
            logger.error(f"LLM指标生成失败，条件不足无法构建指标体系: {e}")
            # 不使用备用方案，直接返回空指标表示无法构建
            empty_metrics = {
                "error": "条件不足，无法构建指标体系",
                "reason": str(e),
                "suggestion": "请确保项目信息完整后重新生成"
            }
            return MetricAnalysisTable(data_json=json.dumps(empty_metrics, ensure_ascii=False))
    
    def _validate_metrics_structure(self, metrics_data: List[dict]) -> List[dict]:
        """
        验证指标数据结构的完整性
        """
        validated_metrics = []
        required_fields = ['metric_id', 'name', 'category', '一级指标', '二级指标', '三级指标', '分值', '评分规则', '评分过程']
        
        for metric in metrics_data:
            if all(field in metric for field in required_fields):
                # 确保一级指标只能是固定的四个值
                if metric['一级指标'] in ['决策', '过程', '产出', '效益']:
                    validated_metrics.append(metric)
                else:
                    logger.warning(f"指标 {metric.get('name', '未知')} 的一级指标不符合要求: {metric.get('一级指标', '')}")
            else:
                logger.warning(f"指标数据不完整: {metric}")
        
        return validated_metrics
    
    def _count_metrics_by_level1(self, metrics: List[dict], level1: str) -> int:
        """
        统计指定一级指标下的指标数量
        """
        return len([m for m in metrics if m.get('一级指标') == level1])
    
