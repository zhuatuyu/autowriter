#!/usr/bin/env python
"""
app_sop3.py - 启动SOP3：仅运行 ProductManager（可维护研究简报）

用法：python app_sop3.py -y config/project01.yaml
"""
import asyncio
import argparse
import yaml
from pathlib import Path

from metagpt.logs import logger

from backend.roles.product_manager import ProductManager
from metagpt.team import Team
from metagpt.utils.project_repo import ProjectRepo
from metagpt.roles import TeamLeader
from metagpt.actions import UserRequirement
from metagpt.schema import Message


class ProjectConfigLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path
        with open(config_path, 'r', encoding='utf-8') as f:
            self.project_config = yaml.safe_load(f)

    def get_workspace_config(self):
        return self.project_config.get('workspace', {})

    def get_user_message(self):
        return (
            self.project_config.get('user_message_sop3')
            or self.project_config.get('user_messages', {}).get('sop3')
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
    parser = argparse.ArgumentParser(description='AutoWriter SOP3 - ProductManager Only')
    parser.add_argument('-y', '--yaml', required=True, help='项目配置文件路径')
    args = parser.parse_args()

    loader = ProjectConfigLoader(args.yaml)
    project_id = loader.setup_workspace()

    user_message = loader.get_user_message()
    # 组建团队（使用 MGXEnv，包含 TeamLeader + ProductManager）
    team = Team(investment=5.0)
    product_manager = ProductManager()

    # 注入 repo
    ws = loader.get_workspace_config()
    workspace_path = Path(ws.get('base_path', f"workspace/{project_id}"))
    project_repo = ProjectRepo(workspace_path).with_src_path(workspace_path)
    product_manager._project_repo = project_repo

    team.hire([TeamLeader(), product_manager])

    # 发布用户需求消息（带 Action 标记，触发 ProductManager）
    team.env.publish_message(Message(content=user_message, cause_by=UserRequirement))
    # 运行
    await team.run(n_round=4)

    print("SOP3完成：已更新可维护研究简报 research_brief.md")


if __name__ == "__main__":
    asyncio.run(main())


