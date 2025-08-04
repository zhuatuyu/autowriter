#!/usr/bin/env python
"""
架构师角色 - 报告结构设计和指标分析
"""
from metagpt.actions.design_api import WriteDesign
from metagpt.actions.design_api_review import DesignReview
from metagpt.roles.di.role_zero import RoleZero
from metagpt.schema import Message, AIMessage, UserMessage
from metagpt.actions.di.run_command import RunCommand
from metagpt.actions.search_enhanced_qa import SearchEnhancedQA
from metagpt.tools.search_engine import SearchEngine
from metagpt.config2 import config  # 使用已实例化的config对象，而不是Config类
from metagpt.logs import logger
from metagpt.actions import UserRequirement
from metagpt.utils.common import any_to_str
from metagpt.prompts.di.role_zero import QUICK_THINK_PROMPT, QUICK_THINK_TAG
from metagpt.utils.report import ThoughtReporter

from backend.actions.research_action import ConductComprehensiveResearch

# 自定义Action
class DesignReportStructure(WriteDesign):
    """设计报告结构的Action"""
    
    async def run(self, research_data: str) -> str:
        # 基于研究数据设计报告结构
        prompt = f"""
        基于以下研究数据，设计一个完整的绩效分析报告结构：
        
        研究数据：
        {research_data}
        
        请设计包含以下部分的报告结构：
        1. 执行摘要
        2. 关键指标分析
        3. 趋势分析
        4. 问题识别
        5. 改进建议
        6. 结论
        
        输出格式为详细的报告大纲和每个部分的具体要求。
        """
        
        result = await self._aask(prompt)
        return result

class Architect(RoleZero):
    """
    Represents an Architect role in a software development process.
    """

    name: str = "Bob"
    profile: str = "Architect"
    goal: str = "Design a concise, usable, complete software system"
    constraints: str = "Try to specify good open source tools as much as possible"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 使用已实例化的config对象，而不是Config()类
        if hasattr(config, 'search') and config.search.api_type == "alibaba":
            search_engine = SearchEngine(
                engine=config.search.api_type,
                api_key=config.search.api_key,
                endpoint=config.search.endpoint,
                workspace=config.search.workspace,
                service_id=config.search.service_id
            )
            self.search_enhanced_qa = SearchEnhancedQA(search_engine=search_engine)
        else:
            self.search_enhanced_qa = SearchEnhancedQA()
        
        # 设置Action和监听
        self.set_actions([DesignReportStructure])
        self._watch([ConductComprehensiveResearch])  # 监听ProductManager的输出
        
        # 更新工具执行映射
        self._update_tool_execution()

    def _update_tool_execution(self):
        """更新工具执行映射"""
        super()._update_tool_execution()
        if hasattr(self, 'search_enhanced_qa'):
            self.tool_execution_map["SearchEnhancedQA.run"] = self.search_enhanced_qa.run

    async def _quick_think(self):
        """重写_quick_think方法，使用配置好的搜索引擎"""
        answer = ""
        rsp_msg = None
        
        if self.rc.news[-1].cause_by != any_to_str(UserRequirement):
            return rsp_msg, ""

        memory = self.get_memories(k=self.memory_k)
        context = self.llm.format_msg(memory + [UserMessage(content=QUICK_THINK_PROMPT)])
        
        async with ThoughtReporter() as reporter:
            await reporter.async_report({"type": "classify"})
            intent_result = await self.llm.aask(context, system_msgs=[self.format_quick_system_prompt()])

        if "SEARCH" in intent_result:
            query = "\n".join(str(msg) for msg in memory)
            # 使用配置好的搜索引擎实例
            answer = await self.search_enhanced_qa.run(query)

        if answer:
            self.rc.memory.add(AIMessage(content=answer, cause_by=QUICK_THINK_TAG))
            await self.reply_to_human(content=answer)
            rsp_msg = AIMessage(
                content=answer,
                sent_from=self.name,
                cause_by=QUICK_THINK_TAG,
            )

        return rsp_msg, intent_result

    async def _act(self) -> Message:
        """执行架构设计任务"""
        logger.info(f"{self.name} is designing report structure...")
        
        # 获取ProductManager的研究数据
        research_data = ""
        for msg in self.get_memories():
            if msg.cause_by == "ConductComprehensiveResearch":
                research_data = msg.content
                break
        
        if not research_data:
            research_data = "No research data available"
        
        # 执行报告结构设计
        todo = self.rc.todo
        result = await todo.run(research_data)
        
        msg = Message(
            content=result,
            role=self.profile,
            cause_by=type(todo),
            sent_from=self,
        )
        
        self.rc.memory.add(msg)
        return msg