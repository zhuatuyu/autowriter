#!/usr/bin/env python
"""
app_sop4.py - 启动SOP4：仅运行 SectionWriter 进行章节写作（已具备 report_structure.md 与 research_brief.md）

用法：python app_sop4.py -y config/project01.yaml
前置：
- workspace/<project>/docs/report_structure.md 已生成
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
from backend.actions.project_manager_action import CreateTaskPlan, TaskPlan, Task
import re


class ProjectConfigLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path
        with open(config_path, 'r', encoding='utf-8') as f:
            self.project_config = yaml.safe_load(f)

    def get_workspace_config(self):
        return self.project_config.get('workspace', {})

    def setup_workspace(self) -> str:
        ws = self.get_workspace_config()
        project_id = ws.get('project_id', 'project01')
        base_path = ws.get('base_path', f'workspace/{project_id}')
        Path(base_path).mkdir(parents=True, exist_ok=True)
        (Path(base_path) / 'uploads').mkdir(exist_ok=True)
        return project_id


async def main():
    parser = argparse.ArgumentParser(description='AutoWriter SOP4 - SectionWriter Only')
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

    # 基于磁盘的 report_structure.md 解析生成 TaskPlan，并注入两条消息
    rs_path = project_repo.docs.workdir / "report_structure.md"
    if not rs_path.exists():
        print(f"未找到报告结构文件: {rs_path}")
        return

    sections = []
    text = rs_path.read_text(encoding="utf-8")
    # 粗略解析：以 "### " 开头的标题作为章节，后续非标题段落并入 instruction
    lines = text.splitlines()
    current_title = None
    current_instr = []
    def flush():
        nonlocal sections, current_title, current_instr
        if current_title:
            instruction = "\n".join(current_instr).strip()
            sections.append({"section_title": current_title, "instruction": instruction or "根据结构与简报撰写"})
        current_title = None
        current_instr = []

    for line in lines:
        if line.startswith("### "):
            flush()
            ttl = re.sub(r"^###\s+", "", line).strip()
            current_title = ttl
        else:
            if current_title is not None:
                current_instr.append(line)
    flush()

    tasks = [Task(task_id=i, section_title=s["section_title"], instruction=s["instruction"]) for i, s in enumerate(sections)]
    task_plan = TaskPlan(tasks=tasks)

    # 注入 ArchitectAction（占位满足 SectionWriter 的 _watch），不带 instruct_content 以规避序列化问题
    team.env.publish_message(Message(content="报告结构已存在（SOP4注入）", cause_by=ArchitectAction))
    # 注入 CreateTaskPlan（提供实际任务），直接传递 Pydantic BaseModel 实例以满足序列化
    team.env.publish_message(Message(content="任务计划已注入（SOP4）", cause_by=CreateTaskPlan, instruct_content=task_plan))

    await team.run(n_round=4)

    print("SOP4完成：章节写作流程已运行。请在 docs/ 下查看 final_report_*.md（若有生成）。")


if __name__ == "__main__":
    asyncio.run(main())


