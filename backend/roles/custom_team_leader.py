#!/usr/bin/env python
"""
自定义团队领导者 - 配置了正确的搜索引擎
"""
from metagpt.roles.di.team_leader import TeamLeader
from metagpt.actions.search_enhanced_qa import SearchEnhancedQA
from metagpt.actions.research import CollectLinks
from metagpt.config2 import config
from metagpt.tools.search_engine import SearchEngine
from metagpt.tools import SearchEngineType
from metagpt.schema import Message, AIMessage
from metagpt.logs import logger
from typing import Tuple


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

        # 创建 SearchEnhancedQA 并注入配置好的 CollectLinks
        self.search_enhanced_qa_action = SearchEnhancedQA(collect_links_action=self.collect_links_action)
        
        # 调用更新工具执行映射
        self._update_tool_execution()

    def _update_tool_execution(self):
        """重写父类方法，使用我们配置好的SearchEnhancedQA实例"""
        # 调用父类方法
        super()._update_tool_execution()
        
        # 使用我们配置好的实例替换默认的SearchEnhancedQA
        if self.config.enable_search:
            self.tool_execution_map["SearchEnhancedQA.run"] = self.search_enhanced_qa_action.run

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