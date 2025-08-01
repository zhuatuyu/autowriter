"""
✍️ 写作专家（张翰） - 完全符合MetaGPT原生架构的写作智能体
"""
from metagpt.roles.role import Role
from metagpt.schema import Message
from metagpt.logs import logger
from pydantic import BaseModel, Field
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
    ✍️ 写作专家（张翰） - 完全符合MetaGPT原生架构的写作智能体
    负责根据案例研究结果撰写高质量的结构化报告
    """
    
    name: str = "张翰"
    profile: str = "writer_expert"
    goal: str = "根据案例研究结果撰写高质量的结构化报告"
    constraints: str = "确保报告内容准确、结构清晰、语言专业"
    language: str = "zh-cn"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 设置actions
        actions = [WriteContent(), SummarizeText(), PolishContent(), ReviewContent()]
        self.set_actions(actions)
        
        # 监听案例专家和数据分析师的结果
        self._watch(["CaseExpertAgent", "DataAnalystAgent"])

    async def _think(self) -> bool:
        """思考阶段：分析当前任务"""
        msg = self.rc.memory.get(k=1)[0]
        
        # 检查是否是写作任务
        if "写作" in msg.content or "撰写" in msg.content or "报告" in msg.content:
            logger.info(f"{self.name} 识别到写作任务")
            return True
            
        return False

    async def _act(self) -> Message:
        """执行阶段：执行写作任务"""
        msg = self.rc.memory.get(k=1)[0]
        
        # 获取项目仓库
        project_repo = getattr(self, 'project_repo', None)
        if not project_repo:
            logger.error("ProjectRepo not found in agent context!")
            return Message(content="写作失败：缺少项目仓库", role=self.profile)
        
        try:
            # 获取案例研究结果
            case_reports_path = project_repo.get_path('research/cases')
            if case_reports_path.exists():
                case_files = list(case_reports_path.glob("*.md"))
                if case_files:
                    # 读取最新的案例报告
                    latest_case = max(case_files, key=lambda x: x.stat().st_mtime)
                    with open(latest_case, 'r', encoding='utf-8') as f:
                        case_content = f.read()
                else:
                    case_content = "暂无案例研究结果"
            else:
                case_content = "暂无案例研究结果"
            
            # 获取数据分析结果
            analysis_path = project_repo.get_path('analysis')
            if analysis_path.exists():
                analysis_files = list(analysis_path.glob("*.md"))
                if analysis_files:
                    # 读取最新的分析报告
                    latest_analysis = max(analysis_files, key=lambda x: x.stat().st_mtime)
                    with open(latest_analysis, 'r', encoding='utf-8') as f:
                        analysis_content = f.read()
                else:
                    analysis_content = "暂无数据分析结果"
            else:
                analysis_content = "暂无数据分析结果"
            
            # 合并内容
            source_content = f"## 案例研究结果\n\n{case_content}\n\n## 数据分析结果\n\n{analysis_content}"
            
            # 执行写作任务
            write_action = WriteContent()
            content = await write_action.run(
                topic="绩效评价报告",
                summary=source_content,
                project_repo=project_repo
            )
            
            # 润色内容
            polish_action = PolishContent()
            polished_content = await polish_action.run(
                content=content,
                project_repo=project_repo
            )
            
            # 审核内容
            review_action = ReviewContent()
            final_content = await review_action.run(
                content=polished_content,
                project_repo=project_repo
            )
            
            return Message(
                content=f"报告撰写完成，最终报告已保存",
                role=self.profile
            )
            
        except Exception as e:
            logger.error(f"写作失败: {e}")
            return Message(content=f"写作失败: {str(e)}", role=self.profile)