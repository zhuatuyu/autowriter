#!/usr/bin/env python
"""
架构师角色 - 报告结构设计和指标分析
"""
from metagpt.roles import Role  # 改为继承Role而不是RoleZero
from metagpt.schema import Message
from metagpt.logs import logger

from backend.actions.research_action import ConductComprehensiveResearch, ResearchData
from backend.actions.architect_action import DesignReportStructure as ArchitectAction, ArchitectOutput
from typing import List, Optional

class Architect(Role):
    """
    Represents an Architect role in a software development process.
    """

    name: str = "架构专家"
    profile: str = "Architect"
    goal: str = "构建完整的报告结构和指标体系"
    constraints: str = "充分理解前期产品经理的各类研究报告,确保报告整体结构合理，指标体系完整，逻辑清晰，有利于后续写作专家在结构基础上完成内容和具体指标的评价意见编写"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 设置Action和监听 - 专注于消费ProductManager的研究成果
        self.set_actions([ArchitectAction])
        self._watch([ConductComprehensiveResearch])  # 监听ProductManager的输出
        
        # 用于存储向量知识库的引用
        self._current_research_data: Optional[ResearchData] = None
        # 注入的项目信息（由上层Company在启动前设置）
        self._project_info: Optional[dict] = None

    def set_project_info(self, project_info: dict) -> None:
        """由上层注入项目信息，供Architect的Action消费"""
        self._project_info = project_info or {}

    async def _semantic_search(self, query: str, research_data: ResearchData, top_k: int = 3) -> List[str]:
        """通过统一的智能检索服务进行语义检索（配置驱动）。"""
        try:
            from backend.services.intelligent_search import intelligent_search
            result = await intelligent_search.intelligent_search(
                query=query,
                project_vector_storage_path=getattr(research_data, 'vector_store_path', ''),
                mode="hybrid",
                enable_global=True,
                max_results=top_k,
            )
            return result.get("results", [])
        except Exception as e:
            logger.warning(f"语义检索失败: {e}")
            return []
    

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
                            logger.info("📊 获取到完整ResearchData（含向量库路径）")
                        elif hasattr(msg.instruct_content, 'brief'):
                            research_brief = msg.instruct_content.brief
                            # 尝试构造ResearchData对象（优先vector_store_path）
                            if hasattr(msg.instruct_content, 'vector_store_path'):
                                research_data_obj = msg.instruct_content
                                self._current_research_data = research_data_obj
                        elif isinstance(msg.instruct_content, dict):
                            research_brief = msg.instruct_content.get('brief', '')
                            # 尝试从字典构造ResearchData（优先vector_store_path）
                            if 'vector_store_path' in msg.instruct_content:
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
        if self._current_research_data and getattr(self._current_research_data, 'vector_store_path', ''):
            logger.info("🧠 检测到项目向量知识库路径，可用于RAG增强")
        
        # 执行报告结构设计 - 利用向量检索增强设计
        todo = self.rc.todo
        if isinstance(todo, ArchitectAction):
            # 【新增】如果有向量知识库，进行RAG增强设计
            enhanced_research_context = research_brief
            
            if self._current_research_data and getattr(self._current_research_data, 'vector_store_path', ''):
                logger.info("🔍 启动RAG增强的报告结构设计...")
                
                # 通过配置驱动的设计检索维度
                from backend.config.performance_constants import ENV_DESIGN_QUERIES
                design_queries = ENV_DESIGN_QUERIES or []
                
                if design_queries:
                    rag_context = "\n\n### RAG检索增强内容\n\n"
                    for i, query in enumerate(design_queries, 1):
                        try:
                            items = await self._semantic_search(query, self._current_research_data, top_k=2)
                            if items:
                                rag_context += f"#### 检索维度 {i}: {query}\n"
                                for j, chunk in enumerate(items, 1):
                                    rag_context += f"**相关内容 {j}:**\n{chunk}\n\n"
                        except Exception as e:
                            logger.warning(f"设计检索维度查询失败: {query}, {e}")
                    # 将RAG检索结果与原始研究简报结合
                    enhanced_research_context = research_brief + rag_context
                    logger.info(f"✅ RAG增强完成，增强后内容长度: {len(enhanced_research_context)} 字符")
            
            # DesignReportStructure返回Tuple[ReportStructure, MetricAnalysisTable]
            # 在调用前将项目信息注入Action，并作为参数传入
            try:
                if hasattr(self, "_project_info") and self._project_info and hasattr(todo, "set_project_info"):
                    todo.set_project_info(self._project_info)
            except Exception as e:
                logger.warning(f"向Action注入项目信息失败: {e}")

            # 若无向量库路径则直接按简报进行非RAG结构设计，避免阻断
            if not (self._current_research_data and getattr(self._current_research_data, 'vector_store_path', '')):
                logger.warning("⚠️ 未检测到项目向量库路径，将跳过RAG增强，直接基于研究简报进行结构设计。")
                enhanced_research_context = research_brief

            report_structure, metric_table = await todo.run(
                enhanced_research_context,
                research_data=self._current_research_data,
                project_info=self._project_info,
            )
            
            # 保存ReportStructure到文件
            if hasattr(self, '_project_repo') and self._project_repo:
                try:
                    # 保存报告结构
                    structure_content = f"# 报告结构设计\n\n## 报告标题\n{report_structure.title}\n\n"
                    structure_content += "## 章节结构\n\n"
                    for i, section in enumerate(report_structure.sections, 1):
                        structure_content += f"### {i}. {section.section_title}\n"
                        # 章节与指标动态解耦后，不再展示固定的关联指标列表
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
            if self._current_research_data and getattr(self._current_research_data, 'vector_store_path', ''):
                content_msg += "；✨ 使用RAG增强设计"
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