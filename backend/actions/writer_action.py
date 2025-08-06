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


# --- 写作专家专用提示词模板 ---
WRITER_BASE_SYSTEM = """你是绩效评价报告的写作专家。你的目标是：
1. 基于事实依据和数据支撑，撰写高质量的报告章节
2. 严格遵循架构师制定的写作指导和检索要求
3. 确保内容专业、准确、深入，符合绩效评价报告的标准
"""

SECTION_WRITING_PROMPT = """请根据以下信息撰写报告章节：

## 章节标题
{section_title}

## 写作要求与指导
{instruction}

## 相关事实依据（来自向量检索）
{factual_basis}

## 关联的绩效指标
{metrics_text}

## 📋 写作标准与质量要求

### 🎯 内容要求
1. **数据驱动**: 所有论点必须基于上述事实依据，避免空泛论述
2. **结构清晰**: 按照写作要求中的指导顺序组织内容
3. **深度分析**: 不仅要列出事实，还要分析原因、影响和趋势
4. **专业表达**: 使用绩效评价专业术语和商业分析语言

### 📊 格式要求
1. **表格展示**: 涉及数据对比时，务必使用Markdown表格格式
2. **分层论述**: 使用适当的标题层级组织内容结构
3. **数据引用**: 明确标注数据来源和引用依据
4. **字数控制**: 章节内容控制在{word_limit}字以内

### 🔍 检索验证要求
- 如果事实依据中缺少某项关键信息，请明确标注"**信息待补充**"
- 确保每个关键论点都有具体的数据或事实支撑
- 避免使用模糊的表述，如"大约"、"可能"等

请严格按照上述要求开始撰写：
"""


