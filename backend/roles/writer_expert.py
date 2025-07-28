"""
写作专家Agent - 张翰 (React模式-内置决策核心)
负责报告内容撰写和文本创作
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import json
import re


from metagpt.schema import Message
from metagpt.logs import logger

from metagpt.roles.role import Role
from backend.configs.llm_provider import llm
# 导入公共工具


# 导入新的MetaGPT标准Actions
from backend.actions.writer_action import WriteContent, SummarizeText, PolishContent, ReviewContent

# 导入新的Prompt模块



class WriterExpertAgent(Role):




    """
    ✍️ 写作专家（张翰） - 具备内置决策能力的智能内容专家
    """
    def __init__(self, name: str = "WriterExpert", profile: str = "WriterExpert", goal: str = "...", **kwargs):
        super().__init__(name=name, profile=profile, goal=goal, actions=[WriteContent(), SummarizeText(), PolishContent(), ReviewContent()], **kwargs)