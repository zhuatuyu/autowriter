#!/usr/bin/env python
"""
DesignMetricSystem - 仅负责指标体系设计，输出标准化JSON
"""
from metagpt.actions import Action
from metagpt.logs import logger
from backend.tools.json_utils import extract_json_from_llm_response
from backend.config.architect_prompts import (
    METRICS_DESIGN_PROMPT,   # 指标体系设计主提示词（字段规范/枚举/计分规则的生成约束）
    ARCHITECT_BASE_SYSTEM,   # 架构师系统提示（角色定位与目标）
)


class DesignMetricSystem(Action):
    async def run(self, research_brief_text: str) -> list:
        """
        基于研究简报生成指标体系的标准JSON（list[dict]）。
        """
        base = METRICS_DESIGN_PROMPT or "请根据研究简报设计绩效指标体系。"

        # 仅提取六键，避免简报附录（如"指标体系与评分摘要"）干扰设计
        brief_plain = ""
        try:
            brief_obj = extract_json_from_llm_response(research_brief_text)
            if isinstance(brief_obj, dict):
                # 只提取前六个键，排除附录内容
                order = ["项目情况", "资金情况", "重要事件", "政策引用", "推荐方法", "可借鉴网络案例"]
                parts = []
                for k in order:
                    v = brief_obj.get(k)
                    if isinstance(v, str) and v.strip():
                        parts.append(f"### {k}\n{v.strip()}")
                brief_plain = "\n\n".join(parts)
        except Exception:
            pass
        if not brief_plain:
            # 如果解析失败，直接截取前8000字符（增加长度）
            brief_plain = (research_brief_text or "")[:8000]

        # 提示词完全配置驱动：YAML 内已给出字段规范/枚举与约束
        composed = f"研究简报（供参考，不得复制原文）：\n\n{brief_plain}\n\n{base}"

        # 首次生成（增加输出长度限制）
        resp = await self._aask(composed, [ARCHITECT_BASE_SYSTEM])
        data = extract_json_from_llm_response(resp)
        if isinstance(data, dict) and 'metrics' in data:
            data = data['metrics']
        if not isinstance(data, list):
            logger.warning("指标体系非列表格式，已包装为列表")
            data = [data]

        # DEBUG: 输出设计结果详情
        logger.info(f"🔍 指标设计结果: 类型={type(data)}, 数量={len(data) if isinstance(data, list) else 'N/A'}")
        if isinstance(data, list):
            for i, metric in enumerate(data[:3]):  # 只显示前3个
                logger.info(f"  指标{i+1}: {metric.get('name', '无名称')} (ID: {metric.get('metric_id', '无ID')})")
            if len(data) > 3:
                logger.info(f"  ... 还有 {len(data)-3} 个指标")
        elif isinstance(data, dict):
            logger.info(f"  单指标: {data.get('name', '无名称')} (ID: {data.get('metric_id', '无ID')})")
        
        return data

