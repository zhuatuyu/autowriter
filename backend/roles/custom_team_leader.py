#!/usr/bin/env python
"""
自定义团队领导者 - 配置了正确的搜索引擎
"""
from metagpt.roles.di.team_leader import TeamLeader
from backend.actions.robust_search_action import RobustSearchEnhancedQA
from metagpt.actions.research import CollectLinks
from metagpt.config2 import config
from metagpt.tools.search_engine import SearchEngine
from metagpt.tools import SearchEngineType
from metagpt.schema import Message, AIMessage
from metagpt.logs import logger
from typing import Tuple
from pathlib import Path


class CustomTeamLeader(TeamLeader):
    """
    自定义团队领导者 - 使用正确配置的搜索引擎
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 使用 MetaGPT 原生方式创建阿里云搜索引擎
        search_config = config.search
        search_kwargs = search_config.model_dump() if hasattr(search_config, 'model_dump') else {}
        
        # 创建搜索引擎实例
        self.search_engine = SearchEngine(
            engine=SearchEngineType.ALIBABA,
            **search_kwargs
        )

        # 创建正确配置的 CollectLinks
        self.collect_links_action = CollectLinks(search_engine=self.search_engine)

        # 创建健壮的SearchEnhancedQA并注入配置好的CollectLinks
        self.search_enhanced_qa_action = RobustSearchEnhancedQA(collect_links_action=self.collect_links_action)
        
        # 调用更新工具执行映射
        self._update_tool_execution()

    def _update_tool_execution(self):
        """重写父类方法，使用我们配置好的SearchEnhancedQA实例"""
        # 调用父类方法
        super()._update_tool_execution()
        
        # 使用我们配置好的实例替换默认的SearchEnhancedQA
        if self.config.enable_search:
            self.tool_execution_map["SearchEnhancedQA.run"] = self.search_enhanced_qa_action.run

        # 增加一个便捷命令，用于在SOP1阶段提示指标文件已生成，便于调试
        async def _publish_metric_ready_message(path: str | None = None) -> str:
            try:
                base = "workspace/project01"  # 默认项目
                if hasattr(self, "_project_repo") and self._project_repo:
                    base = str(self._project_repo.workdir)
                md = Path(base) / "docs" / "metric_analysis_table.md"
                msg = f"指标结构已生成于 {md}，请指标评价专家进行评价。"
                from metagpt.schema import UserMessage
                await self.rc.env.publish_message(UserMessage(content=msg, sent_from=self.name))
                return msg
            except Exception as e:
                return f"发布提示失败: {e}"

        self.tool_execution_map["TeamLeader.publish_metric_ready"] = _publish_metric_ready_message

    async def _quick_think(self) -> Tuple[Message, str]:
        """重写_quick_think方法，使用我们配置好的SearchEnhancedQA实例"""
        from metagpt.actions import UserRequirement
        from metagpt.utils.common import any_to_str
        
        answer = ""
        rsp_msg = None
        
        if self.rc.news[-1].cause_by != any_to_str(UserRequirement):
            return rsp_msg, ""

        # routing
        memory = self.get_memories(k=self.memory_k)
        
        # 简化的意图分类，直接使用搜索
        intent_result = "SEARCH"
        
        if "SEARCH" in intent_result:
            query = "\n".join(str(msg) for msg in memory)
            try:
                # 使用我们配置好的实例
                answer = await self.search_enhanced_qa_action.run(query)
                logger.info(f"搜索成功，结果长度: {len(answer) if answer else 0}")
            except Exception as e:
                logger.error(f"SearchEnhancedQA failed: {e}")
                answer = "搜索功能暂时不可用，请稍后再试。"

        if answer:
            self.rc.memory.add(AIMessage(content=answer, cause_by="QUICK_THINK_TAG"))
            await self.reply_to_human(content=answer)
            rsp_msg = AIMessage(
                content=answer,
                sent_from=self.name,
                cause_by="QUICK_THINK_TAG",
            )

        return rsp_msg, intent_result