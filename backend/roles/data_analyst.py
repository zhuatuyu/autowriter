"""
数据分析师Agent - 赵丽娅
负责数据提取、分析和可视化
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import re # Added for regex in _execute_specific_task

from metagpt.schema import Message
from metagpt.logs import logger
from metagpt.roles.role import Role

from backend.configs.llm_provider import llm
from backend.actions.data_analyst_action import DataExtraction, DataAnalysis





class DataAnalystAgent(Role):
    """
    📊 数据分析师（赵丽娅） - 虚拟办公室的数据专家
    """
    def __init__(self, name: str = "DataAnalyst", profile: str = "DataAnalyst", goal: str = "进行数据收集、统计分析和可视化", **kwargs):
        super().__init__(name=name, profile=profile, goal=goal, actions=[DataExtraction(), DataAnalysis()], **kwargs)