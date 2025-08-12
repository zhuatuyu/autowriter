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
    _project_repo: object = None  # 使用私有属性避免序列化问题

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
        
        # 设置要执行的Action - 使用实例而不是类
        self.set_actions([prepare_docs_action, research_action])
        
        # 只监听UserRequirement，这是SOP的唯一起点
        self._watch([UserRequirement])
        
        # 注意：现在在单次_act调用中完成两个阶段

    async def _act(self) -> Message:
        """
        执行ProductManager的核心逻辑 - SOP第一阶段
        在一次调用中完成两个阶段：文档准备 + 综合研究
        """
        
        # 阶段1: 准备文档
        logger.info("SOP 1.1: 开始准备和向量化文档...")
        prepare_action = self.actions[0]  # PrepareDocuments实例
        
        uploads_path = Path(self._project_repo.workdir) / "uploads"
        if not uploads_path.exists():
            logger.error(f"❌ 上传目录不存在: {uploads_path}")
            raise FileNotFoundError(f"项目上传目录不存在: {uploads_path}。请确保项目结构正确")
        else:
            documents = await prepare_action.run(uploads_path)

        logger.info(f"✅ 文档准备完成，处理了 {len(documents.docs)} 个文档。")
        
        # 阶段2: 立即进行综合研究
        logger.info("SOP 1.2: 开始进行综合研究...")
        research_action = self.actions[1]  # ConductComprehensiveResearch实例

        # 获取用户最初的需求作为研究主题
        user_req_msgs = self.rc.memory.get_by_action(UserRequirement)
        if user_req_msgs:
            latest_msg = user_req_msgs[-1]
            # 正确解析Message内容并清洗MetaGPT前缀
            raw = latest_msg.content if isinstance(latest_msg.content, str) else str(latest_msg.content)
            try:
                import re as _re
                topic = _re.sub(r"^\[Message\].*?:\s*", "", raw).strip()
            except Exception:
                topic = raw
        else:
            topic = "未定义的研究主题"
        
        logger.info(f"研究主题: {topic}")
        if documents and documents.docs:
            logger.info(f"将使用 {len(documents.docs)} 个本地文档进行RAG增强研究。")

        # 执行研究，现在local_docs是正确传递的
        research_data = await research_action.run(
            topic=topic,
            project_repo=self._project_repo,
            local_docs=documents
        )
        
        # 创建最终的研究简报消息
        msg = Message(
            content=f"研究完成: {research_data.brief[:200]}...",
            role=self.profile,
            cause_by=type(research_action),
            instruct_content=research_data
        )
        
        logger.info(f"✅ ProductManager完成所有研究工作。")
        logger.info(f"📄 研究简报长度: {len(research_data.brief)} 字符")
        logger.info(f"📁 向量存储路径: {research_data.vector_store_path}")
        return msg