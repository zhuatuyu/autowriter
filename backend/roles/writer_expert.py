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

from metagpt.roles.role import Role, RoleReactMode
from metagpt.schema import Message
from metagpt.logs import logger
from pydantic import BaseModel, Field

from backend.roles.director import DirectorAgent
from backend.roles.case_expert import CaseExpertAgent
from backend.models.plan import Plan
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
    ✍️ 写作专家（张翰） - 具备内置决策能力的智能内容专家 (重构后)
    """
    def __init__(self, name: str = "张翰", profile: str = "writer_expert", goal: str = "根据案例研究结果撰写高质量的结构化报告", **kwargs):
        super().__init__(name=name, profile=profile, goal=goal, **kwargs)
        
        # 设置Actions和react模式
        self.set_actions([SummarizeText(), WriteContent(), PolishContent(), ReviewContent()])
        # 监听 DirectorAgent (获取计划) 和 CaseExpertAgent (获取原始材料)
        self._watch([DirectorAgent, CaseExpertAgent])
        self._set_react_mode(RoleReactMode.REACT.value)
        # 用于存储从计划中获取的任务主题
        self.task_topic: str = ""


    async def _think(self) -> bool:
        """思考如何响应观察到的消息，并设置下一步的动作"""
        if not self.rc.news:
            return False

        msg = self.rc.news[0]

        # 检查消息来源，使用字符串包含检查
        if 'DirectorAgent' in str(msg.cause_by):
            try:
                plan_data = json.loads(msg.content)
                plan = Plan(**plan_data)
                
                # 查找分配给writer_expert的任务
                writer_tasks = [task for task in plan.tasks if task.agent == "writer_expert"]
                if writer_tasks:
                    self.task_topic = writer_tasks[0].description
                    logger.info(f"{self.profile}: 接收到任务 - {self.task_topic}")
                    # 设置第一个Action
                    self.rc.todo = self.actions[0]  # SummarizeText
                    return True
                else:
                    logger.info(f"{self.profile}: 没有分配给我的任务")
                    return False
                    
            except Exception as e:
                logger.error(f"{self.profile}: 解析计划失败 - {e}")
                return False

        # Case 2: 收到案例分析材料，开始写作流程
        if msg.cause_by == CaseExpertAgent:
            if not self.task_topic:
                logger.warning(f"{self.profile}: 收到了案例材料，但没有任务主题，无法开始写作。")
                return False
            
            logger.info(f"{self.profile}: 收到了案例材料，准备开始写作任务: {self.task_topic}")
            source_content = msg.content # 假设CaseExpert的产出是文本内容
            report = WritingReport(topic=self.task_topic, source_content=source_content)
            self.rc.todo = self.actions[0] # SummarizeText
            # 将初始报告对象放入内存，供_act使用
            self.rc.memory.add(Message(content=source_content, instruct_content=report, role=self.profile))
            return True
        
        return False

    async def _act(self) -> Message:
        """
        通过按顺序执行预定义的Action来完成写作任务。
        """
        if not self.rc.todo:
            return None
            
        logger.info(f"[{self.profile}] to do {self.rc.todo.name}")
        todo = self.rc.todo
        # 获取最新的消息，它应该包含 WritingReport
        msg = self.rc.memory.get(k=1)[0]
        
        # 从消息中解析出结构化的WritingReport，如果不存在则初始化
        if isinstance(msg.instruct_content, WritingReport):
            report = msg.instruct_content
            topic = report.topic
        else:
            topic = getattr(self, 'task_topic', msg.content)
            report = WritingReport(topic=topic, source_content=msg.content)

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
            project_repo = getattr(self, 'project_repo', None)
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
            project_repo = getattr(self, 'project_repo', None)
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
            project_repo = getattr(self, 'project_repo', None)
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