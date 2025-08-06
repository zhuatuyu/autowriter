#!/usr/bin/env python
"""
架构师角色 - 报告结构设计和指标分析
"""
from metagpt.actions.design_api import WriteDesign
from metagpt.roles import Role  # 改为继承Role而不是RoleZero
from metagpt.schema import Message
from metagpt.logs import logger

from backend.actions.research_action import ConductComprehensiveResearch, ResearchData
from backend.actions.architect_action import DesignReportStructure as ArchitectAction, ArchitectOutput
from typing import List, Optional
import re

class Architect(Role):
    """
    Represents an Architect role in a software development process.
    """

    name: str = "Bob"
    profile: str = "Architect"
    goal: str = "Design a concise, usable, complete software system"
    constraints: str = "Try to specify good open source tools as much as possible"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 设置Action和监听 - 专注于消费ProductManager的研究成果
        self.set_actions([ArchitectAction])
        self._watch([ConductComprehensiveResearch])  # 监听ProductManager的输出
        
        # 用于存储向量知识库的引用
        self._current_research_data: Optional[ResearchData] = None

    def _semantic_search(self, query: str, research_data: ResearchData, top_k: int = 3) -> List[str]:
        """
        基于语义的向量检索（目前使用关键词匹配，后续可升级为真正的向量相似度检索）
        """
        if not research_data.content_chunks:
            logger.warning("向量知识库为空，无法进行检索")
            return []
        
        # 提取查询关键词
        query_keywords = self._extract_keywords(query)
        logger.info(f"🔍 检索关键词: {query_keywords}")
        
        # 计算每个内容块的相关度分数
        chunk_scores = []
        for i, chunk in enumerate(research_data.content_chunks):
            score = self._calculate_relevance_score(chunk, query_keywords)
            chunk_scores.append((i, score, chunk))
        
        # 按分数降序排序，取前top_k个
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        relevant_chunks = []
        
        for i, (chunk_idx, score, chunk) in enumerate(chunk_scores[:top_k]):
            if score > 0:  # 只返回有相关性的块
                relevant_chunks.append(chunk)
                logger.info(f"📋 相关块 {i+1} (分数: {score}): {chunk[:100]}...")
        
        return relevant_chunks
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取查询中的关键词"""
        # 简单的关键词提取，去掉常见停用词
        stopwords = {'的', '了', '在', '是', '和', '与', '或', '以及', '对于', '关于', '如何', '什么', '哪些'}
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', query)
        keywords = [word for word in words if len(word) > 1 and word not in stopwords]
        return keywords
    
    def _calculate_relevance_score(self, chunk: str, keywords: List[str]) -> float:
        """计算内容块与关键词的相关度分数"""
        score = 0
        chunk_lower = chunk.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # 精确匹配得分更高
            if keyword_lower in chunk_lower:
                count = chunk_lower.count(keyword_lower)
                score += count * 2  # 出现次数越多分数越高
        
        # 标准化分数
        return score / max(len(chunk), 1)

    async def _act(self) -> Message:
        """执行架构设计任务"""
        logger.info(f"🏗️ {self.name} (Architect) 开始执行架构设计任务...")
        
        # 添加调试信息
        memories = self.get_memories()
        logger.info(f"📝 Architect 检查到 {len(memories)} 条消息历史")
        for i, msg in enumerate(memories):
            logger.info(f"  消息 {i}: cause_by={msg.cause_by}, role={msg.role}")
        
        
        # 获取ProductManager的研究数据 - 完整获取包括向量知识库
        research_data_obj = None
        research_brief = ""
        
        for msg in self.get_memories():
            logger.info(f"🔍 检查消息: cause_by={msg.cause_by}, 类型={type(msg.cause_by)}")
            if str(msg.cause_by).endswith("ConductComprehensiveResearch"):
                logger.info(f"✅ 找到匹配的ProductManager消息!")
                # 正确解析instruct_content中的ResearchData对象
                if hasattr(msg, 'instruct_content') and msg.instruct_content:
                    try:
                        # 优先处理ResearchData对象
                        if isinstance(msg.instruct_content, ResearchData):
                            research_data_obj = msg.instruct_content
                            research_brief = research_data_obj.brief
                            self._current_research_data = research_data_obj
                            logger.info(f"📊 获取到完整ResearchData，包含 {len(research_data_obj.content_chunks)} 个向量块")
                        elif hasattr(msg.instruct_content, 'brief'):
                            research_brief = msg.instruct_content.brief
                            # 尝试构造ResearchData对象
                            if hasattr(msg.instruct_content, 'content_chunks'):
                                research_data_obj = msg.instruct_content
                                self._current_research_data = research_data_obj
                        elif isinstance(msg.instruct_content, dict):
                            research_brief = msg.instruct_content.get('brief', '')
                            # 尝试从字典构造ResearchData
                            if 'content_chunks' in msg.instruct_content:
                                research_data_obj = ResearchData(**msg.instruct_content)
                                self._current_research_data = research_data_obj
                        else:
                            # 如果instruct_content不是预期格式，尝试从content获取
                            research_brief = msg.content
                    except Exception as e:
                        logger.error(f"解析研究数据失败: {e}")
                        research_brief = msg.content
                break
        
        if not research_brief:
            logger.error("❌ 未找到有效的研究数据！无法进行架构设计")
            raise ValueError("未找到有效的研究数据，无法进行架构设计。请确保ProductManager已完成研究")
        
        logger.info(f"📄 成功获取研究简报，长度: {len(research_brief)} 字符")
        if self._current_research_data:
            logger.info(f"🧠 向量知识库可用，包含 {len(self._current_research_data.content_chunks)} 个内容块")
        
        # 执行报告结构设计 - 利用向量检索增强设计
        todo = self.rc.todo
        if isinstance(todo, ArchitectAction):
            # 【新增】如果有向量知识库，进行RAG增强设计
            enhanced_research_context = research_brief
            
            if self._current_research_data and self._current_research_data.content_chunks:
                logger.info("🔍 启动RAG增强的报告结构设计...")
                
                # 针对报告结构设计进行多角度检索
                design_queries = [
                    "报告结构 章节划分 目录大纲",
                    "关键指标 评价指标 绩效指标",
                    "数据分析 技术方案 实施方法",
                    "风险挑战 问题建议 解决方案"
                ]
                
                rag_context = "\n\n### RAG检索增强内容\n\n"
                
                for i, query in enumerate(design_queries, 1):
                    relevant_chunks = self._semantic_search(query, self._current_research_data, top_k=2)
                    if relevant_chunks:
                        rag_context += f"#### 检索维度 {i}: {query}\n"
                        for j, chunk in enumerate(relevant_chunks, 1):
                            rag_context += f"**相关内容 {j}:**\n{chunk}\n\n"
                
                # 将RAG检索结果与原始研究简报结合
                enhanced_research_context = research_brief + rag_context
                logger.info(f"✅ RAG增强完成，增强后内容长度: {len(enhanced_research_context)} 字符")
            
            # DesignReportStructure返回Tuple[ReportStructure, MetricAnalysisTable]
            # 传递research_data参数到新的Action
            report_structure, metric_table = await todo.run(enhanced_research_context, research_data=self._current_research_data)
            
            # 保存ReportStructure到文件
            if hasattr(self, '_project_repo') and self._project_repo:
                try:
                    # 保存报告结构
                    structure_content = f"# 报告结构设计\n\n## 报告标题\n{report_structure.title}\n\n"
                    structure_content += "## 章节结构\n\n"
                    for i, section in enumerate(report_structure.sections, 1):
                        structure_content += f"### {i}. {section.section_title}\n"
                        structure_content += f"**关联指标**: {', '.join(section.metric_ids)}\n"
                        structure_content += f"**写作要点**: {section.description_prompt}\n\n"
                    
                    await self._project_repo.docs.save(
                        filename="report_structure.md", 
                        content=structure_content
                    )
                    logger.info(f"报告结构已保存到: {self._project_repo.docs.workdir}/report_structure.md")
                    
                    # 保存指标分析表
                    import json
                    metric_data = json.loads(metric_table.data_json)
                    metric_content = f"# 指标分析表\n\n```json\n{json.dumps(metric_data, ensure_ascii=False, indent=2)}\n```"
                    
                    await self._project_repo.docs.save(
                        filename="metric_analysis_table.md", 
                        content=metric_content
                    )
                    logger.info(f"指标分析表已保存到: {self._project_repo.docs.workdir}/metric_analysis_table.md")
                    
                except Exception as e:
                    logger.error(f"保存Architect输出文件失败: {e}")
            
            # 创建包含ReportStructure的消息，供ProjectManager使用
            # 创建复合输出对象，按照原生MetaGPT模式
            architect_output = ArchitectOutput(
                report_structure=report_structure,
                metric_analysis_table=metric_table
            )
            
            # 输出更详细的完成信息
            content_msg = f"📋 报告结构设计完成：{report_structure.title}，共{len(report_structure.sections)}个章节"
            if self._current_research_data:
                content_msg += f"；✨ 使用RAG增强设计（基于{len(self._current_research_data.content_chunks)}个向量块）"
            content_msg += "；📊 指标分析表生成完成"
            
            msg = Message(
                content=content_msg,
                role=self.profile,
                cause_by=type(todo),
                sent_from=self,
                instruct_content=architect_output  # 直接传递Pydantic对象，像原生代码一样
            )
            
            self.rc.memory.add(msg)
            return msg
        else:
            # 如果不是DesignReportStructure，使用原有逻辑
            result = await todo.run(research_brief)
            
            msg = Message(
                content=result,
                role=self.profile,
                cause_by=type(todo),
                sent_from=self,
            )
            
            self.rc.memory.add(msg)
            return msg