class EvaluateMetrics(Action):
    """
    指标评分Action - 按照标准化评价类型进行指标评分
    为每个指标生成评价意见和具体得分
    """
    
    async def run(self, metric_table_json: str, vector_store_path: str) -> dict:
        """
        对所有指标进行评分，返回评分结果
        
        Returns:
            dict: {
                "metrics_scores": [{"metric": {}, "score": 85.5, "opinion": "评价意见"}],
                "level1_summary": {"决策": 12.5, "过程": 22.3, "产出": 30.1, "效益": 20.6},
                "total_score": 85.5,
                "grade": "良好"
            }
        """
        logger.info("📊 开始进行指标评分...")
        
        try:
            # 解析指标数据
            import json
            metrics_data = json.loads(metric_table_json)
            
            if isinstance(metrics_data, dict) and "error" in metrics_data:
                return {"error": "指标体系构建失败", "details": metrics_data}
            
            # 为每个指标进行评分
            metrics_scores = []
            level1_scores = {"决策": 0, "过程": 0, "产出": 0, "效益": 0}
            
            for metric in metrics_data:
                try:
                    # 执行单个指标评分
                    score, opinion = await self._evaluate_single_metric(metric, vector_store_path)
                    
                    metrics_scores.append({
                        "metric": metric,
                        "score": score,
                        "opinion": opinion,
                        "weight_score": score * metric.get("分值", 0) / 100
                    })
                    
                    # 累计一级指标得分
                    level1 = metric.get("一级指标", "")
                    if level1 in level1_scores:
                        level1_scores[level1] += score * metric.get("分值", 0) / 100
                    
                    logger.info(f"✅ 完成指标评分: {metric.get('name', '未知指标')} - {score}分")
                    
                except Exception as e:
                    logger.error(f"指标评分失败: {metric.get('name', '未知指标')} - {e}")
                    # 给默认分数
                    metrics_scores.append({
                        "metric": metric,
                        "score": 0,
                        "opinion": f"评分过程中出现错误：{str(e)}",
                        "weight_score": 0
                    })
            
            # 计算总分
            total_score = sum(level1_scores.values())
            
            # 确定评价等级
            grade = self._determine_grade(total_score)
            
            result = {
                "metrics_scores": metrics_scores,
                "level1_summary": level1_scores,
                "total_score": round(total_score, 2),
                "grade": grade
            }
            
            logger.info(f"📊 指标评分完成，总分: {total_score:.2f}分，等级: {grade}")
            return result
            
        except Exception as e:
            logger.error(f"指标评分过程失败: {e}")
            return {"error": "指标评分失败", "details": str(e)}
    
    async def _evaluate_single_metric(self, metric: dict, vector_store_path: str) -> tuple:
        """
        评价单个指标，返回(得分, 评价意见)
        """
        metric_name = metric.get("name", "未知指标")
        evaluation_type = metric.get("evaluation_type", "")
        evaluation_points = metric.get("evaluation_points", [])
        scoring_method = metric.get("scoring_method", "")
        
        # RAG检索相关事实
        facts = await self._retrieve_metric_facts(metric_name, vector_store_path)
        
        # 根据评价类型执行相应的评分逻辑
        if evaluation_type == "要素符合度计分":
            return await self._evaluate_element_compliance(facts, evaluation_points, scoring_method)
        elif evaluation_type == "公式计算得分":
            return await self._evaluate_formula_calculation(facts, evaluation_points, scoring_method)
        elif evaluation_type == "条件判断得分":
            return await self._evaluate_condition_judgment(facts, evaluation_points, scoring_method)
        elif evaluation_type == "定性与定量结合":
            return await self._evaluate_qualitative_quantitative(facts, evaluation_points, scoring_method)
        elif evaluation_type == "递减扣分机制":
            return await self._evaluate_deduction_scoring(facts, evaluation_points, scoring_method)
        elif evaluation_type == "李克特量表法":
            return await self._evaluate_likert_scale(facts, evaluation_points, scoring_method)
        else:
            # 默认评分方式
            return await self._evaluate_default(facts, metric_name)
    
    async def _retrieve_metric_facts(self, metric_name: str, vector_store_path: str) -> str:
        """
        为指标检索相关事实依据
        """
        try:
            from metagpt.rag.engines.simple import SimpleEngine
            from llama_index.llms.openai import OpenAI as LlamaOpenAI
            from pathlib import Path
            from metagpt.config2 import Config
            from metagpt.rag.factories.embedding import get_rag_embedding
            import os
            
            if not os.path.exists(vector_store_path):
                return f"向量库不可用，无法检索关于'{metric_name}'的事实依据。"
            
            vector_files = []
            if os.path.isdir(vector_store_path):
                vector_files = [os.path.join(vector_store_path, f) for f in os.listdir(vector_store_path) if f.endswith('.txt')]
            
            if not vector_files:
                return f"向量库为空，无法检索关于'{metric_name}'的事实依据。"
            
            # 使用MetaGPT原生的RAG引擎
            full_config = Config.from_yaml_file(Path('config/config2.yaml'))
            llm_config = full_config.llm
            llm = LlamaOpenAI(
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                model="gpt-3.5-turbo"
            )
            
            embed_model = get_rag_embedding(config=full_config)
            embed_model.embed_batch_size = 10
            
            engine = SimpleEngine.from_docs(
                input_files=vector_files,
                llm=llm,
                embed_model=embed_model
            )
            
            # 执行检索
            results = await engine.aretrieve(metric_name)
            
            if results:
                facts = "\n\n".join([result.text.strip() for result in results[:3]])
                logger.debug(f"成功检索到关于'{metric_name}'的事实依据")
                return facts
            else:
                return f"未能检索到关于'{metric_name}'的相关事实依据。"
                
        except Exception as e:
            logger.error(f"检索指标事实失败: {e}")
            return f"检索过程发生错误：{str(e)}"
    
    async def _evaluate_element_compliance(self, facts: str, evaluation_points: list, scoring_method: str) -> tuple:
        """
        要素符合度计分评价
        """
        evaluation_prompt = f"""
请根据以下事实依据，对照评价要点进行要素符合度评价：

评价要点：
{chr(10).join(evaluation_points)}

事实依据：
{facts}

评分方法：{scoring_method}

请按照要素符合度计分的标准，生成评价意见并计算得分：
1. 逐一对照评价要点，判断每个要点的符合情况
2. 根据符合的要点数量和评分方法计算得分
3. 生成符合格式要求的评价意见（不包含最终得分）

返回JSON格式：
{{
    "score": 85.5,
    "opinion": "项目立项依据相关法律法规，符合评价要点①；项目内容符合行业规划，符合评价要点②；..."
}}
"""
        
        try:
            result = await self._aask(evaluation_prompt, [WRITER_BASE_SYSTEM])
            # 解析结果
            import json
            parsed = self._extract_json_from_evaluation_response(result)
            return parsed.get("score", 0), parsed.get("opinion", "评价意见生成失败")
        except Exception as e:
            logger.error(f"要素符合度评价失败: {e}")
            return 0, f"要素符合度评价过程中出现错误：{str(e)}"
    
    async def _evaluate_formula_calculation(self, facts: str, evaluation_points: list, scoring_method: str) -> tuple:
        """
        公式计算得分评价
        """
        evaluation_prompt = f"""
请根据以下事实依据，进行公式计算得分评价：

计算要求：
{chr(10).join(evaluation_points)}

事实依据：
{facts}

评分方法：{scoring_method}

请按照公式计算得分的标准：
1. 从事实中提取具体数据
2. 按照公式进行计算
3. 将计算结果转换为得分
4. 生成包含完整计算过程的评价意见

返回JSON格式：
{{
    "score": 87.93,
    "opinion": "依据基础数据表，2021-2024年预算执行率分别为100.00%、100.00%、100.00%、68.91%，四年加权平均值为87.93%；..."
}}
"""
        
        try:
            result = await self._aask(evaluation_prompt, [WRITER_BASE_SYSTEM])
            parsed = self._extract_json_from_evaluation_response(result)
            return parsed.get("score", 0), parsed.get("opinion", "评价意见生成失败")
        except Exception as e:
            logger.error(f"公式计算评价失败: {e}")
            return 0, f"公式计算评价过程中出现错误：{str(e)}"
    
    async def _evaluate_condition_judgment(self, facts: str, evaluation_points: list, scoring_method: str) -> tuple:
        """
        条件判断得分评价
        """
        evaluation_prompt = f"""
请根据以下事实依据，进行条件判断得分评价：

判断条件：
{chr(10).join(evaluation_points)}

事实依据：
{facts}

评分方法：{scoring_method}

请按照条件判断得分的标准：
1. 判断每个条件的满足情况
2. 根据条件满足程度给出得分
3. 提供具体的证据支撑

返回JSON格式：
{{
    "score": 75.0,
    "opinion": "项目制定了完整的管理办法，符合条件①；申报材料存在格式问题，不符合条件②；..."
}}
"""
        
        try:
            result = await self._aask(evaluation_prompt, [WRITER_BASE_SYSTEM])
            parsed = self._extract_json_from_evaluation_response(result)
            return parsed.get("score", 0), parsed.get("opinion", "评价意见生成失败")
        except Exception as e:
            logger.error(f"条件判断评价失败: {e}")
            return 0, f"条件判断评价过程中出现错误：{str(e)}"
    
    async def _evaluate_qualitative_quantitative(self, facts: str, evaluation_points: list, scoring_method: str) -> tuple:
        """
        定性与定量结合评价
        """
        evaluation_prompt = f"""
请根据以下事实依据，进行定性与定量结合评价：

评价要求：
{chr(10).join(evaluation_points)}

事实依据：
{facts}

评分方法：{scoring_method}

请按照定性与定量结合的标准：
1. 分别进行定量和定性评价
2. 按权重综合计算得分
3. 评价意见要体现两个方面的结合

返回JSON格式：
{{
    "score": 92.0,
    "opinion": "依据基础数据表，设备匹配度达90.00%，符合评价要点①；通过实地调研发现设备利用充分，符合评价要点②；..."
}}
"""
        
        try:
            result = await self._aask(evaluation_prompt, [WRITER_BASE_SYSTEM])
            parsed = self._extract_json_from_evaluation_response(result)
            return parsed.get("score", 0), parsed.get("opinion", "评价意见生成失败")
        except Exception as e:
            logger.error(f"定性定量评价失败: {e}")
            return 0, f"定性定量评价过程中出现错误：{str(e)}"
    
    async def _evaluate_deduction_scoring(self, facts: str, evaluation_points: list, scoring_method: str) -> tuple:
        """
        递减扣分机制评价
        """
        evaluation_prompt = f"""
请根据以下事实依据，进行递减扣分机制评价：

扣分标准：
{chr(10).join(evaluation_points)}

事实依据：
{facts}

评分方法：{scoring_method}

请按照递减扣分机制的标准：
1. 识别存在的问题
2. 按照扣分标准计算扣分
3. 从满分中扣除相应分数

返回JSON格式：
{{
    "score": 70.0,
    "opinion": "按时报送工作总结，符合要求；发现2个赛事未按规定时限报送总结，扣除20分；未提供专家论证资料，扣除10分；..."
}}
"""
        
        try:
            result = await self._aask(evaluation_prompt, [WRITER_BASE_SYSTEM])
            parsed = self._extract_json_from_evaluation_response(result)
            return parsed.get("score", 0), parsed.get("opinion", "评价意见生成失败")
        except Exception as e:
            logger.error(f"递减扣分评价失败: {e}")
            return 0, f"递减扣分评价过程中出现错误：{str(e)}"
    
    async def _evaluate_likert_scale(self, facts: str, evaluation_points: list, scoring_method: str) -> tuple:
        """
        李克特量表法评价
        """
        evaluation_prompt = f"""
请根据以下事实依据，进行李克特量表法评价：

调查要求：
{chr(10).join(evaluation_points)}

事实依据：
{facts}

评分方法：{scoring_method}

请按照李克特量表法的标准：
1. 分析调查数据和样本量
2. 计算满意度百分比
3. 根据满意度确定得分

返回JSON格式：
{{
    "score": 91.58,
    "opinion": "根据电子问卷调查及结果汇总，共回收有效问卷1330份，满意度问题回答总数为9310题，其中非常满意7055题，比较满意1589题，无感511题，比较不满意96题，非常不满意59题。经计算，满意度为91.58%。"
}}
"""
        
        try:
            result = await self._aask(evaluation_prompt, [WRITER_BASE_SYSTEM])
            parsed = self._extract_json_from_evaluation_response(result)
            return parsed.get("score", 0), parsed.get("opinion", "评价意见生成失败")
        except Exception as e:
            logger.error(f"李克特量表评价失败: {e}")
            return 0, f"李克特量表评价过程中出现错误：{str(e)}"
    
    async def _evaluate_default(self, facts: str, metric_name: str) -> tuple:
        """
        默认评价方式（当评价类型未识别时使用）
        """
        evaluation_prompt = f"""
请根据以下事实依据，对指标"{metric_name}"进行评价：

事实依据：
{facts}

请生成评价意见并给出合理的得分（0-100分）：

返回JSON格式：
{{
    "score": 80.0,
    "opinion": "基于现有事实依据的综合评价意见..."
}}
"""
        
        try:
            result = await self._aask(evaluation_prompt, [WRITER_BASE_SYSTEM])
            parsed = self._extract_json_from_evaluation_response(result)
            return parsed.get("score", 60), parsed.get("opinion", "默认评价意见")
        except Exception as e:
            logger.error(f"默认评价失败: {e}")
            return 60, f"默认评价：基于有限信息给出中等评价"
    
    def _extract_json_from_evaluation_response(self, response: str) -> dict:
        """
        从评价响应中提取JSON内容
        """
        try:
            import json
            import re
            
            # 尝试多种JSON提取方法
            try:
                return json.loads(response)
            except:
                pass
            
            # 提取JSON代码块
            json_pattern = r'```json\s*(.*?)\s*```'
            match = re.search(json_pattern, response, re.DOTALL)
            if match:
                return json.loads(match.group(1).strip())
            
            # 查找大括号内容
            start_idx = response.find('{')
            if start_idx != -1:
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
            
            raise ValueError("无法提取JSON内容")
            
        except Exception as e:
            logger.error(f"JSON提取失败: {e}")
            return {"score": 0, "opinion": "评价结果解析失败"}
    
    def _determine_grade(self, total_score: float) -> str:
        """
        根据总分确定评价等级
        """
        if total_score >= 90:
            return "优秀"
        elif total_score >= 80:
            return "良好"
        elif total_score >= 70:
            return "一般"
        elif total_score >= 60:
            return "及格"
        else:
            return "较差"


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
            # 尝试直接解析JSON
            import json
            metric_data = json.loads(metric_table_json)
            
            # 如果是列表格式（新格式），转换为DataFrame
            if isinstance(metric_data, list):
                metric_df = pd.DataFrame(metric_data)
            else:
                # 如果是DataFrame格式（旧格式），直接用pandas读取
                metric_df = pd.read_json(metric_table_json)
        except Exception as e:
            logger.error(f"解析指标数据失败: {e}")
            # 创建一个空的DataFrame以防止程序崩溃
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
        """获取与任务相关的指标数据"""
        if not task.metric_ids or metric_df.empty:
            return pd.DataFrame()
        
        # 检查DataFrame是否有必要的列
        if 'metric_id' not in metric_df.columns:
            logger.warning("指标数据中缺少metric_id列，返回空DataFrame")
            return pd.DataFrame()
        
        relevant_metrics = metric_df[metric_df['metric_id'].isin(task.metric_ids)]
        return relevant_metrics
    
    async def _retrieve_factual_basis(self, task: Task, vector_store_path: str) -> str:
        """从向量索引中检索相关的事实依据"""
        try:
            from metagpt.rag.engines.simple import SimpleEngine
            from llama_index.llms.openai import OpenAI as LlamaOpenAI
            from pathlib import Path
            from metagpt.config2 import Config
            from metagpt.rag.factories.embedding import get_rag_embedding
            import os
            
            if not os.path.exists(vector_store_path):
                logger.warning(f"向量库路径不存在: {vector_store_path}")
                return f"向量库不可用，无法检索关于'{task.section_title}'的事实依据。"
            
            # 检查向量库文件
            vector_files = []
            if os.path.isdir(vector_store_path):
                vector_files = [os.path.join(vector_store_path, f) for f in os.listdir(vector_store_path) if f.endswith('.txt')]
            
            if not vector_files:
                logger.warning(f"向量库目录为空: {vector_store_path}")
                return f"向量库为空，无法检索关于'{task.section_title}'的事实依据。"
            
            # 使用MetaGPT原生的RAG引擎
            full_config = Config.from_yaml_file(Path('config/config2.yaml'))
            
            # 获取LLM配置
            llm_config = full_config.llm
            llm = LlamaOpenAI(
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                model="gpt-3.5-turbo"
            )
            
            # 使用MetaGPT原生embedding工厂
            embed_model = get_rag_embedding(config=full_config)
            embed_model.embed_batch_size = 10
            
            engine = SimpleEngine.from_docs(
                input_files=vector_files,
                llm=llm,
                embed_model=embed_model
            )
            
            # 构建检索查询 - 结合章节标题和写作要求
            search_query = f"{task.section_title} {task.instruction[:200]}"
            
            # 执行检索
            results = await engine.aretrieve(search_query)
            
            # 提取检索到的内容
            factual_basis = ""
            if results:
                factual_basis = "\n\n".join([
                    f"**相关资料{i+1}**: {result.text.strip()}" 
                    for i, result in enumerate(results[:3])  # 取前3个最相关的结果
                ])
                logger.info(f"成功从向量库检索到 {len(results)} 条相关信息用于章节: {task.section_title}")
            else:
                factual_basis = f"未能从向量库中检索到关于'{task.section_title}'的相关信息。"
                logger.warning(f"向量检索未返回结果: {task.section_title}")
            
            return factual_basis
            
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
        
        prompt = SECTION_WRITING_PROMPT.format(
            section_title=task.section_title,
            instruction=task.instruction,
            factual_basis=factual_basis,
            metrics_text=metrics_text,
            word_limit="4000"
        )
        return prompt
    
    async def _generate_content(self, prompt: str) -> str:
        """生成章节内容"""
        # 使用LLM生成内容
        section_content = await self._aask(prompt, [WRITER_BASE_SYSTEM])
        return section_content


