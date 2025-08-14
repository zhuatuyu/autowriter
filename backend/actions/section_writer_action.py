#!/usr/bin/env python
"""
写作专家Action集合 - 内容生成和整合（SOP2 章节写作，禁用RAG；不注入指标）
"""
from pathlib import Path
from metagpt.actions import Action
from metagpt.logs import logger
from backend.config.writer_prompts import (
    WRITER_BASE_SYSTEM,      # 写作专家系统提示（写作目标/质量要求）
    SECTION_WRITING_PROMPT,  # 章节写作提示词模板（标题/指导/事实）
)
from backend.tools.project_info import get_project_info_text
from backend.tools.json_utils import extract_json_from_llm_response
import json
from .project_manager_action import Task
import re


class WriteSection(Action):
    """
    写作章节Action - WriterExpert的核心能力
    仅基于研究简报与网络案例摘录生成章节内容（禁用RAG，不注入指标）。
    """
    
    async def run(
        self,
        task: Task,
    ) -> str:
        """基于任务要求与研究简报/网络案例生成章节内容。"""
        logger.info(f"开始写作章节: {task.section_title}")
        # 1) 读取研究简报与参考网络资料（不做RAG检索）
        factual_basis = await self._assemble_factual_basis(task)
        # 1.1) 读取指标表做轻量统计（不注入到消息，不污染简报）
        metric_summary_text = self._summarize_metrics()
        if metric_summary_text:
            factual_basis += "\n\n## 指标体系要点（来自 metric_analysis_table.md）\n" + metric_summary_text
        # 2) 构建写作prompt
        prompt = self._build_writing_prompt(task, factual_basis)
        # 3) 生成章节内容
        section_content = await self._generate_content(prompt)
        
        logger.info(f"章节写作完成: {task.section_title}")
        return section_content
    
    async def _assemble_factual_basis(self, task: Task) -> str:
        """基于研究简报与网络案例资源文件拼装事实依据（禁用RAG）。"""
        try:
            project_root = self._get_project_root()
            brief_text, brief_dict = self._read_and_format_research_brief(project_root)
            case_snippets = self._collect_case_snippets_by_source(project_root, brief_dict)
            parts = []
            if brief_text:
                parts.append("## 项目研究简报\n" + brief_text)
            if case_snippets:
                parts.append("\n## 参考网络资料\n" + case_snippets)
            return "\n\n".join(parts) if parts else "（暂无研究简报与参考网络资料）"
        except Exception as e:
            logger.error(f"拼装事实依据失败: {e}")
            return f"（拼装事实依据失败: {e}）"

    def _get_project_root(self) -> Path:
        """使用已注入的 ProjectRepo 获取项目根目录（不做回退）。"""
        return Path(self._project_repo.workdir)

    def _read_and_format_research_brief(self, project_root: Path) -> tuple[str, dict]:
        brief_file = project_root / "docs" / "research_brief.md"
        if not brief_file.exists():
            return "", {}
        try:
            raw = brief_file.read_text(encoding="utf-8").strip()
            data = extract_json_from_llm_response(raw)
            brief = data if isinstance(data, dict) else {}
        except Exception:
            brief = {}
        # 将六键拼成可读文本
        order = ["项目情况", "资金情况", "重要事件", "政策引用", "推荐方法", "可借鉴网络案例"]
        lines = []
        for k in order:
            v = brief.get(k)
            if v:
                lines.append(f"### {k}\n{v}")
        return ("\n\n".join(lines), brief)

    def _summarize_metrics(self) -> str:
        """从 metric_analysis_table.md 读取 JSON，做轻量统计摘要。
        - 仅统计：总指标数、按一级维度分布（决策/过程/产出/效益）、已评分/未评分数量、平均分。
        - 返回纯文本，不影响上游消息与简报。
        """
        try:
            project_root = self._get_project_root()
            metric_file = project_root / "docs" / "metric_analysis_table.md"
            if not metric_file.exists():
                return ""
            text = metric_file.read_text(encoding="utf-8")
            import re
            m = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL)
            if not m:
                return ""
            data = json.loads(m.group(1))
            if not isinstance(data, list):
                return ""
            total = len(data)
            by_l1 = {}
            scored = 0
            score_sum = 0.0
            for item in data:
                l1 = item.get("level1_name") or "未分组"
                by_l1[l1] = by_l1.get(l1, 0) + 1
                if isinstance(item.get("score"), (int, float)):
                    scored += 1
                    score_sum += float(item["score"])
            avg = (score_sum / scored) if scored else 0.0
            parts = [f"总指标数: {total}", f"已评分/未评分: {scored}/{total-scored}", f"平均分: {avg:.2f}"]
            parts.append("按一级维度分布:" )
            for k, v in by_l1.items():
                parts.append(f"- {k}: {v}")
            return "\n".join(parts)
        except Exception as e:
            logger.warning(f"读取指标表统计失败: {e}")
            return ""

    def _collect_case_snippets_by_source(self, project_root: Path, brief: dict) -> str:
        """根据简报中的‘来源：...’URL/文件名，在 resources/ 网络案例文件中截取对应片段。"""
        src_field = (brief or {}).get("可借鉴网络案例", "")
        if not isinstance(src_field, str) or not src_field.strip():
            return ""
        # 匹配形如 （来源：...） 的片段，支持多个；同时兼容中文全角分号分隔
        sources = re.findall(r"来源[:：]([^；)]+)", src_field)
        if not sources:
            return ""
        resources_dir = project_root / "resources"
        if not resources_dir.exists():
            return ""
        snippets = []
        # 预编译 来源 标记匹配（支持 '## 来源:' 或 '#### 来源:'）
        def find_segments(text: str, needle: str) -> list[str]:
            lines = text.splitlines()
            segments = []
            start_idx = None
            header_pattern = re.compile(r"^#{2,4}\\s*来源[:：]")
            for i, line in enumerate(lines):
                if start_idx is None and needle in line:
                    start_idx = i
                    continue
                if start_idx is not None and header_pattern.match(line):
                    # 到达下一个来源段，切片
                    seg = "\n".join(lines[start_idx:i]).strip()
                    if seg:
                        segments.append(seg)
                    start_idx = i if needle in line else None
            if start_idx is not None:
                seg = "\n".join(lines[start_idx:]).strip()
                if seg:
                    segments.append(seg)
            return segments
        # 遍历 resources 下的 Markdown 文件，寻找匹配片段
        for fp in sorted(resources_dir.glob("*.md")):
            try:
                content = fp.read_text(encoding="utf-8")
            except Exception:
                continue
            for needle in sources:
                segs = find_segments(content, needle.strip())
                for seg in segs:
                    snippets.append(f"【参考来源】{needle}\n文件: {fp.name}\n\n{seg}")
        return "\n\n---\n\n".join(snippets[:5])  # 截取最多5段，避免上下文过长
    
    def _build_writing_prompt(self, task: Task, factual_basis: str) -> str:
        """构建写作prompt（不包含指标引用）"""
        prompt = SECTION_WRITING_PROMPT.format(
            section_title=task.section_title,
            instruction=task.instruction,
            factual_basis=factual_basis,
            word_limit="2000"
        )
        return prompt
    
    async def _generate_content(self, prompt: str) -> str:
        """生成章节内容"""
        # 使用LLM生成内容
        # 注入项目配置信息作为系统级提示
        project_info_text = get_project_info_text()
        section_content = await self._aask(prompt, [WRITER_BASE_SYSTEM, project_info_text])
        return section_content


