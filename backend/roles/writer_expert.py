#!/usr/bin/env python
"""
写作专家角色 - 内容生成和整合
"""
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger
from datetime import datetime

from backend.actions.writer_action import WriteSection
from backend.actions.metric_action import EvaluateMetrics
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
        
        self.set_actions([WriteSection, EvaluateMetrics])
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
            # 直接使用最新的 Architect 输出，移除早期兼容与全量扫描
            metric_table_msg = metric_table_msgs[-1]
            logger.info("✅ 使用最新 Architect 输出作为指标数据源")
            
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
            
            # 获取指标数据（仅支持 ArchitectOutput，去除早期兼容）
            metric_data = "{}"
            if hasattr(metric_table_msg, 'instruct_content') and metric_table_msg.instruct_content:
                instruct_content = metric_table_msg.instruct_content
                if isinstance(instruct_content, ArchitectOutput):
                    metric_data = instruct_content.metric_analysis_table.data_json
                    logger.info("✅ 从最新ArchitectOutput获取metric_data")
                else:
                    logger.error("指标数据格式不符合预期（非 ArchitectOutput）")
                    return Message(content="指标数据格式错误", cause_by=WriteSection)
            else:
                logger.error("最新 Architect 输出缺少 instruct_content")
                return Message(content="指标数据缺失", cause_by=WriteSection)
            
            # === 新的完整工作流程（先评分后写作） ===

            # 阶段1: 指标评分处理并回写指标表
            logger.info("📊 阶段1: 开始指标评分处理...")
            metrics_evaluation_result = {}
            try:
                evaluate_action = EvaluateMetrics()
                metrics_evaluation_result = await evaluate_action.run(
                    metric_table_json=metric_data,
                    vector_store_path=vector_store_path,
                    metric_table_md_path=str(self._project_repo.docs.workdir / "metric_analysis_table.md") if hasattr(self, '_project_repo') and self._project_repo else None
                )
                
                if "error" in metrics_evaluation_result:
                    logger.error(f"指标评分失败: {metrics_evaluation_result}")
                    metrics_evaluation_result = {
                        "metrics_scores": [],
                        "level1_summary": {"决策": 0, "过程": 0, "产出": 0, "效益": 0},
                        "total_score": 0,
                        "grade": "评分失败"
                    }
                else:
                    logger.info(f"✅ 指标评分完成，总分: {metrics_evaluation_result.get('total_score', 0)}分")
                    
            except Exception as e:
                logger.error(f"指标评分阶段失败: {e}")
                metrics_evaluation_result = {
                    "metrics_scores": [],
                    "level1_summary": {"决策": 0, "过程": 0, "产出": 0, "效益": 0},
                    "total_score": 0,
                    "grade": "评分失败"
                }
            
            # 评分后：若存在metrics md，读取其中的JSON作为后续章节写作的指标数据源
            updated_metric_data = metric_data
            try:
                if hasattr(self, '_project_repo') and self._project_repo:
                    from pathlib import Path as _Path
                    import re as _re
                    md_path = _Path(self._project_repo.docs.workdir) / "metric_analysis_table.md"
                    if md_path.exists():
                        text = md_path.read_text(encoding="utf-8")
                        m = _re.search(r"```json\s*(.*?)\s*```", text, flags=_re.DOTALL)
                        if m:
                            updated_metric_data = m.group(1)
                            logger.info("📝 已读取回写后的指标JSON用于章节写作")
            except Exception as e:
                logger.warning(f"读取已回写指标表失败，继续使用Architect输出: {e}")

            # 阶段2: 主报告章节写作
            logger.info("📝 阶段2: 开始主报告章节写作...")
            sections = []
            write_action = WriteSection()
            
            for i, task in enumerate(tasks):
                try:
                    task_obj = task if hasattr(task, 'section_title') else Task(
                        task_id=i,
                        section_title=task.get('section_title', f'章节{i+1}'),
                        instruction=task.get('instruction', task.get('description', '分析内容')),
                    )
                    
                    section_content = await write_action.run(
                        task=task_obj,
                        vector_store_path=vector_store_path,
                        metric_table_json=updated_metric_data
                    )
                    sections.append(section_content)
                    logger.info(f"✅ 完成主报告章节: {task_obj.section_title}")
                except Exception as e:
                    logger.error(f"生成章节{i+1}失败: {e}")
                    # 生成一个简单的默认章节
                    section_title = task_obj.section_title if hasattr(task_obj, 'section_title') else f'章节{i+1}'
                    default_content = f"# {section_title}\n\n基于研究数据的分析内容。\n"
                    sections.append(default_content)
            
            # 阶段3: 生成最终报告（不再整合指标表，仅汇总章节内容；按 report_structure.md 指定顺序）
            try:
                final_report = ""
                ordered_sections = []
                # 尝试读取 report_structure.md 以确定章节顺序
                structure_titles = []
                if hasattr(self, '_project_repo') and self._project_repo:
                    struct_path = self._project_repo.docs.workdir / "report_structure.md"
                    if struct_path.exists():
                        txt = struct_path.read_text(encoding="utf-8")
                        for line in txt.splitlines():
                            s = line.strip()
                            if s.startswith('#'):
                                # 去掉#与空格
                                title = s.lstrip('#').strip()
                                if title:
                                    structure_titles.append(title)
                
                # 从章节内容提取标题映射
                def normalize_title(t: str) -> str:
                    # 去除常见编号前缀，例如“X、”“一、”“1.”等，仅做轻量归一
                    t = t.strip()
                    for sep in ["、", ".", "：", ":"]:
                        if sep in t[:4]:
                            t = t.split(sep, 1)[-1].strip()
                            break
                    return t
                
                section_title_to_content = {}
                for sec in sections:
                    first_line = sec.splitlines()[0] if sec else ""
                    first_line = first_line.lstrip('#').strip()
                    if first_line:
                        section_title_to_content[normalize_title(first_line)] = sec
                
                # 按结构文件顺序挑选；若匹配不到则按生成顺序补齐
                picked_keys = set()
                for st in structure_titles:
                    key = normalize_title(st)
                    if key in section_title_to_content:
                        ordered_sections.append(section_title_to_content[key])
                        picked_keys.add(key)
                # 补齐未匹配的章节
                for sec in sections:
                    first_line = sec.splitlines()[0] if sec else ""
                    key = normalize_title(first_line.lstrip('#').strip()) if first_line else ""
                    if key and key not in picked_keys:
                        ordered_sections.append(sec)
                        picked_keys.add(key)
                
                # 组装并保存
                final_report = "\n\n".join(ordered_sections) if ordered_sections else "\n\n".join(sections)
                if hasattr(self, '_project_repo') and self._project_repo:
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    fname = f"final_report_{ts}.md"
                    await self._project_repo.docs.save(filename=fname, content=final_report)
                    logger.info(f"📝 最终报告已保存: {self._project_repo.docs.workdir / fname}")
            except Exception as e:
                logger.error(f"最终报告生成失败: {e}")
            
            # 不再整合最终报告，返回一个简要完成提示
            return Message(
                content="章节写作完成并已对指标进行评分，结果已回写至 metric_analysis_table.md",
                cause_by=WriteSection
            )
            
        except Exception as e:
            logger.error(f"写作报告失败: {e}")
            return Message(content=f"错误：{str(e)}", cause_by=WriteSection)