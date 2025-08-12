#!/usr/bin/env python
"""
DesignMetricSystem - 仅负责指标体系设计，输出标准化JSON
"""
from metagpt.actions import Action
from metagpt.logs import logger
from backend.tools.json_utils import extract_json_from_llm_response
from backend.config.architect_prompts import (
    METRICS_DESIGN_PROMPT as ENV_METRICS_DESIGN_PROMPT,
    ARCHITECT_BASE_SYSTEM as ENV_ARCHITECT_BASE_SYSTEM,
)


class DesignMetricSystem(Action):
    async def run(self, research_brief_text: str) -> list:
        """
        基于研究简报生成指标体系的标准JSON（list[dict]）。
        """
        base = ENV_METRICS_DESIGN_PROMPT or "请根据研究简报设计绩效指标体系。"
        # 提示词完全配置驱动：YAML 内已给出字段规范/枚举与约束，这里不再在代码层硬编码
        composed = f"研究简报（供参考，不得复制原文）：\n\n{research_brief_text[:6000]}\n\n{base}"
        resp = await self._aask(composed, [ENV_ARCHITECT_BASE_SYSTEM])
        data = extract_json_from_llm_response(resp)
        if isinstance(data, dict) and 'metrics' in data:
            data = data['metrics']
        if not isinstance(data, list):
            logger.warning("指标体系非列表格式，已包装为列表")
            data = [data]
        return data

