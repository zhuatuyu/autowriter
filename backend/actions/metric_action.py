#!/usr/bin/env python
"""
指标评分Action - 从writer_action中彻底独立
"""
from metagpt.actions import Action
from metagpt.logs import logger
from backend.tools.json_utils import extract_json_from_llm_response

from backend.config.performance_constants import (
    ENV_WRITER_BASE_SYSTEM,
    ENV_EVALUATION_TYPES,
    ENV_WRITER_EVALUATION_PROMPT_TEMPLATE,
    ENV_METRIC_PROMPT_SPEC,
)
from pathlib import Path
import re


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
                "grade": "良好"
            }
        """
        logger.info("📊 开始进行指标评分...")

        try:
            # 解析指标数据（使用通用提取工具，兼容代码块/松散JSON）
            metrics_data = extract_json_from_llm_response(metric_table_json)

            if isinstance(metrics_data, dict) and "error" in metrics_data:
                return {"error": "指标体系构建失败", "details": metrics_data}

            # extract_json_from_llm_response 已做归一化；此处只做最终兜底
            if isinstance(metrics_data, dict):
                metrics_data = [metrics_data]
            elif not isinstance(metrics_data, list):
                metrics_data = []

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

            # 将意见与得分回写至指标表md（若提供路径）
            if metric_table_md_path:
                try:
                    self._update_metric_table_md(metric_table_md_path, metrics_scores)
                    logger.info(f"📝 已回写评分与意见至: {metric_table_md_path}")
                except Exception as e:
                    logger.error(f"回写metric_analysis_table.md失败: {e}")

            total_score = round(sum(level1_scores.values()), 2)
            result = {
                "metrics_scores": metrics_scores,
                "level1_summary": level1_scores,
                "total_score": total_score,
            }

            logger.info(f"📊 指标评分完成，总分: {total_score:.2f}分")
            return result

        except Exception as e:
            logger.error(f"指标评分过程失败: {e}")
            return {"error": "指标评分失败", "details": str(e)}

    def _update_metric_table_md(self, md_path: str, metrics_scores: list[dict]) -> None:
        """在 metric_analysis_table.md 的 JSON 里为匹配的指标补充 opinion 与 score。"""
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

        # 建立评分映射（优先使用 metric_id，回退 name）
        score_map: dict[str, dict] = {}
        for item in metrics_scores:
            metric = item.get("metric", {})
            key = metric.get("metric_id") or metric.get("name")
            if key:
                score_map[key] = {"score": item.get("score", 0), "opinion": item.get("opinion", "")}

        # 回写至原列表（优先 metric_id，其次 name）
        matched_keys = set()
        for m in metrics_list:
            if not isinstance(m, dict):
                continue
            key = m.get("metric_id") or m.get("name")
            if key and key in score_map:
                m["score"] = score_map[key]["score"]
                m["opinion"] = score_map[key]["opinion"]
                matched_keys.add(key)

        # 若仍有未匹配的评分项，则追加为新记录，确保不丢分
        for key, so in score_map.items():
            if key in matched_keys:
                continue
            # 查找原始指标以附带基本字段
            origin = None
            for item in metrics_scores:
                metric = item.get("metric", {})
                if (metric.get("metric_id") or metric.get("name")) == key:
                    origin = metric
                    break
            base = {"metric_id": origin.get("metric_id") if origin else key,
                    "name": origin.get("name") if origin else key,
                    "category": origin.get("category") if origin else ""}
            base.update({"score": so.get("score", 0), "opinion": so.get("opinion", "")})
            metrics_list.append(base)

        # 写回 md（保持```json 块）
        from json import dumps
        new_json = dumps(metrics_list, ensure_ascii=False, indent=2)
        new_text = text[:code_block_match.start(1)] + new_json + text[code_block_match.end(1):]
        path.write_text(new_text, encoding="utf-8")

    async def _evaluate_single_metric(self, metric: dict, vector_store_path: str) -> tuple:
        """统一的配置驱动评价：根据评价类型从配置读取模板并执行"""
        metric_name = metric.get("name", "未知指标")
        evaluation_type = metric.get("evaluation_type", "")
        evaluation_points = metric.get("evaluation_points", [])
        scoring_method = metric.get("scoring_method", "")

        # RAG检索事实
        facts = await self._retrieve_metric_facts(metric_name, vector_store_path)

        # 从配置获取该评价类型的详细说明
        eval_cfg = ENV_EVALUATION_TYPES.get(evaluation_type, {})
        type_description = eval_cfg.get("description", "")
        scoring_guidance = eval_cfg.get("scoring_guidance", "")
        opinion_requirements = eval_cfg.get("opinion_requirements", "")

        # 指标级提示词组合规范
        spec_default = ENV_METRIC_PROMPT_SPEC.get('default', {})
        spec_type = ENV_METRIC_PROMPT_SPEC.get('by_evaluation_type', {}).get(evaluation_type, {})
        points_intro = spec_type.get('points_intro', spec_default.get('points_intro', '评价要点：'))
        point_bullet = spec_type.get('point_bullet', spec_default.get('point_bullet', '- '))
        scoring_method_intro = spec_type.get('scoring_method_intro', spec_default.get('scoring_method_intro', '评分方法：'))
        max_points = int(spec_default.get('max_points', 10))

        # 规范化评价要点
        if isinstance(evaluation_points, list):
            evaluation_points = evaluation_points[:max_points]
            points_str = points_intro + "\n" + "\n".join([f"{point_bullet}{pt}" for pt in evaluation_points]) if evaluation_points else points_intro + " 无"
        else:
            points_str = points_intro + "\n" + str(evaluation_points)

        # 规范化评分方法
        scoring_method = f"{scoring_method_intro}{scoring_method}" if scoring_method else f"{scoring_method_intro}无"

        if ENV_WRITER_EVALUATION_PROMPT_TEMPLATE:
            prompt = ENV_WRITER_EVALUATION_PROMPT_TEMPLATE.format(
                evaluation_type=evaluation_type or "标准评价",
                evaluation_points=points_str,
                facts=facts,
                scoring_method=scoring_method,
                type_description=type_description,
                scoring_guidance=scoring_guidance,
                opinion_requirements=opinion_requirements,
            )
        else:
            # 兜底模板
            prompt = f"请基于以下事实，按{evaluation_type or '标准评价'}进行评分。\n\n要点:\n{points_str}\n\n事实:\n{facts}\n\n评分方法:{scoring_method}"

        try:
            result = await self._aask(prompt, [ENV_WRITER_BASE_SYSTEM])
            parsed = extract_json_from_llm_response(result)
            return parsed.get("score", 0), parsed.get("opinion", "评价意见生成失败")
        except Exception as e:
            logger.error(f"统一评价失败: {e}")
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
                max_results=3,
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




