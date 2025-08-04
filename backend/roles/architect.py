#!/usr/bin/env python
"""
架构师角色 - 报告结构设计和指标分析
"""
from metagpt.actions.design_api import WriteDesign
from metagpt.roles import Role  # 改为继承Role而不是RoleZero
from metagpt.schema import Message
from metagpt.logs import logger

from backend.actions.research_action import ConductComprehensiveResearch, ResearchData
from backend.actions.architect_action import DesignReportStructure as ArchitectAction

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

    async def _act(self) -> Message:
        """执行架构设计任务"""
        logger.info(f"🏗️ {self.name} (Architect) 开始执行架构设计任务...")
        
        # 添加调试信息
        memories = self.get_memories()
        logger.info(f"📝 Architect 检查到 {len(memories)} 条消息历史")
        for i, msg in enumerate(memories):
            logger.info(f"  消息 {i}: cause_by={msg.cause_by}, role={msg.role}")
        
        
        # 获取ProductManager的研究数据 - 修复bug: 从instruct_content获取而不是content
        research_data_obj = None
        research_brief = ""
        
        for msg in self.get_memories():
            logger.info(f"🔍 检查消息: cause_by={msg.cause_by}, 类型={type(msg.cause_by)}")
            if str(msg.cause_by).endswith("ConductComprehensiveResearch"):
                logger.info(f"✅ 找到匹配的ProductManager消息!")
                # 正确解析instruct_content中的ResearchData对象
                if hasattr(msg, 'instruct_content') and msg.instruct_content:
                    try:
                        # 处理instruct_content (可能是ResearchData对象或动态生成的对象)
                        if hasattr(msg.instruct_content, 'brief'):
                            research_brief = msg.instruct_content.brief
                        elif isinstance(msg.instruct_content, dict) and 'brief' in msg.instruct_content:
                            research_brief = msg.instruct_content['brief']
                        elif isinstance(msg.instruct_content, ResearchData):
                            research_data_obj = msg.instruct_content
                            research_brief = research_data_obj.brief
                        else:
                            # 如果instruct_content不是预期格式，尝试从content获取
                            research_brief = msg.content
                    except Exception as e:
                        logger.error(f"解析研究数据失败: {e}")
                        research_brief = msg.content
                break
        
        if not research_brief:
            research_brief = "No research data available"
            logger.warning("未找到有效的研究数据，使用默认值")
        
        logger.info(f"成功获取研究简报，长度: {len(research_brief)} 字符")
        
        # 执行报告结构设计
        todo = self.rc.todo
        if isinstance(todo, ArchitectAction):
            # DesignReportStructure返回Tuple[ReportStructure, MetricAnalysisTable]
            report_structure, metric_table = await todo.run(research_brief)
            
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
            msg = Message(
                content=f"报告结构设计完成：{report_structure.title}，共{len(report_structure.sections)}个章节",
                role=self.profile,
                cause_by=type(todo),
                sent_from=self,
                instruct_content=Message.create_instruct_value(report_structure.model_dump())
            )
            
            # 也需要保存MetricAnalysisTable供WriterExpert使用
            metric_msg = Message(
                content=f"指标分析表生成完成",
                role=self.profile,
                cause_by=type(todo),
                sent_from=self,
                instruct_content=Message.create_instruct_value(metric_table.model_dump())
            )
            
            self.rc.memory.add(msg)
            self.rc.memory.add(metric_msg)
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