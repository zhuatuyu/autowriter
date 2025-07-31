"""
使用MetaGPT原生Environment类，确保智能体状态管理和消息路由正常工作
"""
from metagpt.environment import Environment as MetaGPTEnvironment
from metagpt.context import Context

class Environment(MetaGPTEnvironment):
    """继承MetaGPT原生Environment，确保完整的智能体协作功能"""
    
    def __init__(self, context: Context = None):
        """初始化Environment，使用MetaGPT标准实现"""
        super().__init__(context=context or Context())