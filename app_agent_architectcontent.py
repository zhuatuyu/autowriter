#!/usr/bin/env python
"""
独立入口：章节架构师（ArchitectContent）
独立运行产出 report_structure.json

使用方法：
python app_agent_architectcontent.py -y config/project01.yaml

功能：
- 基于研究简报设计章节结构
- 生成 JSON 格式的 report_structure.json
- 包含完整的章节配置、写作指导、事实引用要求等
- 跳过指标表生成（由 SOP1 负责）

输出文件：
- workspace/project01/docs/report_structure.json
"""
import asyncio
import argparse
import yaml
from pathlib import Path

from metagpt.team import Team
from metagpt.roles import TeamLeader
from metagpt.actions import UserRequirement
from metagpt.schema import Message
from metagpt.utils.project_repo import ProjectRepo

from backend.roles.architect_content import ArchitectContent


class ProjectConfigLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path
        with open(config_path, 'r', encoding='utf-8') as f:
            self.project_config = yaml.safe_load(f)

    def get_workspace_config(self):
        return self.project_config.get('workspace', {})

    def get_user_message(self):
        return (
            self.project_config.get('user_message_architect_content')
            or self.project_config.get('user_messages', {}).get('architect_content')
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
    parser = argparse.ArgumentParser(description='ArchitectContent Only - 仅生成章节结构')
    parser.add_argument('-y', '--yaml', required=True, help='项目配置文件路径')
    args = parser.parse_args()

    loader = ProjectConfigLoader(args.yaml)
    project_id = loader.setup_workspace()

    ws = loader.get_workspace_config()
    workspace_path = Path(ws.get('base_path', f"workspace/{project_id}"))
    project_repo = ProjectRepo(workspace_path).with_src_path(workspace_path)

    team = Team(investment=5.0)
    tl = TeamLeader()
    ac = ArchitectContent()
    ac._project_repo = project_repo
    team.hire([tl, ac])

    user_message = loader.get_user_message() or "请设计报告章节结构"
    team.env.publish_message(Message(content=user_message, cause_by=UserRequirement))

    # 2轮足够：1) 读取简报并生成结构 2) 写盘并结束
    await team.run(n_round=2)
    print("已生成章节结构: ", project_repo.docs.workdir / "report_structure.json")


if __name__ == "__main__":
    asyncio.run(main())


