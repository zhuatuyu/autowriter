"""
🔍 案例专家（王磊） - 虚拟办公室的研究员
一个完全符合MetaGPT设计哲学的、由多个Action驱动的自动化案例研究智能体。
"""
import re
import os
from metagpt.config2 import Config
import json
from metagpt.roles.role import Role, RoleReactMode
from metagpt.schema import Message
from metagpt.logs import logger
from pydantic import BaseModel, Field
from typing import Dict, List, TYPE_CHECKING

# 使用TYPE_CHECKING避免循环导入
if TYPE_CHECKING:
    from backend.roles.project_manager import ProjectManagerAgent

from backend.actions.case_research import CollectCaseLinks, WebBrowseAndSummarizeCase, ConductCaseResearch
from metagpt.tools.search_engine import SearchEngine
from metagpt.config2 import config

class CaseReport(BaseModel):
    """用于在研究流程中传递结构化数据的模型，模仿researcher.py中的Report"""
    topic: str
    links: Dict[str, List[str]] = Field(default_factory=dict)
    summaries: Dict[str, str] = Field(default_factory=dict)
    content: str = ""


class CaseExpertAgent(Role):
    """
    🔍 案例专家（王磊） - 虚拟办公室的研究员
    一个完全符合MetaGPT设计哲学的、由多个Action驱动的自动化案例研究智能体。
    完全模仿 metagpt.roles.researcher.Researcher 的实现。
    """
    name: str = "王磊"
    profile: str = "案例专家"
    goal: str = "收集信息并进行案例研究"
    constraints: str = "确保信息的准确性和相关性"
    language: str = "zh-cn"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 1. 从config2.yaml加载搜索配置并初始化SearchEngine
        search_config = config.search
        if not search_config or not search_config.api_key:
            raise ValueError("Search config with api_key is not configured in config2.yaml")

        # 使用 SearchEngine.from_search_config 方法正确初始化搜索引擎
        # 这会自动处理所有配置参数，包括 params 字典中的阿里云特定参数
        self.search_engine = SearchEngine.from_search_config(search_config)

        # 2. 配置长文本模型
        qwen_long_config = Config.default()
        qwen_long_config.llm.model = "qwen-long-latest"

        # 3. 使用MetaGPT标准方式设置actions和react_mode，完全模仿researcher.py
        actions = [
            CollectCaseLinks(),
            WebBrowseAndSummarizeCase(config=qwen_long_config),
            ConductCaseResearch(config=qwen_long_config)
        ]
        self.set_actions(actions)
        # 监听 ProjectManagerAgent 的消息 - 使用字符串避免循环导入
        self._watch(["ProjectManagerAgent"])
        # 设置为 BY_ORDER 模式，完全模仿researcher.py的实现
        self._set_react_mode(RoleReactMode.BY_ORDER.value, len(self.actions))


    async def _act(self) -> Message:
        """
        通过按顺序执行预定义的Action来完成案例研究任务。
        完全模仿 Researcher._act 的逻辑，使用Pydantic模型传递状态。
        """
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo
        msg = self.rc.memory.get(k=1)[0]
        
        # 从消息中解析出结构化的CaseReport，如果不存在则初始化
        if isinstance(msg.instruct_content, CaseReport):
            report = msg.instruct_content
            topic = report.topic
        else:
            topic = msg.content
            report = CaseReport(topic=topic)

        # 根据当前Action执行不同操作，完全模仿Researcher的逻辑
        if isinstance(todo, CollectCaseLinks):
            # 直接传递search_engine参数，而不是设置属性
            links = await todo.run(topic=topic, links=report.links, summaries=report.summaries, search_engine=self.search_engine)
            ret = Message(
                content="", instruct_content=CaseReport(topic=topic, links=links), role=self.profile, cause_by=todo
            )
            
        elif isinstance(todo, WebBrowseAndSummarizeCase):
            summaries = await todo.run(topic=topic, links=report.links, summaries=report.summaries)
            ret = Message(
                content="", instruct_content=CaseReport(topic=topic, links=report.links, summaries=summaries), role=self.profile, cause_by=todo
            )
            
        elif isinstance(todo, ConductCaseResearch):
            # 获取 project_repo 从角色属性
            project_repo = getattr(self, 'project_repo', None)
            if not project_repo:
                raise ValueError("ProjectRepo not found in agent context!")
            
            summary_text = "\n\n---\n\n".join(f"**来源链接**: {url}\n\n**内容摘要**:\n{summary}" for url, summary in report.summaries.items())

            report_path = await todo.run(topic=topic, content=summary_text, project_repo=project_repo)
            
            ret = Message(
                content=f"案例研究完成：{topic}",
                instruct_content=CaseReport(topic=topic, links=report.links, summaries=report.summaries, content=str(report_path)),
                role=self.profile,
                cause_by=todo,
            )
            
        else:
            # 默认情况，直接返回原消息
            ret = Message(content=topic, instruct_content=report, role=self.profile, cause_by=todo)

        self.rc.memory.add(ret)
        return ret