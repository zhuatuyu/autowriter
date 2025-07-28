"""
🔍 案例专家（王磊） - 虚拟办公室的研究员
一个完全符合MetaGPT设计哲学的、由多个Action驱动的自动化案例研究智能体。
"""
import re
from metagpt.roles.role import RoleReactMode
from metagpt.schema import Message
from metagpt.logs import logger
from pydantic import BaseModel, Field
from typing import Dict, List

from metagpt.roles.role import Role
from backend.actions.case_research import (
    CollectCaseLinks, 
    WebBrowseAndSummarizeCase, 
    ConductCaseResearch
)
from backend.tools.search_engine_alibaba import alibaba_search_engine

class CaseReport(BaseModel):
    """用于在研究流程中传递结构化数据的模型，模仿researcher.py中的Report"""
    topic: str
    links: Dict[str, List[str]] = Field(default_factory=dict)
    summaries: Dict[str, str] = Field(default_factory=dict)
    content: str = ""


class CaseExpertAgent(Role):
    """
    案例专家Agent，其工作流程被定义为一系列可重用的Actions:
    1. CollectCaseLinks: 收集相关链接
    2. WebBrowseAndSummarizeCase: 浏览并总结链接内容
    3. ConductCaseResearch: 撰写最终研究报告
    """
    def __init__(
        self, 
        name: str = "CaseExpert", 
        profile: str = "CaseExpert", 
        goal: str = "搜索、分析并提供与项目相关的深度案例研究报告",
        search_config: dict = None, # 允许外部传入搜索配置
        **kwargs
    ):
        # 1. Call super() first to correctly initialize the Pydantic model and context.
        super().__init__(
            name=name, 
            profile=profile, 
            goal=goal, 
            **kwargs
        )
        
        # 2. Now that self.config.workspace is initialized, set up dependent paths.
        self.cases_dir = self.config.workspace.path / "cases"
        self.cases_dir.mkdir(exist_ok=True, parents=True)

        # 3. Configure and initialize the search engine.
        default_search_config = {
            "api_key": "OS-ykkz87t4q83335yl",
            "endpoint": "http://default-0t01.platform-cn-shanghai.opensearch.aliyuncs.com",
            "workspace": "default",
            "service_id": "ops-web-search-001"
        }
        self.search_engine = alibaba_search_engine(search_config or default_search_config)

        # 4. 使用MetaGPT标准方式设置actions和react_mode
        self.set_actions([CollectCaseLinks, WebBrowseAndSummarizeCase, ConductCaseResearch])
        self._set_react_mode(RoleReactMode.BY_ORDER.value, len(self.actions))


    async def _act(self) -> Message:
        """
        通过按顺序执行预定义的Action来完成案例研究任务。
        完全模仿 Researcher._act 的逻辑，使用Pydantic模型传递状态。
        """
        logger.info(f"[{self.profile}] to do {self.rc.todo.name})")
        todo = self.rc.todo
        msg = self.rc.memory.get(k=1)[0]
        
        # 从消息中解析出结构化的CaseReport，如果不存在则初始化
        if isinstance(msg.instruct_content, CaseReport):
            report = msg.instruct_content
            topic = report.topic
        else:
            topic = msg.content
            report = CaseReport(topic=topic)

        # 根据当前Action执行不同操作，模仿Researcher的逻辑
        if isinstance(todo, CollectCaseLinks):
            # 为CollectCaseLinks设置search_engine
            todo.search_engine = self.search_engine
            links = await todo.run(topic=topic, links=report.links, summaries=report.summaries)
            ret = Message(
                content="", instruct_content=CaseReport(topic=topic, links=links), role=self.profile, cause_by=todo
            )
        elif isinstance(todo, WebBrowseAndSummarizeCase):
            summaries = await todo.run(topic=topic, links=report.links, summaries=report.summaries)
            ret = Message(
                content="", instruct_content=CaseReport(topic=topic, links=report.links, summaries=summaries), role=self.profile, cause_by=todo
            )
        elif isinstance(todo, ConductCaseResearch):
            content = await todo.run(topic=topic, links=report.links, summaries=report.summaries, output_dir=self.cases_dir)
            ret = Message(
                content="",
                instruct_content=CaseReport(topic=topic, links=report.links, summaries=report.summaries, content=str(content)),
                role=self.profile,
                cause_by=todo,
            )
        else:
            # 默认情况，直接返回原消息
            ret = Message(content=topic, instruct_content=report, role=self.profile, cause_by=todo)

        self.rc.memory.add(ret)
        return ret