#!/usr/bin/env python
"""
架构师Action集合 - 报告结构设计和指标分析
"""
import pandas as pd
from typing import List, Tuple
from pydantic import BaseModel, Field
from metagpt.actions import Action
from metagpt.logs import logger


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


class DesignReportStructure(Action):
    """
    设计报告结构Action - Architect的核心能力
    基于研究简报设计报告架构和指标体系
    """
    
    async def run(self, research_brief: str) -> Tuple[ReportStructure, MetricAnalysisTable]:
        """
        基于研究简报设计报告结构和指标分析表
        """
        logger.info("开始设计报告结构和指标体系")
        
        # 1. 分析研究简报，提取关键主题 (这里简化处理，实际会用LLM分析)
        topic_analysis = await self._analyze_research_brief(research_brief)
        
        # 2. 设计指标体系
        metrics_df = await self._design_metrics_system(topic_analysis)
        
        # 3. 设计报告大纲，并建立章节到指标的映射
        report_structure = await self._design_report_outline(topic_analysis, metrics_df)
        
        # 4. 封装返回结果
        metric_table = MetricAnalysisTable(data_json=metrics_df.to_json(orient='records'))
        
        logger.info(f"报告结构设计完成: {report_structure.title}")
        logger.info(f"指标体系设计完成: {len(metrics_df)} 个指标")
        
        return report_structure, metric_table
    
    async def _analyze_research_brief(self, research_brief: str) -> dict:
        """分析研究简报，提取关键信息"""
        # 简化实现，实际会使用LLM进行智能分析
        analysis = {
            "main_topic": "绩效分析",
            "key_areas": ["用户增长", "转化效率", "营收表现", "市场竞争"],
            "time_period": "年度",
            "company_focus": True
        }
        return analysis
    
    async def _design_metrics_system(self, topic_analysis: dict) -> pd.DataFrame:
        """设计指标体系"""
        # 基于主题分析设计指标 (简化实现)
        metrics_data = [
            {
                'metric_id': 'MAU',
                'name': '月活跃用户',
                'category': '用户增长',
                'value': '1,000,000',
                'analysis': '同比增长20%，主要来源于新用户获取策略的优化',
                'trend': 'positive'
            },
            {
                'metric_id': 'ConversionRate',
                'name': '转化率',
                'category': '转化效率',
                'value': '5.2%',
                'analysis': '环比下降0.3%，需要优化转化漏斗中的关键节点',
                'trend': 'negative'
            },
            {
                'metric_id': 'Revenue',
                'name': '营业收入',
                'category': '营收表现',
                'value': '¥50,000,000',
                'analysis': '同比增长15%，主要驱动因素为客单价提升',
                'trend': 'positive'
            },
            {
                'metric_id': 'MarketShare',
                'name': '市场份额',
                'category': '市场竞争',
                'value': '12%',
                'analysis': '在细分市场中排名第三，与头部企业差距缩小',
                'trend': 'stable'
            }
        ]
        
        return pd.DataFrame(metrics_data)
    
    async def _design_report_outline(self, topic_analysis: dict, metrics_df: pd.DataFrame) -> ReportStructure:
        """设计报告大纲"""
        # 根据指标分类设计章节结构
        sections = []
        
        # 按指标类别分组
        for category in metrics_df['category'].unique():
            category_metrics = metrics_df[metrics_df['category'] == category]
            metric_ids = category_metrics['metric_id'].tolist()
            
            section = Section(
                section_title=f"{category}分析",
                metric_ids=metric_ids,
                description_prompt=f"深入分析{category}相关的关键指标，包括趋势分析、原因探讨和改进建议"
            )
            sections.append(section)
        
        # 添加总结章节
        sections.append(Section(
            section_title="总结与建议",
            metric_ids=[],
            description_prompt="基于各项指标分析，总结整体绩效表现，并提出具体的改进建议和未来发展策略"
        ))
        
        report_structure = ReportStructure(
            title=f"{topic_analysis.get('main_topic', '绩效')}分析报告",
            sections=sections
        )
        
        return report_structure