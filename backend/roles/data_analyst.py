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
from metagpt.roles.role import Role, RoleContext
from metagpt.config2 import Config
from backend.actions.data_analyst_action import AnalyzeData, SummarizeAnalysis
from backend.utils.project_repo import ProjectRepo

class DataAnalystAgent(Role):
    """
    📊 数据分析师（赵丽娅） - 虚拟办公室的数据专家
    """
    def __init__(self, name: str = "DataAnalyst", profile: str = "DataAnalyst", goal: str = "根据用户指令，分析数据文件并生成报告", project_repo: ProjectRepo = None, **kwargs):
        qwen_long_config = Config.default()
        qwen_long_config.llm.model = "qwen3-coder-plus"
        
        kwargs.pop('config', None)
        super().__init__(name=name, profile=profile, goal=goal, actions=[AnalyzeData(), SummarizeAnalysis()], config=qwen_long_config, **kwargs)
        self._set_react_mode(react_mode="by_order")
        self.project_repo = project_repo


    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}")
        todo = self.rc.todo

        # 从上下文中获取项目仓库，如果没有则使用传入的参数（用于测试）
        project_repo = self.project_repo
        if not project_repo:
            raise ValueError("ProjectRepo not found in agent context!")

        # 从记忆中获取消息，期望是包含'instruction'和'file_path'的JSON字符串
        msg = self.rc.memory.get(k=1)[0]
        try:
            data = json.loads(msg.content)
            instruction = data["instruction"]
            file_name = data["file_name"] # 应该是文件名，而不是完整路径
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"无法解析输入消息或缺少必要字段: {e}")
            return Message(content=f"错误：输入格式不正确。我需要一个包含 'instruction' 和 'file_name' 的JSON。", role="assistant")

        # 构建文件路径和分析产出路径
        file_path = project_repo.get_path('uploads', file_name)
        analysis_path = project_repo.get_path('analysis')
        analysis_path.mkdir(exist_ok=True)

        # 顺序执行Action
        if isinstance(todo, AnalyzeData):
            # 1. 分析数据
            analysis_result = await todo.run(
                instruction=instruction,
                file_path=file_path,
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
            report_path = analysis_path / f"analysis_report_{file_name}.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"分析报告已保存至: {report_path}")
            
            # 任务完成，框架会自动处理循环终止
            return Message(content=str(report_path), role="assistant", cause_by=SummarizeAnalysis)

        # 默认或错误状态
        logger.warning(f"未知的todo: {type(todo)}")
        return Message(content="任务执行出现未知错误。", role="assistant")