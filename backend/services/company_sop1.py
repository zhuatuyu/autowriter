"""
SOP1 Company - 指标体系生成与评分回写
"""
from pathlib import Path
from typing import Dict, Any, Optional, List

from metagpt.team import Team
from metagpt.environment import Environment
from metagpt.logs import logger
from metagpt.utils.project_repo import ProjectRepo
from metagpt.schema import Message
from metagpt.actions import UserRequirement

 # 角色延迟导入，避免在配置未设置前加载常量


class CompanySOP1:
    def __init__(self):
        self.team: Optional[Team] = None
        self.project_repo: Optional[ProjectRepo] = None

    async def process_message(self, project_config: Dict[str, Any], message: str, environment: Environment, file_paths: Optional[List[str]] = None) -> str:
        project_id = project_config.get('project_id', 'default_project')
        workspace_config = project_config.get('workspace', {})

        team = await self._get_or_create_team(project_id, environment, workspace_config)

        # 路由
        user_msg = Message(content=message, cause_by=UserRequirement)
        if file_paths:
            # 简化：直接注入上传目录的文件到uploads
            workspace_path = Path(workspace_config.get('base_path', f"workspace/{project_id}"))
            uploads_path = workspace_path / "uploads"
            uploads_path.mkdir(parents=True, exist_ok=True)
            for p in file_paths:
                try:
                    sp = Path(p)
                    if sp.exists() and sp.is_file():
                        tp = uploads_path / sp.name
                        if sp.resolve() != tp.resolve():
                            import shutil
                            shutil.copy2(sp, tp)
                except Exception as e:
                    logger.warning(f"复制文件失败: {p}: {e}")
        team.env.publish_message(user_msg)

        await team.run(n_round=3)
        return "SOP1完成：已生成并回写 metric_analysis_table.md"

    async def _get_or_create_team(self, project_id: str, environment: Environment, workspace_config: Dict[str, Any]) -> Team:
        if self.team:
            return self.team

        workspace_path = Path(workspace_config.get('base_path', f"workspace/{project_id}"))
        workspace_path.mkdir(parents=True, exist_ok=True)
        (workspace_path / "uploads").mkdir(exist_ok=True)

        self.project_repo = ProjectRepo(workspace_path).with_src_path(workspace_path)

        # 常量化后无需加载性能配置 YAML

        # 组建团队：TeamLeader(默认) + ProductManager + ArchitectMetric + MetricEvaluator（SOP1不需要PM）
        from backend.roles.custom_team_leader import CustomTeamLeader
        from backend.roles.product_manager import ProductManager
        from backend.roles.architect_metric import ArchitectMetric
        from backend.roles.metric_evaluator import MetricEvaluator
        team_leader = CustomTeamLeader()
        product_manager = ProductManager()
        architect_metric = ArchitectMetric()
        metric_evaluator = MetricEvaluator()

        # 注入repo
        for role in [team_leader, product_manager, architect_metric, metric_evaluator]:
            role._project_repo = self.project_repo

        team = Team(investment=10.0, environment=environment)
        team.hire([team_leader, product_manager, architect_metric, metric_evaluator])

        self.team = team
        return team

