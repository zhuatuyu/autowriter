"""
SOP2 Company - 章节写作（依赖SOP1生成的指标表）
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


class CompanySOP2:
    def __init__(self):
        self.team: Optional[Team] = None
        self.project_repo: Optional[ProjectRepo] = None

    async def process_message(self, project_config: Dict[str, Any], message: str, environment: Environment, file_paths: Optional[List[str]] = None) -> str:
        project_id = project_config.get('project_id', 'default_project')
        workspace_config = project_config.get('workspace', {})

        # 前置校验：必须存在指标表
        workspace_path = Path(workspace_config.get('base_path', f"workspace/{project_id}"))
        metrics_md = workspace_path / "docs" / "metric_analysis_table.md"
        if not metrics_md.exists():
            logger.error("缺少 metric_analysis_table.md，SOP2 退出")
            return "缺少 metric_analysis_table.md，请先运行 SOP1"

        # 进一步校验：尝试解析指标表中的 JSON
        try:
            import re as _re
            import json as _json
            text = metrics_md.read_text(encoding="utf-8")
            m = _re.search(r"```json\s*(.*?)\s*```", text, flags=_re.DOTALL)
            if not m:
                logger.error("metric_analysis_table.md 中未找到 JSON 代码块，SOP2 退出")
                return "metric_analysis_table.md 格式不正确（缺少```json ... ```），请检查 SOP1 输出"
            _json.loads(m.group(1))
        except Exception as e:
            logger.error(f"metric_analysis_table.md JSON 解析失败: {e}")
            return "metric_analysis_table.md JSON 解析失败，请先修复 SOP1 输出"

        team = await self._get_or_create_team(project_id, environment, workspace_config)

        user_msg = Message(content=message, cause_by=UserRequirement)
        team.env.publish_message(user_msg)
        await team.run(n_round=8)
        return "SOP2完成：章节写作与最终报告已生成"

    async def _get_or_create_team(self, project_id: str, environment: Environment, workspace_config: Dict[str, Any]) -> Team:
        if self.team:
            return self.team

        workspace_path = Path(workspace_config.get('base_path', f"workspace/{project_id}"))
        workspace_path.mkdir(parents=True, exist_ok=True)
        (workspace_path / "uploads").mkdir(exist_ok=True)

        self.project_repo = ProjectRepo(workspace_path).with_src_path(workspace_path)

        # 常量化后无需加载性能配置 YAML

        # 组建团队：TeamLeader + ProductManager + ArchitectContent + PM + SectionWriter
        from backend.roles.custom_team_leader import CustomTeamLeader
        from backend.roles.product_manager import ProductManager
        from backend.roles.architect_content import ArchitectContent
        from backend.roles.project_manager import ProjectManager as PM
        from backend.roles.section_writer import SectionWriter
        team_leader = CustomTeamLeader()
        product_manager = ProductManager()
        architect_content = ArchitectContent()
        project_manager = PM()
        section_writer = SectionWriter()

        # 注入repo（确保各角色能读写 workspace）
        for role in [product_manager, architect_content, section_writer]:
            role._project_repo = self.project_repo

        team = Team(investment=10.0, environment=environment)
        team.hire([team_leader, product_manager, architect_content, project_manager, section_writer])

        self.team = team
        return team

