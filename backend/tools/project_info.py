#!/usr/bin/env python
"""
项目基本信息读取与格式化工具
读取 config/project01.yaml（或指定路径）中的 project_info 并格式化为提示词上下文
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import yaml


def load_project_info(config_path: str = 'config/project01.yaml') -> Dict[str, Any]:
    """读取项目配置文件，返回 project_info 字典（不存在时返回空字典）。"""
    try:
        path = Path(config_path)
        if not path.exists():
            return {}
        data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        info = data.get('project_info') or {}
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}


def get_project_info_text(config_path: str = 'config/project01.yaml') -> str:
    """将 project_info 格式化为提示词上下文文本。"""
    info = load_project_info(config_path)
    if not info:
        return ""

    lines = []

    def add(k: str, v: Any):
        if v:
            lines.append(f"- {k}: {v}")

    add("项目名称", info.get('project_name'))
    add("项目类型", info.get('project_type'))
    add("项目描述:", info.get('project_description'))
    add("省", info.get('province'))
    add("市", info.get('city'))
    add("县/区", info.get('county'))


    return "\n".join(lines)

