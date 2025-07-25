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

from backend.roles.base import BaseAgent
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


class CaseExpertAgent(BaseAgent):
    """
    案例专家Agent，其工作流程被定义为一系列可重用的Actions:
    1. CollectCaseLinks: 收集相关链接
    2. WebBrowseAndSummarizeCase: 浏览并总结链接内容
    3. ConductCaseResearch: 撰写最终研究报告
    """
    def __init__(
        self, 
        agent_id: str = "case_expert", 
        session_id: str = None, 
        workspace_path: str = None, 
        memory_manager=None,
        search_config: dict = None # 允许外部传入搜索配置
    ):
        super().__init__(
            agent_id=agent_id,
            session_id=session_id,
            workspace_path=workspace_path,
            memory_manager=memory_manager,
            role="案例专家",
            profile="王磊",
            goal="搜索、分析并提供与项目相关的深度案例研究报告"
        )
        
        # 1. 配置并初始化搜索引擎
        default_search_config = {
            "api_key": "OS-ykkz87t4q83335yl",
            "endpoint": "http://default-0t01.platform-cn-shanghai.opensearch.aliyuncs.com",
            "workspace": "default",
            "service_id": "ops-web-search-001"
        }
        self.search_engine = alibaba_search_engine(search_config or default_search_config)
        
        # 2. 注册Action工作流
        self.set_actions([
            CollectCaseLinks,
            WebBrowseAndSummarizeCase,
            ConductCaseResearch,
        ])
        
        # 3. 设置为顺序执行模式
        self._set_react_mode(react_mode=RoleReactMode.BY_ORDER.value)
        
        # 创建工作子目录
        self.cases_dir = self.agent_workspace / "cases"
        self.cases_dir.mkdir(exist_ok=True)


    async def _act(self) -> Message:
        """
        通过按顺序执行预定义的Action来完成案例研究任务。
        完全模仿 Researcher._act 的逻辑，使用Pydantic模型传递状态。
        """
        logger.info(f"[{self.profile}] to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo
        msg = self.rc.memory.get(k=1)[0]
        
        # 从消息中解析出结构化的CaseReport，如果不存在则初始化
        if isinstance(msg.instruct_content, CaseReport):
            report = msg.instruct_content
            topic = report.topic
        else:
            topic = msg.content
            report = CaseReport(topic=topic)

        # 根据当前Action执行不同操作
        if isinstance(todo, CollectCaseLinks):
            links = await todo.run(topic=topic, search_engine=self.search_engine)
            report.links = links
            ret = Message(content=topic, instruct_content=report, role=self.profile, cause_by=todo)

        elif isinstance(todo, WebBrowseAndSummarizeCase):
            links = report.links
            summaries = await todo.run(links=links)
            report.summaries = summaries
            ret = Message(content=topic, instruct_content=report, role=self.profile, cause_by=todo)

        elif isinstance(todo, ConductCaseResearch):
            summaries = report.summaries
            report_path = await todo.run(topic=topic, summaries=summaries, output_dir=self.cases_dir)
            report.content = str(report_path)
            ret = Message(content=str(report_path), instruct_content=report, role=self.profile, cause_by=todo)
        
        else:
            logger.warning(f"未知或不支持的Action: {type(todo)}")
            ret = Message(content="任务执行失败，遇到未知Action", role=self.profile, cause_by=todo)
            
        self.rc.memory.add(ret)
        return ret 