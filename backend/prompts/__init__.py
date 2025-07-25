"""
LLM Prompts Module
存放所有智能体的提示词模板，提供统一的提示词管理。
"""

from . import director_prompts
from . import core_manager_prompts
from . import data_analyst_prompts
from . import document_expert_prompts
from . import writer_expert_prompts

__all__ = [
    'director_prompts',
    'core_manager_prompts', 
    'data_analyst_prompts',
    'document_expert_prompts',
    'writer_expert_prompts'
] 