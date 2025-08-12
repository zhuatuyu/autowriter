#!/usr/bin/env python
"""
写作专家Action集合 - 内容生成和整合（SOP2 章节写作）
"""
import pandas as pd
from pathlib import Path
from metagpt.actions import Action
from metagpt.logs import logger
from backend.services.intelligent_search import intelligent_search
from backend.config.writer_prompts import (
    WRITER_BASE_SYSTEM as ENV_WRITER_BASE_SYSTEM,
    SECTION_WRITING_PROMPT as ENV_SECTION_WRITING_PROMPT,
)
from backend.tools.json_utils import extract_json_from_llm_response
from backend.tools.project_info import get_project_info_text
from .project_manager_action import Task


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
        try:
            # 使用集中后的通用JSON提取工具，输出即为可消费结构
            parsed = extract_json_from_llm_response(metric_table_json)

            if isinstance(parsed, list):
                metric_df = pd.DataFrame(parsed)
            elif isinstance(parsed, dict):
                metric_df = pd.DataFrame([parsed])
            else:
                metric_df = pd.DataFrame()
        except Exception as e:
            logger.error(f"解析指标数据失败: {e}")
            metric_df = pd.DataFrame()
        
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
        """获取与任务相关的指标数据（动态解耦后，默认返回全部指标）"""
        if metric_df.empty:
            return pd.DataFrame()
        return metric_df
    
    async def _retrieve_factual_basis(self, task: Task, vector_store_path: str) -> str:
        """🧠 使用智能检索服务检索相关的事实依据"""
        try:
            # 🧠 构建更智能的检索查询 - 结合章节标题和写作要求
            search_query = f"{task.section_title} {task.instruction[:200]}"
            
            # 🧠 检索模式选择交由智能检索服务根据配置决策，这里统一走hybrid
            search_result = await intelligent_search.intelligent_search(
                query=search_query,
                project_vector_storage_path=vector_store_path,
                mode="hybrid",
                enable_global=True,
                max_results=6
            )
            
            # 提取检索到的内容
            if search_result.get("results"):
                results = search_result["results"]
                factual_basis = "\n\n".join([
                    f"**🧠 智能检索资料{i+1}**: {result}" 
                    for i, result in enumerate(results[:6])  # 取前6个最相关的结果
                ])
                
                # 🧠 添加智能洞察
                if search_result.get("insights"):
                    factual_basis += "\n\n**💡 智能分析洞察**:\n" + "\n".join(search_result["insights"])
                
                logger.info(f"🧠 智能检索到 {len(results)} 条相关信息用于章节: {task.section_title}，使用模式: {search_result.get('mode_used', 'hybrid')}")
                return factual_basis
            else:
                logger.warning(f"未检索到结果: {task.section_title}")
                return f"未能检索到关于'{task.section_title}'的相关信息。"
            
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return f"向量检索发生错误，无法获取关于'{task.section_title}'的事实依据。错误: {str(e)}"
    
    def _build_writing_prompt(self, task: Task, factual_basis: str, relevant_metrics: pd.DataFrame) -> str:
        """构建写作prompt - 整合Architect的写作指导"""
        
        # 格式化指标数据
        metrics_text = ""
        if not relevant_metrics.empty:
            # 检查DataFrame的列结构
            if 'name' in relevant_metrics.columns:
                # 新格式：直接使用指标信息
                metrics_text = "\n".join([
                    f"- **{row['name']}** ({row.get('category', '未分类')}): {row.get('评分规则', '评分规则待补充')}"
                    for _, row in relevant_metrics.iterrows()
                ])
            else:
                # 旧格式兼容
                metrics_text = "\n".join([
                    f"- {row.get('name', '未知指标')}: {row.get('value', '数值待补充')} ({row.get('analysis', '分析待补充')})"
                    for _, row in relevant_metrics.iterrows()
                ])
        
        prompt = ENV_SECTION_WRITING_PROMPT.format(
            section_title=task.section_title,
            instruction=task.instruction,
            factual_basis=factual_basis,
            metrics_text=metrics_text,
            word_limit="2000"
        )
        return prompt
    
    async def _generate_content(self, prompt: str) -> str:
        """生成章节内容"""
        # 使用LLM生成内容
        # 注入项目配置信息作为系统级提示
        project_info_text = get_project_info_text()
        section_content = await self._aask(prompt, [ENV_WRITER_BASE_SYSTEM, project_info_text])
        return section_content


