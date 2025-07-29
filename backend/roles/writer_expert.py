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

from metagpt.roles.role import RoleReactMode
from metagpt.schema import Message
from metagpt.logs import logger
from pydantic import BaseModel, Field

from metagpt.roles.role import Role

# 导入公共工具

# 导入新的MetaGPT标准Actions
from backend.actions.writer_action import WriteContent, SummarizeText, PolishContent, ReviewContent

# 导入新的Prompt模块

class WritingReport(BaseModel):
    """用于在写作流程中传递结构化数据的模型"""
    topic: str
    source_content: str = ""
    summary: str = ""
    content: str = ""
    polished_content: str = ""

class WriterExpertAgent(Role):
    """
    ✍️ 写作专家（张翰） - 具备内置决策能力的智能内容专家
    """
    def __init__(self, name: str = "WriterExpert", profile: str = "WriterExpert", goal: str = "根据案例研究结果撰写高质量的结构化报告", **kwargs):
        super().__init__(name=name, profile=profile, goal=goal, **kwargs)
        
        # 设置Actions和react模式
        self.set_actions([SummarizeText(), WriteContent(), PolishContent(), ReviewContent()])
        self._set_react_mode(RoleReactMode.BY_ORDER.value, len(self.actions))

    async def _act(self) -> Message:
        """
        通过按顺序执行预定义的Action来完成写作任务。
        """
        logger.info(f"[{self.profile}] to do {self.rc.todo.name}")
        todo = self.rc.todo
        msg = self.rc.memory.get(k=1)[0]
        
        # 从消息中解析出结构化的WritingReport，如果不存在则初始化
        # 统一从消息中获取内容，无论是直接内容还是文件内容
        source_content = msg.content
        # 尝试从instruct_content中获取更详细的上下文，但这不再是主要逻辑
        topic = msg.instruct_content.topic if hasattr(msg, 'instruct_content') and hasattr(msg.instruct_content, 'topic') else "基于提供内容的报告"
        
        report = WritingReport(topic=topic, source_content=source_content)

        # 根据当前Action执行不同操作
        if isinstance(todo, SummarizeText):
            summary = await todo.run(content=report.source_content)
            ret = Message(
                content="", 
                instruct_content=WritingReport(
                    topic=topic, 
                    source_content=report.source_content,
                    summary=summary
                ), 
                role=self.profile, 
                cause_by=todo
            )
        elif isinstance(todo, WriteContent):
            # 获取 project_repo 从上下文
            project_repo = self.context.kwargs.get('project_repo')
            if not project_repo:
                raise ValueError("ProjectRepo not found in agent context!")
            
            content = await todo.run(topic=topic, summary=report.summary, project_repo=project_repo)
            ret = Message(
                content="", 
                instruct_content=WritingReport(
                    topic=topic, 
                    source_content=report.source_content,
                    summary=report.summary,
                    content=content
                ), 
                role=self.profile, 
                cause_by=todo
            )
        elif isinstance(todo, PolishContent):
            # 获取 project_repo 从上下文
            project_repo = self.context.kwargs.get('project_repo')
            if not project_repo:
                raise ValueError("ProjectRepo not found in agent context!")
            
            polished_content = await todo.run(content=report.content, project_repo=project_repo)
            ret = Message(
                content="", 
                instruct_content=WritingReport(
                    topic=topic, 
                    source_content=report.source_content,
                    summary=report.summary,
                    content=report.content,
                    polished_content=polished_content
                ), 
                role=self.profile, 
                cause_by=todo
            )
        elif isinstance(todo, ReviewContent):
            # 获取 project_repo 从上下文
            project_repo = self.context.kwargs.get('project_repo')
            if not project_repo:
                raise ValueError("ProjectRepo not found in agent context!")
            
            final_content = await todo.run(content=report.polished_content, project_repo=project_repo)
            ret = Message(
                content=f"写作任务完成：{topic}",
                instruct_content=WritingReport(
                    topic=topic, 
                    source_content=report.source_content,
                    summary=report.summary,
                    content=report.content,
                    polished_content=final_content
                ), 
                role=self.profile, 
                cause_by=todo
            )
        else:
            # 默认情况，直接返回原消息
            ret = Message(content=topic, instruct_content=report, role=self.profile, cause_by=todo)

        self.rc.memory.add(ret)
        return ret