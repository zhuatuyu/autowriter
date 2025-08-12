#!/usr/bin/env python
"""
指标评分Action - 从writer_action中彻底独立（SOP1 指标评价，内联实现）
"""
from metagpt.actions import Action
from metagpt.logs import logger
from backend.tools.json_utils import extract_json_from_llm_response

from backend.config.evaluation_standards import EVALUATION_TYPES as ENV_EVALUATION_TYPES
from backend.config.evaluator_prompts import (
    EVALUATOR_BASE_SYSTEM as ENV_EVALUATOR_BASE_SYSTEM,
    EVALUATION_PROMPT_TEMPLATE as ENV_EVALUATOR_PROMPT_TEMPLATE,
    METRIC_PROMPT_SPEC as ENV_METRIC_PROMPT_SPEC,
)
from pathlib import Path
import re
from backend.tools.project_info import get_project_info_text


class EvaluateMetrics(Action):
    """
    指标评分Action - 按照标准化评价类型进行指标评分
    为每个指标生成评价意见和具体得分
    """

    async def run(self, metric_table_json: str, vector_store_path: str, metric_table_md_path: str | None = None) -> dict:
        """
        对所有指标进行评分，返回评分结果

        Returns:
            dict: {
                "metrics_scores": [{"metric": {}, "score": 85.5, "opinion": "评价意见"}],
                "level1_summary": {"决策": 12.5, "过程": 22.3, "产出": 30.1, "效益": 20.6},
                "total_score": 85.5,
            }
        """
        logger.info("📊 开始进行指标评分...")

        try:
            # 优先从文件读取，避免经由消息上下文传递造成污染
            metrics_data = None
            if metric_table_md_path:
                path = Path(metric_table_md_path)
                if path.exists():
                    text = path.read_text(encoding="utf-8")
                    m = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL)
                    if m:
                        metrics_data = extract_json_from_llm_response(m.group(1))
            if metrics_data is None:
                # 回退：解析传入的 JSON 字符串（兼容代码块/松散JSON）
                metrics_data = extract_json_from_llm_response(metric_table_json)

            if isinstance(metrics_data, dict) and "error" in metrics_data:
                return {"error": "指标体系构建失败", "details": metrics_data}

            # extract_json_from_llm_response 已做归一化；此处只做最终兜底
            if isinstance(metrics_data, dict):
                metrics_data = [metrics_data]
            elif not isinstance(metrics_data, list):
                metrics_data = []

            # 为每个指标进行评分（严格对齐 SOP1 扁平英文字段结构）
            metrics_scores = []

            for metric in metrics_data:
                try:
                    # 执行单个指标评分
                    score, opinion = await self._evaluate_single_metric(metric, vector_store_path)

                    metrics_scores.append({
                        "metric": metric,
                        "score": score,
                        "opinion": opinion,
                    })

                    logger.info(f"✅ 完成指标评分: {metric.get('name', '未知指标')} - {score}分")

                except Exception as e:
                    logger.error(f"指标评分失败: {metric.get('name', '未知指标')} - {e}")


            # 将意见与得分回写至指标表md（若提供路径）
            if metric_table_md_path:
                try:
                    self._update_metric_table_md(metric_table_md_path, metrics_scores)
                    logger.info(f"📝 已回写评分与意见至: {metric_table_md_path}")
                except Exception as e:
                    logger.error(f"回写metric_analysis_table.md失败: {e}")

            result = {"metrics_scores": metrics_scores}
            logger.info("📊 指标评分完成，已回写每项 score/opinion")
            return result

        except Exception as e:
            logger.error(f"指标评分过程失败: {e}")
            return {"error": "指标评分失败", "details": str(e)}

    def _update_metric_table_md(self, md_path: str, metrics_scores: list[dict]) -> None:
        """在 metric_analysis_table.md 的 JSON 里为匹配的指标补充 opinion 与 score（优先按 metric_id，其次按 name）。"""
        path = Path(md_path)
        if not path.exists():
            raise FileNotFoundError(f"未找到文件: {md_path}")

        text = path.read_text(encoding="utf-8")

        # 提取 ```json ... ``` 代码块
        code_block_match = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL)
        if not code_block_match:
            raise ValueError("metric_analysis_table.md 内未找到JSON代码块")

        json_str = code_block_match.group(1)
        data = extract_json_from_llm_response(json_str)

        # 归一为列表
        if isinstance(data, dict):
            metrics_list = [data]
        elif isinstance(data, list):
            metrics_list = data
        else:
            raise ValueError("metric_analysis_table.md 中JSON不是对象或数组")

        # 建立评分映射（优先 metric_id，其次 name）
        score_map_id: dict[str, dict] = {}
        score_map_name: dict[str, dict] = {}
        for item in metrics_scores:
            metric = item.get("metric", {})
            mid = metric.get("metric_id")
            mname = metric.get("name")
            payload = {"score": item.get("score", 0), "opinion": item.get("opinion", "")}
            if mid:
                score_map_id[mid] = payload
            if mname:
                score_map_name[mname] = payload

        # 回写至原列表（按 metric_id）
        matched_ids = set()
        matched_names = set()
        for m in metrics_list:
            if not isinstance(m, dict):
                continue
            key_id = m.get("metric_id")
            key_name = m.get("name")
            if key_id and key_id in score_map_id:
                m["score"] = score_map_id[key_id]["score"]
                m["opinion"] = score_map_id[key_id]["opinion"]
                matched_ids.add(key_id)
            elif key_name and key_name in score_map_name:
                m["score"] = score_map_name[key_name]["score"]
                m["opinion"] = score_map_name[key_name]["opinion"]
                matched_names.add(key_name)

        # 不再追加新记录：仅更新匹配项，保持初始结构稳定

        # 写回 md（保持```json 块）
        from json import dumps
        new_json = dumps(metrics_list, ensure_ascii=False, indent=2)
        new_text = text[:code_block_match.start(1)] + new_json + text[code_block_match.end(1):]
        path.write_text(new_text, encoding="utf-8")

    async def _evaluate_single_metric(self, metric: dict, vector_store_path: str) -> tuple:
        """统一的配置驱动评价：根据评价类型从配置读取模板并执行"""
        metric_name = metric.get("name", "未知指标")
        evaluation_type = metric.get("evaluation_type", "")
        evaluation_points = metric.get("evaluation_points", "")
        scoring_method = metric.get("scoring_method", "")

        logger.info(f"🔍 开始评价指标: {metric_name} (类型: {evaluation_type})")

        # RAG检索事实
        facts = await self._retrieve_metric_facts(metric_name, vector_store_path)
        logger.info(f"📚 检索到事实依据: {len(facts)} 字符")

        # 从配置获取该评价类型的详细说明
        eval_cfg = ENV_EVALUATION_TYPES.get(evaluation_type, {})
        type_description = eval_cfg.get("description", "")
        scoring_guidance = eval_cfg.get("scoring_guidance", "")
        opinion_requirements = eval_cfg.get("opinion_requirements", "")

        logger.info(f"📋 评价类型配置: {type_description}")
        logger.info(f"📝 评价意见要求: {len(opinion_requirements)} 字符")

        # 指标级提示词组合规范
        spec_default = ENV_METRIC_PROMPT_SPEC.get('default', {})
        spec_type = ENV_METRIC_PROMPT_SPEC.get('by_evaluation_type', {}).get(evaluation_type, {})
        points_intro = spec_type.get('points_intro', spec_default.get('points_intro', '评价要点：'))
        point_bullet = spec_type.get('point_bullet', spec_default.get('point_bullet', '① '))
        scoring_method_intro = spec_type.get('scoring_method_intro', spec_default.get('scoring_method_intro', '评分方法：'))
        max_points = int(spec_default.get('max_points', 10))

        # 规范化评价要点 - evaluation_points现在是包含评价要素和计分规则的文本
        if evaluation_points:
            # 直接使用evaluation_points文本，因为它已经包含了完整的评价要素和计分规则
            points_str = points_intro + "\n" + evaluation_points
            logger.info(f"📊 评价要点格式化完成: {len(points_str)} 字符")
        else:
            points_str = points_intro + " 无"
            logger.warning("⚠️ 评价要点为空")

        # 规范化评分方法 - 如果scoring_method为空，可以从evaluation_points中提取
        if scoring_method:
            scoring_method = f"{scoring_method_intro}{scoring_method}"
        else:
            # 如果scoring_method为空，尝试从evaluation_points中提取计分规则
            if "得分" in evaluation_points or "分值" in evaluation_points:
                scoring_method = f"{scoring_method_intro}计分规则已在评价要点中明确"
            else:
                scoring_method = f"{scoring_method_intro}无"

        if ENV_EVALUATOR_PROMPT_TEMPLATE:
            prompt = ENV_EVALUATOR_PROMPT_TEMPLATE.format(
                evaluation_type=evaluation_type or "标准评价",
                evaluation_points=points_str,
                facts=facts,
                scoring_method=scoring_method,
                type_description=type_description,
                scoring_guidance=scoring_guidance,
                opinion_requirements=opinion_requirements,
            )
            logger.info(f"📝 提示词模板生成完成: {len(prompt)} 字符")
        else:
            # 兜底模板
            prompt = f"请基于以下事实，按{evaluation_type or '标准评价'}进行评分。\n\n要点:\n{points_str}\n\n事实:\n{facts}\n\n评分方法:{scoring_method}"
            logger.warning("⚠️ 使用兜底提示词模板")

        try:
            project_info_text = get_project_info_text()
            logger.info("🤖 开始调用LLM进行评分...")
            result = await self._aask(prompt, [ENV_EVALUATOR_BASE_SYSTEM, project_info_text])
            logger.info(f"🤖 LLM响应完成: {len(result)} 字符")
            
            # 解析JSON响应
            parsed = extract_json_from_llm_response(result)
            logger.info(f"🔍 JSON解析结果类型: {type(parsed)}")
            
            # 只接受单对象；若返回列表/包裹，则判定为非法，直接置0并回写解析失败说明
            if isinstance(parsed, dict):
                item = parsed
                logger.info(f"✅ 成功解析JSON对象，包含键: {list(item.keys())}")
            else:
                raise ValueError(f"评分结果必须为单个JSON对象，且仅包含score/opinion 两个键，实际类型: {type(parsed)}")
            
            score_val = item.get("score")
            if not isinstance(score_val, (int, float)):
                raise ValueError(f"score必须为数值(0-100)，禁止字符串/百分号/文字，实际值: {score_val}")
            
            score = float(score_val)
            opinion = item.get("opinion") or ""
            
            logger.info(f"✅ 指标评分成功: {metric_name} - {score}分")
            logger.info(f"📝 评价意见: {opinion[:100]}...")
            
            return score, opinion
            
        except Exception as e:
            logger.error(f"❌ 统一评价失败: {e}")
            logger.error(f"📝 原始LLM响应: {result[:200]}...")
            return 0, f"统一评价过程中出现错误：{str(e)}"

    async def _retrieve_metric_facts(self, metric_name: str, vector_store_path: str) -> str:
        """🧠 使用智能检索服务为指标检索相关事实依据"""
        try:
            from backend.services.intelligent_search import intelligent_search

            primary_query = f"{metric_name} 的具体数据、完成情况和实施效果"

            search_result = await intelligent_search.intelligent_search(
                query=primary_query,
                project_vector_storage_path=vector_store_path,
                mode="hybrid",
                enable_global=True,
                max_results=5,
            )

            if search_result.get("results"):
                facts = "\n\n".join(search_result["results"])
                if search_result.get("insights"):
                    facts += "\n\n💡 智能分析:\n" + "\n".join(search_result["insights"])
                return facts
            return f"未能检索到关于'{metric_name}'的相关事实依据。"
        except Exception as e:
            logger.error(f"智能检索指标事实失败: {e}")
            return f"检索失败，无法获取关于'{metric_name}'的事实依据。"


