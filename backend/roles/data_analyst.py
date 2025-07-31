"""
数据分析师Agent - 赵丽娅
负责数据提取、分析和可视化
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List

from metagpt.schema import Message
from metagpt.logs import logger
from metagpt.roles.role import Role, RoleContext, RoleReactMode
from metagpt.config2 import Config

from backend.roles.director import DirectorAgent
from backend.models.plan import Plan
from backend.actions.data_analyst_action import AnalyzeData, SummarizeAnalysis
from backend.utils.project_repo import ProjectRepo

class DataAnalystAgent(Role):
    """
    📊 数据分析师（赵丽娅） - 虚拟办公室的数据专家 (重构后)
    """
    def __init__(self, name: str = "赵丽娅", profile: str = "data_analyst", goal: str = "根据用户指令，分析数据文件并生成报告", **kwargs):
        qwen_long_config = Config.default()
        qwen_long_config.llm.model = "qwen3-coder-plus"
        
        kwargs.pop('config', None)
        super().__init__(name=name, profile=profile, goal=goal, actions=[AnalyzeData(), SummarizeAnalysis()], config=qwen_long_config, **kwargs)
        self._watch([DirectorAgent])
        self._set_react_mode(react_mode=RoleReactMode.REACT.value)


    async def _think(self) -> bool:
        if not self.rc.news:
            return False

        msg = self.rc.news[0]
        # 检查消息来源，使用字符串包含检查
        if 'DirectorAgent' not in str(msg.cause_by):
            logger.info(f"{self.profile}: 消息不是来自DirectorAgent，实际来源={msg.cause_by}, 类型={type(msg.cause_by).__name__}")
            return False

        # 解析计划
        try:
            plan_data = json.loads(msg.content)
            plan = Plan(**plan_data)
            
            # 查找分配给data_analyst的任务
            data_tasks = [task for task in plan.tasks if task.agent == "data_analyst"]
            if not data_tasks:
                logger.info(f"{self.profile}: 没有分配给我的任务")
                return False
                
            # 设置第一个任务
            self.task_description = data_tasks[0].description
            logger.info(f"{self.profile}: 接收到任务 - {self.task_description}")
            
            # 设置第一个Action
            self.rc.todo = self.actions[0]  # AnalyzeData
            return True
            
        except Exception as e:
            logger.error(f"{self.profile}: 解析计划失败 - {e}")
            return False

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}")
        todo = self.rc.todo

        project_repo = getattr(self, 'project_repo', None)
        if not project_repo:
            raise ValueError("ProjectRepo not found in agent context!")

        # 使用任务描述而不是解析消息内容
        task_description = getattr(self, 'task_description', '分析数据')
        
        # 构建分析产出路径
        analysis_path = project_repo.get_path('analysis')
        analysis_path.mkdir(exist_ok=True)

        # 顺序执行Action
        if isinstance(todo, AnalyzeData):
            # 1. 分析数据
            analysis_result = await todo.run(
                instruction=task_description,
                file_path=None,  # 暂时不需要具体文件
                analysis_path=analysis_path
            )
            # 将结果传递给下一个Action
            return Message(content=str(analysis_result), role="assistant", cause_by=AnalyzeData)

        elif isinstance(todo, SummarizeAnalysis):
            # 2. 总结分析
            # 上一个Action的结果在记忆中
            analysis_result = self.rc.memory.get(k=1)[0].content
            report = await todo.run(analysis_result=analysis_result)
            
            # 保存报告
            report_path = analysis_path / f"analysis_report_{task_description[:20]}.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"分析报告已保存至: {report_path}")
            
            # 任务完成，框架会自动处理循环终止
            return Message(content=str(report_path), role="assistant", cause_by=SummarizeAnalysis)

        # 默认或错误状态
        logger.warning(f"未知的todo: {type(todo)}")
        return Message(content="任务执行出现未知错误。", role="assistant")