"""
✍️ 写作专家（张翰） - 完全模仿MetaGPT engineer.py的REACT模式实现
负责报告内容撰写和文本创作，采用标准的think-act循环
"""
import json
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from pathlib import Path

from metagpt.roles.role import Role, RoleReactMode
from metagpt.schema import Message
from metagpt.logs import logger
from pydantic import BaseModel, Field
from metagpt.utils.common import any_to_str

# 使用TYPE_CHECKING避免循环导入
if TYPE_CHECKING:
    from backend.roles.project_manager import ProjectManagerAgent
    from backend.roles.case_expert import CaseExpertAgent

from backend.models.plan import Plan
from backend.actions.writer_action import WriteContent, SummarizeText, PolishContent, ReviewContent

class WritingReport(BaseModel):
    """用于在写作流程中传递结构化数据的模型"""
    topic: str
    source_content: str = ""
    summary: str = ""
    content: str = ""
    polished_content: str = ""

class WriterExpertAgent(Role):
    """
    ✍️ 写作专家（张翰） - 完全模仿MetaGPT engineer.py的REACT模式实现
    采用标准的think-act循环，动态选择Action执行
    """
    
    name: str = "张翰"
    profile: str = "writer_expert"
    goal: str = "根据案例研究结果撰写高质量的结构化报告"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 设置Actions - 模仿engineer.py的方式
        self.set_actions([SummarizeText, WriteContent, PolishContent, ReviewContent])
        # 监听其他Agent的消息 - 使用字符串避免循环导入
        self._watch(["ProjectManagerAgent", "CaseExpertAgent"])
        # 使用REACT模式（默认模式，无需显式设置）
        # self._set_react_mode(RoleReactMode.REACT.value)  # 这是默认值
        
        # 存储任务相关信息
        self.task_topic: str = ""
        self.writing_report: Optional[WritingReport] = None


    async def _think(self) -> bool:
        """
        模仿engineer.py的_think方法实现
        根据接收到的消息类型，决定下一步要执行的Action
        """
        if not self.rc.news:
            return False

        msg = self.rc.news[0]
        logger.info(f"{self.profile}: 收到消息 from {msg.cause_by}")

        # 处理来自ProjectManagerAgent的计划消息
        if msg.cause_by == "ProjectManagerAgent":
            try:
                plan_data = json.loads(msg.content)
                plan = Plan(**plan_data)
                
                # 查找分配给writer_expert的任务
                writer_tasks = [task for task in plan.tasks if task.agent == "writer_expert"]
                if writer_tasks:
                    self.task_topic = writer_tasks[0].description
                    logger.info(f"{self.profile}: 接收到任务 - {self.task_topic}")
                    # 等待案例材料，暂不设置Action
                    return False
                else:
                    logger.info(f"{self.profile}: 没有分配给我的任务")
                    return False
                    
            except Exception as e:
                logger.error(f"{self.profile}: 解析计划失败 - {e}")
                return False

        # 处理来自CaseExpertAgent的案例材料
        elif msg.cause_by == "CaseExpertAgent":
            if not self.task_topic:
                logger.warning(f"{self.profile}: 收到了案例材料，但没有任务主题，无法开始写作。")
                return False
            
            logger.info(f"{self.profile}: 收到案例材料，开始写作任务: {self.task_topic}")
            # 初始化写作报告
            self.writing_report = WritingReport(
                topic=self.task_topic, 
                source_content=msg.content
            )
            # 设置第一个Action：SummarizeText
            self.rc.todo = self.actions[0]  # SummarizeText
            return True

        # 处理自己发送的消息（Action执行结果）
        elif msg.sent_from == any_to_str(self):
            # 根据消息的cause_by决定下一个Action
            if msg.cause_by == any_to_str(SummarizeText):
                self.rc.todo = self.actions[1]  # WriteContent
                return True
            elif msg.cause_by == any_to_str(WriteContent):
                self.rc.todo = self.actions[2]  # PolishContent
                return True
            elif msg.cause_by == any_to_str(PolishContent):
                self.rc.todo = self.actions[3]  # ReviewContent
                return True
            elif msg.cause_by == any_to_str(ReviewContent):
                # 写作流程完成
                logger.info(f"{self.profile}: 写作任务完成")
                self.rc.todo = None
                return False

        return False

    async def _act(self) -> Message:
        """
        模仿engineer.py的_act方法实现
        执行当前设定的Action
        """
        if not self.rc.todo:
            return None
            
        logger.info(f"{self.profile}: 执行 {self.rc.todo}")
        todo = self.rc.todo
        
        # 获取project_repo（如果需要）
        project_repo = getattr(self, 'project_repo', None)
        
        # 根据Action类型执行不同操作
        if isinstance(todo, SummarizeText):
            summary = await todo.run(content=self.writing_report.source_content)
            self.writing_report.summary = summary
            
            # 返回消息给自己，触发下一个Action
            return Message(
                content=f"总结完成: {summary[:100]}...",
                role=self.profile,
                cause_by=todo,
                sent_from=any_to_str(self),
                send_to=any_to_str(self)
            )
            
        elif isinstance(todo, WriteContent):
            if not project_repo:
                raise ValueError("ProjectRepo not found in agent context!")
            
            content = await todo.run(
                topic=self.writing_report.topic, 
                summary=self.writing_report.summary, 
                project_repo=project_repo
            )
            self.writing_report.content = content
            
            return Message(
                content=f"内容撰写完成: {len(content)} 字符",
                role=self.profile,
                cause_by=todo,
                sent_from=any_to_str(self),
                send_to=any_to_str(self)
            )
            
        elif isinstance(todo, PolishContent):
            if not project_repo:
                raise ValueError("ProjectRepo not found in agent context!")
            
            polished_content = await todo.run(
                content=self.writing_report.content, 
                project_repo=project_repo
            )
            self.writing_report.polished_content = polished_content
            
            return Message(
                content=f"内容润色完成: {len(polished_content)} 字符",
                role=self.profile,
                cause_by=todo,
                sent_from=any_to_str(self),
                send_to=any_to_str(self)
            )
            
        elif isinstance(todo, ReviewContent):
            if not project_repo:
                raise ValueError("ProjectRepo not found in agent context!")
            
            final_content = await todo.run(
                content=self.writing_report.polished_content, 
                project_repo=project_repo
            )
            
            # 写作任务完成，发送最终结果
            return Message(
                content=f"写作任务完成：{self.writing_report.topic}",
                instruct_content=WritingReport(
                    topic=self.writing_report.topic,
                    source_content=self.writing_report.source_content,
                    summary=self.writing_report.summary,
                    content=self.writing_report.content,
                    polished_content=final_content
                ),
                role=self.profile,
                cause_by=todo,
                sent_from=any_to_str(self),
                send_to="<all>"  # 发送给所有Agent
            )
        
        # 默认情况
        return await todo.run()