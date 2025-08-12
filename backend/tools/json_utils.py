#!/usr/bin/env python
"""
通用LLM JSON提取工具
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List


def extract_json_from_llm_response(response: str) -> Any:
    """
    从LLM文本回复中尽力提取并纠偏JSON，返回“可直接消费”的结构：
    - 若检测到顶层列表：返回 List[dict]
    - 若检测到顶层对象：
        - 若包含常见列表字段(metrics/data/items/list)：返回对应 List[dict]
        - 若像单个对象（含典型字段，如 name/metric_id）：返回 [dict]
        - 其他：返回原对象(dict)

    纠偏策略（按序尝试，命中即返回）：
    1) 直接 json.loads
    2) 解析 ```json ... ``` 代码块；若无则解析 ```...``` 任意代码块
    3) 匹配并解析首个 JSON 数组 [...]（括号配对）
    4) 匹配并解析首个 JSON 对象 {...}（括号配对）
    """
    text = response or ""

    # 基础预处理：去除常见不可见字符与成对中文引号尽量替换为英文
    text = text.replace("\uFEFF", "").replace("“", '"').replace("”", '"')

    def _normalize(obj: Any) -> Any:
        """将解析结果归一化为更易消费的结构（尽量返回列表）。"""
        if isinstance(obj, list):
            # 仅保留字典项，过滤掉异常字符串等
            return [item for item in obj if isinstance(item, dict)]

        if isinstance(obj, dict):
            # 常见列表字段（扩充：包含 performance_metrics）
            for key in ("metrics", "data", "items", "list", "results", "performance_metrics"):
                val = obj.get(key)
                if isinstance(val, list):
                    return [item for item in val if isinstance(item, dict)]

            # 单对象常见特征：含名称或指标ID
            indicative_keys = ("name", "metric_id", "一级指标", "二级指标")
            if any(k in obj for k in indicative_keys):
                return [obj]

            return obj

        return obj

    # 尝试1：直接解析
    try:
        return _normalize(json.loads(text))
    except Exception:
        pass

    # 尝试2：代码块（优先 json 标记，其次任意代码块）
    for pattern in (r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```"):
        try:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                candidate = match.group(1).strip()
                try:
                    return _normalize(json.loads(candidate))
                except Exception:
                    # 如果包含数组/对象壳，继续走配对提取
                    text = candidate
        except Exception:
            pass

    # 尝试3：优先匹配 JSON 数组 [...]（括号配对）
    start_idx = text.find('[')
    if start_idx != -1:
        bracket_count = 0
        end_idx = start_idx
        for i, ch in enumerate(text[start_idx:], start_idx):
            if ch == '[':
                bracket_count += 1
            elif ch == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i
                    break
        if bracket_count == 0:
            json_str = text[start_idx:end_idx + 1]
            try:
                return _normalize(json.loads(json_str))
            except Exception:
                pass

    # 尝试4：匹配 JSON 对象 {...}（括号配对）
    start_idx = text.find('{')
    if start_idx != -1:
        brace_count = 0
        end_idx = start_idx
        for i, ch in enumerate(text[start_idx:], start_idx):
            if ch == '{':
                brace_count += 1
            elif ch == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        if brace_count == 0:
            json_str = text[start_idx:end_idx + 1]
            try:
                return _normalize(json.loads(json_str))
            except Exception:
                pass

    raise ValueError("无法从LLM回复中提取有效JSON")

