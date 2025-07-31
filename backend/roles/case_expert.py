"""
🔍 案例专家（王磊） - 虚拟办公室的研究员
一个完全符合MetaGPT设计哲学的、由多个Action驱动的自动化案例研究智能体。
"""
import re
from metagpt.config2 import Config
import json
from metagpt.roles.role import Role, RoleReactMode
from metagpt.schema import Message
from metagpt.logs import logger
from pydantic import BaseModel, Field
from typing import Dict, List

from backend.roles.director import DirectorAgent # 引入DirectorAgent以进行类型检查
from backend.models.plan import Plan # 引入Plan模型
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
        name: str = "王磊", 
        profile: str = "case_expert", 
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

        # 4. 配置长文本模型
        qwen_long_config = Config.default()
        qwen_long_config.llm.model = "qwen-long-latest"

        # 5. 使用MetaGPT标准方式设置actions和react_mode，并为特定Action配置LLM
        actions = [
            CollectCaseLinks(),
            WebBrowseAndSummarizeCase(config=qwen_long_config),
            ConductCaseResearch(config=qwen_long_config)
        ]
        self.set_actions(actions)
        # 监听 DirectorAgent 的消息
        self._watch([DirectorAgent])
        # 设置为 REACT 模式，以便 _think 方法可以被调用
        self._set_react_mode(RoleReactMode.REACT.value)


    async def _think(self) -> bool:
        """思考如何响应观察到的消息，并设置下一步的动作"""
        logger.info(f"{self.profile}: _think 方法被调用，新消息数={len(self.rc.news)}")
        
        if not self.rc.news:
            logger.info(f"{self.profile}: 没有新消息")
            return False

        # 只处理最新的计划消息
        msg = self.rc.news[0]
        logger.info(f"{self.profile}: 处理消息，来源={msg.cause_by}")
        
        # 检查消息来源，使用字符串包含检查
        if 'DirectorAgent' not in str(msg.cause_by):
            logger.info(f"{self.profile}: 消息不是来自DirectorAgent，实际来源={msg.cause_by}, 类型={type(msg.cause_by).__name__}")
            return False

        # 解析计划
        try:
            plan_data = json.loads(msg.content)
            plan = Plan(**plan_data)
            
            # 查找分配给case_expert的任务
            case_tasks = [task for task in plan.tasks if task.agent == "case_expert"]
            logger.info(f"{self.profile}: 找到 {len(case_tasks)} 个分配给我的任务")
            
            if not case_tasks:
                logger.info(f"{self.profile}: 没有分配给我的任务")
                return False
                
            # 设置第一个任务
            self.task_topic = case_tasks[0].description
            logger.info(f"{self.profile}: 接收到任务 - {self.task_topic}")
            
            # 设置第一个Action
            self.rc.todo = self.actions[0]  # CollectCaseLinks
            logger.info(f"{self.profile}: 设置todo为 {self.rc.todo}")
            return True
            
        except Exception as e:
            logger.error(f"{self.profile}: 解析计划失败 - {e}")
            return False

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
            topic = getattr(self, 'task_topic', msg.content)
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
            # 获取 project_repo 从角色属性
            project_repo = getattr(self, 'project_repo', None)
            if not project_repo:
                raise ValueError("ProjectRepo not found in agent context!")
            
            summary_text = "\n\n---\n\n".join(f"**来源链接**: {url}\n\n**内容摘要**:\n{summary}" for url, summary in report.summaries.items())

            report_path = await todo.run(topic=topic, content=summary_text, project_repo=project_repo)
            ret = Message(
                content="",
                instruct_content=CaseReport(topic=topic, links=report.links, summaries=report.summaries, content=str(report_path)),
                role=self.profile,
                cause_by=todo,
            )
        else:
            # 默认情况，直接返回原消息
            ret = Message(content=topic, instruct_content=report, role=self.profile, cause_by=todo)

        self.rc.memory.add(ret)
        return ret