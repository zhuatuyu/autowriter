"""
数据分析师（赵丽娅） - 数据分析专家
完全符合MetaGPT设计哲学的数据分析智能体
"""
from metagpt.roles.role import Role
from metagpt.schema import Message
from metagpt.logs import logger
from backend.actions.data_analyst_action import AnalyzeData, SummarizeAnalysis


class DataAnalystAgent(Role):
    """
    数据分析师（赵丽娅） - 数据分析专家
    负责分析用户上传的数据文件并生成分析报告
    """
    
    name: str = "赵丽娅"
    profile: str = "data_analyst"
    goal: str = "根据用户指令，分析数据文件并生成报告"
    constraints: str = "确保数据分析的准确性和可解释性"
    language: str = "zh-cn"

    def __init__(self, name: str = "赵丽娅", profile: str = "data_analyst", goal: str = "根据用户指令，分析数据文件并生成报告", **kwargs):
        super().__init__(**kwargs)
        
        # 设置actions
        actions = [AnalyzeData(), SummarizeAnalysis()]
        self.set_actions(actions)
        
        # 监听项目管理和用户需求
        self._watch(["ProjectManagerAgent", "UserRequirement"])

    async def _think(self) -> bool:
        """思考阶段：分析当前任务"""
        msg = self.rc.memory.get(k=1)[0]
        
        # 检查是否是数据分析任务
        if "数据分析" in msg.content or "分析数据" in msg.content or "上传" in msg.content:
            logger.info(f"{self.name} 识别到数据分析任务")
            return True
            
        return False

    async def _act(self) -> Message:
        """执行阶段：执行数据分析任务"""
        msg = self.rc.memory.get(k=1)[0]
        
        # 获取项目仓库
        project_repo = getattr(self, 'project_repo', None)
        if not project_repo:
            logger.error("ProjectRepo not found in agent context!")
            return Message(content="数据分析失败：缺少项目仓库", role=self.profile)
        
        try:
            # 查找上传的数据文件
            uploads_path = project_repo.get_path('uploads')
            if not uploads_path.exists():
                return Message(content="未找到上传的数据文件", role=self.profile)
            
            # 查找数据文件（CSV、Excel等）
            data_files = list(uploads_path.glob("*.csv")) + list(uploads_path.glob("*.xlsx")) + list(uploads_path.glob("*.xls"))
            
            if not data_files:
                return Message(content="未找到可分析的数据文件", role=self.profile)
            
            # 使用第一个找到的数据文件
            data_file = data_files[0]
            analysis_path = project_repo.get_path('analysis')
            
            # 执行数据分析
            analyze_action = AnalyzeData()
            report_path = await analyze_action.run(
                instruction="请对数据进行全面分析，包括描述性统计、数据质量检查、关键指标分析等",
                file_path=data_file,
                analysis_path=analysis_path
            )
            
            return Message(
                content=f"数据分析完成，报告已保存至：{report_path}",
                role=self.profile
            )
            
        except Exception as e:
            logger.error(f"数据分析失败: {e}")
            return Message(content=f"数据分析失败: {str(e)}", role=self.profile)