#!/usr/bin/env python
"""
写作专家角色 - 内容生成和整合
"""
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

from backend.actions.writer_action import WriteSection, IntegrateReport
from backend.actions.pm_action import CreateTaskPlan, TaskPlan, Task
from backend.actions.research_action import ConductComprehensiveResearch, ResearchData
from backend.actions.architect_action import DesignReportStructure as ArchitectAction, MetricAnalysisTable, ArchitectOutput


class WriterExpert(Role):
    """
    写作专家 - 专注的内容创作者
    """
    name: str = "写作专家"
    profile: str = "Writer Expert"
    goal: str = "基于任务计划和研究数据生成高质量的报告内容"
    constraints: str = "必须充分利用RAG检索和指标数据，确保内容的准确性和专业性"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_actions([WriteSection, IntegrateReport])
        self._watch([CreateTaskPlan, ConductComprehensiveResearch, ArchitectAction])

    async def _act(self) -> Message:
        """
        执行WriterExpert的核心逻辑
        """
        logger.info("📝 WriterExpert开始执行写作任务...")
        
        # 检查是否有所有必需的数据 - 从instruct_content获取
        task_plan_msgs = self.rc.memory.get_by_action(CreateTaskPlan)
        research_data_msgs = self.rc.memory.get_by_action(ConductComprehensiveResearch)  
        metric_table_msgs = self.rc.memory.get_by_action(ArchitectAction)
        
        logger.info(f"检查数据: TaskPlan={len(task_plan_msgs) if task_plan_msgs else 0}, "
                   f"ResearchData={len(research_data_msgs) if research_data_msgs else 0}, "
                   f"MetricTable={len(metric_table_msgs) if metric_table_msgs else 0}")
        
        if not all([task_plan_msgs, research_data_msgs, metric_table_msgs]):
            logger.warning("等待所有必需数据...")
            return Message(content="等待数据中...", cause_by=WriteSection)
        
        try:
            # 解析所有数据 - 从instruct_content获取
            task_plan_msg = task_plan_msgs[-1]
            research_data_msg = research_data_msgs[-1]
            metric_table_msg = None
            
            # 寻找包含MetricAnalysisTable的消息（现在和ReportStructure合并在一起）
            memories = self.get_memories()
            logger.info(f"🔍 开始搜索MetricAnalysisTable，总消息数: {len(memories)}")
            
            for i, msg in enumerate(memories):
                logger.info(f"消息 {i}: cause_by={msg.cause_by}, has_instruct_content={hasattr(msg, 'instruct_content')}")
                if hasattr(msg, 'instruct_content') and msg.instruct_content:
                    logger.info(f"消息 {i} instruct_content类型: {type(msg.instruct_content)}")
                    # 按照原生MetaGPT模式检查ArchitectOutput
                    if isinstance(msg.instruct_content, ArchitectOutput):
                        logger.info(f"消息 {i} 找到ArchitectOutput对象!")
                        metric_table_msg = msg
                        logger.info(f"✅ 找到ArchitectOutput数据: {type(msg.instruct_content)}")
                        break
                    # 检查动态生成的对象
                    elif hasattr(msg.instruct_content, 'metric_analysis_table'):
                        logger.info(f"消息 {i} 找到包含metric_analysis_table的对象!")
                        metric_table_msg = msg
                        logger.info(f"✅ 找到MetricAnalysisTable数据: {type(msg.instruct_content)}")
                        break
                    # 保持向后兼容性 - 检查直接的data_json
                    elif hasattr(msg.instruct_content, 'data_json'):
                        logger.info(f"消息 {i} 找到data_json属性!")
                        metric_table_msg = msg
                        logger.info(f"✅ 找到MetricAnalysisTable数据: {type(msg.instruct_content)}")
                        break
                    elif isinstance(msg.instruct_content, dict) and 'data_json' in msg.instruct_content:
                        logger.info(f"消息 {i} 在字典中找到data_json键!")
                        metric_table_msg = msg
                        logger.info(f"✅ 找到MetricAnalysisTable数据: {type(msg.instruct_content)}")
                        break
                    else:
                        logger.info(f"消息 {i} instruct_content内容: {str(msg.instruct_content)[:200]}...")
            
            if not metric_table_msg:
                logger.warning("未找到MetricAnalysisTable数据")
                return Message(content="等待指标数据...", cause_by=WriteSection)
            
            # 获取实际数据
            if hasattr(task_plan_msg, 'instruct_content') and task_plan_msg.instruct_content:
                task_plan = task_plan_msg.instruct_content
            else:
                logger.warning("TaskPlan数据格式不正确")
                return Message(content="任务计划数据格式错误", cause_by=WriteSection)
                
            if hasattr(research_data_msg, 'instruct_content') and research_data_msg.instruct_content:
                research_data = research_data_msg.instruct_content  
            else:
                research_brief = research_data_msg.content
                research_data = {"brief": research_brief}
            
            # 处理task_plan数据
            if hasattr(task_plan, 'tasks'):
                tasks = task_plan.tasks
                title = getattr(task_plan, 'title', '绩效分析报告')
            elif isinstance(task_plan, dict) and 'tasks' in task_plan:
                tasks = task_plan['tasks']
                title = task_plan.get('title', '绩效分析报告')
            else:
                # 如果没有找到tasks，创建一个默认的任务
                logger.warning("未找到有效的task_plan，使用默认任务")
                tasks = [{"section_title": "综合分析", "description": "基于研究数据的综合分析"}]
                title = "绩效分析报告"
            
            logger.info(f"开始写作报告：{title}，共 {len(tasks)} 个章节")
            
            # 获取研究数据路径
            vector_store_path = None
            if hasattr(research_data, 'vector_store_path'):
                vector_store_path = research_data.vector_store_path
            elif isinstance(research_data, dict):
                vector_store_path = research_data.get('vector_store_path')
            
            # 获取指标数据
            metric_data = "{}"  # 默认空JSON
            if hasattr(metric_table_msg, 'instruct_content') and metric_table_msg.instruct_content:
                instruct_content = metric_table_msg.instruct_content
                
                # 按照原生MetaGPT模式处理ArchitectOutput
                if isinstance(instruct_content, ArchitectOutput):
                    metric_data = instruct_content.metric_analysis_table.data_json
                    logger.info(f"✅ 从ArchitectOutput获取metric_data")
                # 处理动态生成的对象
                elif hasattr(instruct_content, 'metric_analysis_table'):
                    metric_table = instruct_content.metric_analysis_table
                    if hasattr(metric_table, 'data_json'):
                        metric_data = metric_table.data_json
                        logger.info(f"✅ 从动态对象获取metric_data")
                    else:
                        metric_data = str(metric_table)
                        logger.info(f"✅ 从动态对象获取metric_data (字符串格式)")
                # 保持向后兼容性
                elif hasattr(instruct_content, 'data_json'):
                    metric_data = instruct_content.data_json
                    logger.info(f"✅ 从直接data_json属性获取metric_data")
                elif isinstance(instruct_content, dict) and 'data_json' in instruct_content:
                    metric_data = instruct_content['data_json']
                    logger.info(f"✅ 从字典data_json键获取metric_data")
                elif isinstance(instruct_content, dict):
                    metric_data = str(instruct_content)
                    logger.info(f"✅ 使用整个字典作为metric_data")
            
            # 为每个任务生成章节内容
            sections = []
            write_action = WriteSection()
            
            for i, task in enumerate(tasks):
                try:
                    task_obj = task if hasattr(task, 'section_title') else Task(
                        section_title=task.get('section_title', f'章节{i+1}'),
                        description=task.get('description', '分析内容')
                    )
                    
                    section_content = await write_action.run(
                        task=task_obj,
                        vector_store_path=vector_store_path,
                        metric_table_json=metric_data
                    )
                    sections.append(section_content)
                    logger.info(f"完成章节: {task_obj.section_title}")
                except Exception as e:
                    logger.error(f"生成章节{i+1}失败: {e}")
                    # 生成一个简单的默认章节
                    default_content = f"# {task.get('section_title', f'章节{i+1}')}\n\n基于研究数据的分析内容。\n"
                    sections.append(default_content)
            
            # 整合最终报告
            integrate_action = IntegrateReport()
            final_report = await integrate_action.run(
                sections=sections,
                report_title=title
            )
            
            # 保存最终报告到文件
            if hasattr(self, '_project_repo') and self._project_repo:
                try:
                    await self._project_repo.docs.save(
                        filename="final_report.md",
                        content=final_report
                    )
                    logger.info(f"最终报告已保存到: {self._project_repo.docs.workdir}/final_report.md")
                except Exception as e:
                    logger.error(f"保存最终报告失败: {e}")
            
            return Message(
                content=final_report,
                cause_by=IntegrateReport
            )
            
        except Exception as e:
            logger.error(f"写作报告失败: {e}")
            return Message(content=f"错误：{str(e)}", cause_by=WriteSection)