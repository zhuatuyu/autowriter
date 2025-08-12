#!/usr/bin/env python
"""
app_sop2.py - 启动SOP2：章节写作（依赖SOP1结果）

用法：python app_sop2.py -y config/project01.yaml
"""
import asyncio
import argparse
import yaml
from pathlib import Path

from metagpt.environment import Environment
from metagpt.logs import logger

from backend.services.company_sop2 import CompanySOP2


class ProjectConfigLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path
        with open(config_path, 'r', encoding='utf-8') as f:
            self.project_config = yaml.safe_load(f)

    def get_workspace_config(self):
        return self.project_config.get('workspace', {})

    def get_user_message(self):
        # 兼容：优先读取 SOP2 专用消息；无则回退通用 user_message
        return (
            self.project_config.get('user_message_sop2')
            or self.project_config.get('user_messages', {}).get('sop2')
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
    parser = argparse.ArgumentParser(description='AutoWriter SOP2')
    parser.add_argument('-y', '--yaml', required=True, help='项目配置文件路径')
    args = parser.parse_args()

    loader = ProjectConfigLoader(args.yaml)
    project_id = loader.setup_workspace()

    user_message = loader.get_user_message()
    environment = Environment()
    company = CompanySOP2()

    project_config = {
        'project_id': project_id,
        'workspace': loader.get_workspace_config(),
        'project_info': self_safe(loader.project_config.get('project_info', {})),
        'file_paths': loader.project_config.get('file_paths', {}),
    }
    result = await company.process_message(project_config, user_message, environment, None)
    print(result)


def self_safe(x):
    return x


if __name__ == "__main__":
    asyncio.run(main())