class IntegrateReport(Action):
    """
    整合报告Action - 将所有章节整合为最终报告，包括指标评分附件
    """
    
    async def run(self, sections: list, report_title: str, metrics_evaluation: dict = None) -> str:
        """
        整合所有章节为最终报告，包括指标评分附件和综合评价表
        """
        logger.info("开始整合最终报告（包含指标评分附件）")
        
        # 构建完整报告
        report_parts = [
            f"# {report_title}",
            "",
            "## 📋 目录",
            ""
        ]
        
        # 生成目录
        toc_items = []
        for i, section in enumerate(sections, 1):
            # 从章节内容中提取标题
            lines = section.split('\n')
            title = lines[0].replace('#', '').strip() if lines else f"章节{i}"
            toc_items.append(f"{i}. {title}")
        
        # 添加附件目录
        if metrics_evaluation and metrics_evaluation.get('metrics_scores'):
            toc_items.extend([
                "",
                "**附件**",
                "A. 指标评分详表",
                "B. 综合评价汇总表"
            ])
        
        report_parts.extend(toc_items)
        report_parts.extend(["", "---", ""])
        
        # 添加综合评价结论（如果有指标评分）
        if metrics_evaluation and metrics_evaluation.get('total_score') > 0:
            total_score = metrics_evaluation.get('total_score', 0)
            grade = metrics_evaluation.get('grade', '待评价')
            level1_summary = metrics_evaluation.get('level1_summary', {})
            
            conclusion_section = f"""## 💯 综合绩效评价结论

**总体评价等级**: {grade}  
**综合得分**: {total_score:.2f}分

### 一级指标得分情况

| 一级指标 | 标准分值 | 实际得分 | 得分率 |
|---------|---------|---------|--------|
| 决策指标 | 15.00分 | {level1_summary.get('决策', 0):.2f}分 | {(level1_summary.get('决策', 0)/15*100):.1f}% |
| 过程指标 | 25.00分 | {level1_summary.get('过程', 0):.2f}分 | {(level1_summary.get('过程', 0)/25*100):.1f}% |
| 产出指标 | 35.00分 | {level1_summary.get('产出', 0):.2f}分 | {(level1_summary.get('产出', 0)/35*100):.1f}% |
| 效益指标 | 25.00分 | {level1_summary.get('效益', 0):.2f}分 | {(level1_summary.get('效益', 0)/25*100):.1f}% |
| **合计** | **100.00分** | **{total_score:.2f}分** | **{total_score:.1f}%** |

根据绩效评价结果，本项目在各项指标中的表现{"优秀" if total_score >= 90 else "良好" if total_score >= 80 else "中等" if total_score >= 70 else "有待改进"}，详细的指标评分情况请参见附件A。

---
"""
            report_parts.append(conclusion_section)
        
        # 添加所有主报告章节
        for section in sections:
            report_parts.append(section)
            report_parts.append("")
        
        # 添加指标评分附件
        if metrics_evaluation and metrics_evaluation.get('metrics_scores'):
            logger.info("添加指标评分附件...")
            
            report_parts.extend([
                "---",
                "",
                "# 📊 附件：指标评分详表",
                "",
                "## 附件A：各项指标评分明细",
                ""
            ])
            
            # 按一级指标分组
            level1_groups = {"决策": [], "过程": [], "产出": [], "效益": []}
            for score_item in metrics_evaluation['metrics_scores']:
                metric = score_item['metric']
                level1 = metric.get('一级指标', '其他')
                if level1 in level1_groups:
                    level1_groups[level1].append(score_item)
            
            # 生成各一级指标的详细评分
            for level1_name, score_items in level1_groups.items():
                if not score_items:
                    continue
                    
                report_parts.extend([
                    f"### A.{list(level1_groups.keys()).index(level1_name)+1} {level1_name}指标评分",
                    ""
                ])
                
                for score_item in score_items:
                    metric = score_item['metric']
                    score = score_item['score']
                    opinion = score_item['opinion']
                    weight_score = score_item['weight_score']
                    
                    metric_detail = f"""#### {metric.get('name', '未知指标')}

**指标权重**: {metric.get('分值', 0)}分  
**评价类型**: {metric.get('evaluation_type', '标准评价')}  
**实际得分**: {score:.2f}分  
**权重得分**: {weight_score:.2f}分  

**评价意见**:  
{opinion}

**评分依据**:  
{metric.get('scoring_method', '无具体评分方法')}

---
"""
                    report_parts.append(metric_detail)
            
            # 添加综合评价汇总表
            report_parts.extend([
                "",
                "## 附件B：综合评价汇总表",
                "",
                "### B.1 指标权重与得分汇总",
                "",
                "| 指标名称 | 一级指标 | 权重分值 | 实际得分 | 权重得分 | 评价类型 |",
                "|---------|---------|---------|---------|---------|---------|"
            ])
            
            for score_item in metrics_evaluation['metrics_scores']:
                metric = score_item['metric']
                score = score_item['score']
                weight_score = score_item['weight_score']
                
                row = f"| {metric.get('name', '未知指标')} | {metric.get('一级指标', '')} | {metric.get('分值', 0)}分 | {score:.2f}分 | {weight_score:.2f}分 | {metric.get('evaluation_type', '')} |"
                report_parts.append(row)
            
            # 总分行
            total_weight = sum([m['metric'].get('分值', 0) for m in metrics_evaluation['metrics_scores']])
            total_score = metrics_evaluation.get('total_score', 0)
            report_parts.extend([
                f"| **总计** | **全部** | **{total_weight}分** | **-** | **{total_score:.2f}分** | **综合评价** |",
                "",
                f"**最终评价等级**: {metrics_evaluation.get('grade', '待评价')}",
                ""
            ])
        
        # 添加报告尾部
        report_parts.extend([
            "---",
            "",
            "## 📄 报告说明",
            "",
            "- 本报告基于向量检索技术和标准化评价方法生成",
            "- 指标评分采用6种标准化评价类型进行专业评估", 
            "- 所有评价意见均基于实际项目资料和数据分析",
            "",
            f"*报告生成时间: {pd.Timestamp.now().strftime('%Y年%m月%d日 %H:%M:%S')}*",
            f"*评价范围: 决策、过程、产出、效益四个维度*",
            f"*评价方法: 标准化绩效评价体系*"
        ])
        
        final_report = "\n".join(report_parts)
        
        # 保存报告到文件 - 添加时间戳避免覆盖
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        report_filename = f"final_report_{timestamp}.md"
        
        if hasattr(self, '_project_repo') and self._project_repo:
            report_path = self._project_repo.docs.workdir / report_filename
        else:
            report_path = DEFAULT_WORKSPACE_ROOT / report_filename
        
        report_path.write_text(final_report, encoding='utf-8')
        
        logger.info(f"完整报告已保存到: {report_path}")
        
        if metrics_evaluation and metrics_evaluation.get('metrics_scores'):
            logger.info(f"📊 报告包含 {len(metrics_evaluation['metrics_scores'])} 个指标的详细评分")
            logger.info(f"📊 综合得分: {metrics_evaluation.get('total_score', 0):.2f}分")
        
        return final_report

