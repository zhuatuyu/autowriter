#!/usr/bin/env python
"""
app_agent_sectionwriter.py - 仅运行 SectionWriter 进行章节写作（已具备 report_structure.json 与 research_brief.md）

用法：python app_agent_sectionwriter.py -y config/project01.yaml
前置：
- workspace/<project>/docs/report_structure.json 已生成
- workspace/<project>/docs/research_brief.md 已生成
- workspace/<project>/docs/metric_analysis_table.md 建议存在（可空）
"""
import asyncio
import argparse
import yaml
from pathlib import Path

from metagpt.environment import Environment
from metagpt.roles import TeamLeader
from metagpt.team import Team
from metagpt.schema import Message

from backend.roles.section_writer import SectionWriter
from metagpt.utils.project_repo import ProjectRepo
from backend.actions.architect_content_action import DesignReportStructureOnly as ArchitectAction


class ProjectConfigLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path
        with open(config_path, 'r', encoding='utf-8') as f:
            self.project_config = yaml.safe_load(f)

    def get_workspace_config(self):
        return self.project_config.get('workspace', {})

    def get_user_message(self):
        return (
            self.project_config.get('user_message_section_writer')
            or self.project_config.get('user_messages', {}).get('section_writer')
            or self.project_config.get('user_message', '')
        )

    def setup_workspace(self) -> str:
        ws = self.get_workspace_config()
        project_id = ws.get('project_id', 'project01')
        base_path = ws.get('base_path', f'workspace/{project_id}')
        Path(base_path).mkdir(parents=True, exist_ok=True)
        (Path(base_path) / 'uploads').mkdir(exist_ok=True)
        return project_id


async def main():
    parser = argparse.ArgumentParser(description='AutoWriter SectionWriter Only - 仅进行章节写作')
    parser.add_argument('-y', '--yaml', required=True, help='项目配置文件路径')
    args = parser.parse_args()

    loader = ProjectConfigLoader(args.yaml)
    project_id = loader.setup_workspace()

    # 建立项目仓库
    ws = loader.get_workspace_config()
    workspace_path = Path(ws.get('base_path', f"workspace/{project_id}"))
    project_repo = ProjectRepo(workspace_path).with_src_path(workspace_path)

    # 仅运行 SectionWriter（含 TeamLeader）
    team = Team(investment=5.0)
    tl = TeamLeader()
    writer = SectionWriter()

    # 注入 ProjectRepo
    writer._project_repo = project_repo

    team.hire([tl, writer])

    # 检查 report_structure.json 是否存在
    rs_path = project_repo.docs.workdir / "report_structure.json"
    if not rs_path.exists():
        print(f"未找到报告结构文件: {rs_path}")
        print("请先运行 app_agent_architectcontent.py 生成章节结构")
        return

    # 发布用户需求消息，触发 SectionWriter 开始写作
    user_message = loader.get_user_message() or "请基于已生成的报告结构，撰写各章节内容并聚合为最终报告。"
    team.env.publish_message(Message(content=user_message, cause_by=ArchitectAction))

    await team.run(n_round=4)

    print("章节写作完成（若Writer已输出）。请在 docs/ 下查看 final_report_*.md。")


if __name__ == "__main__":
    asyncio.run(main())


