#!/usr/bin/env python
"""
产品经理角色 - 需求分析和研究
"""
from backend.actions.research_action import ConductComprehensiveResearch, ResearchData, PrepareDocuments, Documents
from metagpt.actions import UserRequirement
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger
from metagpt.config2 import config
from metagpt.tools.search_engine import SearchEngine
from metagpt.tools import SearchEngineType
from pathlib import Path


class ProductManager(Role):
    """
    产品经理 - 需求分析和研究专家 (SOP第一阶段)
    """
    name: str = "产品经理"
    profile: str = "Product Manager"
    goal: str = "分析用户需求，进行市场和案例研究，输出研究简报"
    constraints: str = "必须进行充分的研究，确保简报内容详实、准确"
    project_repo: object = None

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

        # 创建带有搜索引擎的ConductComprehensiveResearch实例
        research_action = ConductComprehensiveResearch(search_engine=self.search_engine)
        prepare_docs_action = PrepareDocuments()
        
        # 设置要执行的Action
        self.set_actions([prepare_docs_action, research_action])
        
        # 监听用户需求和PrepareDocuments - 这是SOP的起点
        self._watch([UserRequirement, PrepareDocuments])

    async def _act(self) -> Message:
        """
        执行ProductManager的核心逻辑 - SOP第一阶段
        """
        todo = self.rc.todo
        
        # 从记忆中获取用户需求
        user_msgs = self.rc.memory.get_by_action(UserRequirement)
        
        if not user_msgs:
            logger.error("未找到用户需求消息")
            return Message(content="未找到用户需求", role=self.profile)
        
        # 获取最新的用户需求
        latest_user_msg = user_msgs[-1]
        user_requirement = latest_user_msg.content
        logger.info(f"ProductManager开始处理需求: {user_requirement}")
        
        # 检查是否有上传的文档
        local_docs = None
        if hasattr(latest_user_msg, 'instruct_content') and latest_user_msg.instruct_content:
            # 正确解析instruct_content
            try:
                if hasattr(latest_user_msg.instruct_content, 'get'):
                    # 如果是字典形式的instruct_content
                    instruct_data = latest_user_msg.instruct_content
                    if 'docs' in instruct_data:
                        docs_data = instruct_data['docs']
                        docs = [Document(**doc_data) for doc_data in docs_data]
                        local_docs = Documents(docs=docs)
                elif isinstance(latest_user_msg.instruct_content, Documents):
                    local_docs = latest_user_msg.instruct_content
                
                if local_docs:
                    logger.info(f"发现上传的文档: {len(local_docs.docs)} 个")
            except Exception as e:
                logger.error(f"解析上传文档失败: {e}")
        
        if isinstance(todo, ConductComprehensiveResearch):
            # 执行综合研究，包含本地文档
            research_data = await todo.run(
                topic=user_requirement,
                project_repo=self.project_repo,
                local_docs=local_docs  # 传递本地文档
            )
            
            # 创建包含ResearchData的消息，供下游Architect使用
            msg = Message(
                content=f"研究完成: {research_data.brief[:200]}...",
                role=self.profile,
                cause_by=type(todo),
                instruct_content=Message.create_instruct_value(research_data)
            )
            
            logger.info(f"ProductManager完成研究，向量索引路径: {research_data.vector_store_path}")
            return msg
        
        elif isinstance(todo, PrepareDocuments):
            # 如果是PrepareDocuments任务，处理上传的文档
            if self.project_repo:
                uploads_path = Path(self.project_repo.workdir) / "uploads"
                documents = await todo.run(uploads_path)
                
                msg = Message(
                    content=f"文档准备完成，共处理 {len(documents.docs)} 个文档",
                    role=self.profile,
                    cause_by=type(todo),
                    instruct_content=Message.create_instruct_value(documents)
                )
                
                logger.info(f"PrepareDocuments完成，处理了 {len(documents.docs)} 个文档")
                return msg
        
        return Message(content="ProductManager: 无待办任务", role=self.profile)