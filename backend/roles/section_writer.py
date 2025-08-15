#!/usr/bin/env python
"""
SectionWriter - 章节写作专家（SOP2）
"""
import json
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger
from datetime import datetime

from backend.actions.section_writer_action import WriteSection
from backend.actions.project_manager_action import Task
from backend.actions.architect_content_action import DesignReportStructureOnly as ArchitectAction


class SectionWriter(Role):
    name: str = "章节写作专家"
    profile: str = "SectionWriter"
    goal: str = "按结构生成章节并聚合为最终报告"
    constraints: str = "严格遵循结构顺序，不包含指标表"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([WriteSection])
        # 仅监听架构师结构消息；也支持无消息时从本地路径直接读取结构
        self._watch([ArchitectAction])
        self._project_repo = None
        self._last_structure_hash = None

    async def _act(self) -> Message:
        # 直接读取并解析 report_structure.json
        from pathlib import Path
        structure_path = self._project_repo.docs.workdir / "report_structure.json" if hasattr(self, "_project_repo") and self._project_repo else Path("workspace/project01/docs/report_structure.json")
        if not structure_path.exists():
            logger.warning("SectionWriter: 未找到 report_structure.json，跳过写作")
            return Message(content="缺少报告结构，跳过写作", cause_by=WriteSection)

        try:
            # 读取JSON文件
            with open(structure_path, 'r', encoding='utf-8') as f:
                structure_data = json.load(f)
            
            # 计算内容哈希用于幂等控制
            content_str = json.dumps(structure_data, sort_keys=True, ensure_ascii=False)
            new_hash = str(hash(content_str))
            if self._last_structure_hash and new_hash == self._last_structure_hash:
                logger.info("SectionWriter: 结构未变化，跳过重复写作。")
                return Message(content="结构未变化，跳过写作", cause_by=WriteSection)
            self._last_structure_hash = new_hash

            # 从JSON中提取任务信息
            sections = structure_data.get('sections', [])
            tasks = []
            for section in sections:
                # 构建写作指导文本
                writing_guidance = f"{section.get('description_prompt', '')}\n\n"
                if section.get('rag_instructions'):
                    writing_guidance += f"### 📋 具体写作指导与引用要求（不进行外部检索）：\n{section.get('rag_instructions')}\n\n"
                
                fact_reqs = section.get('fact_requirements', {})
                if fact_reqs:
                    writing_guidance += "### 🔍 事实引用与一致性要求：\n"
                    writing_guidance += f"1. 仅使用{', '.join(fact_reqs.get('data_sources', []))}为事实来源，不要发起任何外部检索\n"
                    writing_guidance += "2. 每个关键论点需可追溯到具体来源（简报键名/案例标题/指标名称）\n"
                    fallback_msg = fact_reqs.get('fallback_instruction', '如缺失信息，标注 "信息待补充"，避免臆测')
                    writing_guidance += f"3. {fallback_msg}\n"
                    consistency_msg = fact_reqs.get('consistency_requirement', '确保表述与事实一致，避免过度延展')
                    writing_guidance += f"4. {consistency_msg}\n"
                
                tasks.append({
                    "section_title": section.get('section_title', ''),
                    "instruction": writing_guidance.strip(),
                    "section_id": section.get('section_id', 0),
                    "writing_sequence_order": section.get('writing_sequence_order', 0)
                })
            
            # 按写作顺序排序
            tasks.sort(key=lambda x: x.get('writing_sequence_order', 0))
            
            logger.info(f"SectionWriter: 解析JSON结构成功，章节数: {len(tasks)}")
        except Exception as e:
            logger.error(f"SectionWriter: 解析 report_structure.json 失败: {e}")
            return Message(content="解析结构失败", cause_by=WriteSection)
        
        # 章节写作不再注入指标表或触发检索：仅消费研究简报与网络案例摘录

        # 写作
        sections = []
        write_action = WriteSection()
        # 注入 ProjectRepo，供写作Action读取 docs/resources（研究简报与网络案例）
        write_action._project_repo = self._project_repo
        vector_store_path = None  # 不使用RAG
        # tasks 已在上方判空
        
        logger.info(f"SectionWriter: 开始写作 {len(tasks)} 个章节")
        
        for i, task in enumerate(tasks):
            task_obj = Task(
                task_id=i,
                section_title=task.get('section_title', f'章节{i+1}'),
                instruction=task.get('instruction', task.get('description', '分析内容')),
            )
            
            logger.info(f"📝 写作章节 {i+1}: {getattr(task_obj, 'section_title', '未知标题')}")
            
            sec = await write_action.run(task=task_obj)
            sections.append(sec)
            logger.info(f"✅ 章节 {i+1} 写作完成")

        # 聚合保存
        try:
            final_report = "\n\n".join(sections)
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            fname = f"final_report_{ts}.md"
            await self._project_repo.docs.save(filename=fname, content=final_report)
            logger.info(f"📝 最终报告已保存: {self._project_repo.docs.workdir / fname}")
        except Exception as e:
            logger.error(f"保存最终报告失败: {e}")

        return Message(content="章节写作完成", cause_by=WriteSection)

