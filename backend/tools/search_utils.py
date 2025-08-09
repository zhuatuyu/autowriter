#!/usr/bin/env python
"""
搜索与检索相关的通用工具函数
"""
from __future__ import annotations

from typing import Any, List


def normalize_keywords(raw_list: Any, topic: str) -> List[str]:
    """将 LLM 产出的关键词结构（可能为字符串、dict、混合）统一规范为字符串列表。

    - 输入可以是 str / dict / list[ str | dict | Any ]
    - dict 常见结构: {"category": "..", "keywords": ["k1","k2"]}
    - 其余情况尽量转为字符串并去空、去重
    - 若最终为空，回退为基于 topic 的单一关键词
    """
    normalized: List[str] = []

    if isinstance(raw_list, str):
        raw_list = [raw_list]

    if not isinstance(raw_list, list):
        return [str(raw_list)] if raw_list is not None else [topic[:50]]

    for item in raw_list:
        if isinstance(item, str):
            text = item.strip()
            if text:
                normalized.append(text)
        elif isinstance(item, dict):
            kws = item.get("keywords")
            if isinstance(kws, list):
                for k in kws:
                    k = str(k).strip()
                    if k:
                        normalized.append(k)
            else:
                for v in item.values():
                    if isinstance(v, list):
                        for k in v:
                            k = str(k).strip()
                            if k:
                                normalized.append(k)
                    else:
                        v = str(v).strip()
                        if v:
                            normalized.append(v)
        else:
            s = str(item).strip()
            if s:
                normalized.append(s)

    # 去重保序
    seen = set()
    deduped: List[str] = []
    for k in normalized:
        if k not in seen:
            seen.add(k)
            deduped.append(k)

    return deduped or [topic[:50]]

