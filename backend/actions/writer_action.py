#!/usr/bin/env python
"""
写作专家Action集合 - 内容生成和整合
"""
import pandas as pd
from pathlib import Path
from metagpt.actions import Action
from metagpt.logs import logger
from metagpt.const import DEFAULT_WORKSPACE_ROOT

from .pm_action import Task


class WriteSection(Action):
    """
    写作章节Action - WriterExpert的核心能力
    集成RAG检索，结合事实依据和数据生成章节内容
    """
    
    async def run(
        self, 
        task: Task, 
        vector_store_path: str, 
        metric_table_json: str
    ) -> str:
        """
        基于任务要求、向量索引和指标数据生成章节内容
        """
        logger.info(f"开始写作章节: {task.section_title}")
        
        # 1. 加载指标数据
        metric_df = pd.read_json(metric_table_json)
        
        # 2. 获取相关指标数据
        relevant_metrics = self._get_relevant_metrics(task, metric_df)
        
        # 3. RAG检索事实依据 (简化实现)
        factual_basis = await self._retrieve_factual_basis(task, vector_store_path)
        
        # 4. 构建写作prompt
        prompt = self._build_writing_prompt(task, factual_basis, relevant_metrics)
        
        # 5. 生成章节内容
        section_content = await self._generate_content(prompt)
        
        logger.info(f"章节写作完成: {task.section_title}")
        return section_content
    
    def _get_relevant_metrics(self, task: Task, metric_df: pd.DataFrame) -> pd.DataFrame:
        """获取与任务相关的指标数据"""
        if not task.metric_ids:
            return pd.DataFrame()
        
        relevant_metrics = metric_df[metric_df['metric_id'].isin(task.metric_ids)]
        return relevant_metrics
    
    async def _retrieve_factual_basis(self, task: Task, vector_store_path: str) -> str:
        """从向量索引中检索相关的事实依据"""
        # TODO: 实际的RAG检索实现
        # from metagpt.rag.engines import SimpleEngine
        # engine = SimpleEngine.from_persist(vector_store_path)
        # query_engine = engine.get_query_engine()
        # retrieved_nodes = await query_engine.aquery(task.instruction)
        # factual_basis = "\n".join([node.get_content() for node in retrieved_nodes])
        
        # 简化实现
        factual_basis = f"根据我们的研究，关于'{task.section_title}'的核心发现包括市场趋势分析、竞争对手表现对比、以及相关的行业最佳实践案例。"
        return factual_basis
    
    def _build_writing_prompt(self, task: Task, factual_basis: str, relevant_metrics: pd.DataFrame) -> str:
        """构建写作prompt"""
        # 格式化指标数据
        metrics_text = ""
        if not relevant_metrics.empty:
            metrics_text = "\n".join([
                f"- {row['name']}: {row['value']} ({row['analysis']})"
                for _, row in relevant_metrics.iterrows()
            ])
        
        prompt = f"""
请根据以下信息撰写报告章节：

## 章节标题
{task.section_title}

## 写作要求
{task.instruction}

## 相关事实依据
{factual_basis}

## 关键指标数据
{metrics_text}

## 写作指南
1. 章节内容应该结构清晰，逻辑严谨
2. 充分利用提供的事实依据和数据支撑观点
3. 包含深度分析和具体建议
4. 使用专业的商业分析语言
5. 字数控制在800-1200字之间

请开始撰写：
"""
        return prompt
    
    async def _generate_content(self, prompt: str) -> str:
        """生成章节内容"""
        # 使用LLM生成内容
        section_content = await self._aask(prompt)
        return section_content


class IntegrateReport(Action):
    """
    整合报告Action - 将所有章节整合为最终报告
    """
    
    async def run(self, sections: list, report_title: str) -> str:
        """
        整合所有章节为最终报告
        """
        logger.info("开始整合最终报告")
        
        # 构建完整报告
        report_parts = [
            f"# {report_title}",
            "",
            "## 摘要",
            "本报告基于综合数据分析和市场研究，对相关绩效指标进行深入分析，并提出具体的改进建议。",
            "",
        ]
        
        # 添加所有章节
        for section in sections:
            report_parts.append(section)
            report_parts.append("")
        
        # 添加报告尾部
        report_parts.extend([
            "---",
            f"*报告生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])
        
        final_report = "\n".join(report_parts)
        
        # 保存报告到文件
        report_path = DEFAULT_WORKSPACE_ROOT / "final_report.md"
        report_path.write_text(final_report, encoding='utf-8')
        
        logger.info(f"最终报告已保存到: {report_path}")
        return final_report


# 保留原有的Action以保持兼容性
class WriteContent(Action):
    """原有的写作Action，保持兼容性"""
    async def run(self, instruction: str) -> str:
        return await self._aask(instruction)


class SummarizeText(Action):
    """原有的总结Action，保持兼容性"""
    async def run(self, text: str) -> str:
        prompt = f"请对以下文本进行总结：\n\n{text}"
        return await self._aask(prompt)


class PolishContent(Action):
    """原有的润色Action，保持兼容性"""
    async def run(self, content: str) -> str:
        prompt = f"请对以下内容进行润色和优化：\n\n{content}"
        return await self._aask(prompt)


class ReviewContent(Action):
    """原有的审核Action，保持兼容性"""
    async def run(self, content: str) -> str:
        prompt = f"请对以下内容进行审核和评价：\n\n{content}"
        return await self._aask(prompt)