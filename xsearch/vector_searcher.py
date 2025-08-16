#!/usr/bin/env python3
"""
向量搜索客户端
复用现有的向量搜索服务
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from .local_vector_service import LocalVectorService
    from .global_knowledge_service import GlobalKnowledgeService
    VECTOR_SERVICES_AVAILABLE = True
except ImportError:
    VECTOR_SERVICES_AVAILABLE = False
    print("⚠️ 向量搜索服务不可用")

# 导入配置常量
from .config_constants import VECTOR_SEARCH_CONFIG


class VectorSearcher:
    """向量搜索客户端"""
    
    def __init__(self, project_config: Dict[str, Any]):
        self.project_config = project_config
        self.project_vector_storage = project_config.get('project_vector_storage', '')
        self.global_vector_storage = project_config.get('global_vector_storage', '')
        
        # 创建本地向量化服务
        self.local_vector_service = LocalVectorService(project_config)
        
        # 创建全局知识库服务
        self.global_knowledge_service = GlobalKnowledgeService(project_config)
        
        if not VECTOR_SERVICES_AVAILABLE:
            print("⚠️ 向量搜索服务不可用，将使用模拟搜索")
    
    async def search_project(self, query: str, top_k: int = None) -> List[str]:
        """搜索项目知识库"""
        # 使用配置常量作为默认值
        if top_k is None:
            top_k = VECTOR_SEARCH_CONFIG["PROJECT_TOP_K"]
        """搜索项目知识库"""
        if not VECTOR_SERVICES_AVAILABLE:
            print("⚠️ 向量搜索服务不可用")
            return []
        
        try:
            # 优先使用本地向量化服务
            print("🔍 使用本地向量化服务搜索项目文档...")
            local_results = await self.local_vector_service.search_local_documents(query, top_k)
            
            if local_results:
                print(f"📁 本地文档搜索完成，找到 {len(local_results)} 条结果")
                return local_results
            
            # 如果本地没有结果，尝试使用原有的hybrid_search服务
            print("🔍 本地文档无结果，尝试使用原有项目知识库...")
            results = await hybrid_search.hybrid_search(
                query=query,
                project_vector_storage_path=self.project_vector_storage,
                enable_global=False,  # 只要项目数据
                project_top_k=top_k
            )
            
            print(f"📁 项目知识库检索完成，找到 {len(results)} 条结果")
            return results if results else []
            
        except Exception as e:
            print(f"⚠️ 项目知识库搜索失败: {e}")
            print("⚠️ 项目知识库搜索失败，返回空结果")
            return []
    
    async def search_global(self, query: str, top_k: int = None) -> List[str]:
        """搜索全局知识库（直接使用已构建的索引）"""
        # 使用配置常量作为默认值
        if top_k is None:
            top_k = VECTOR_SEARCH_CONFIG["GLOBAL_TOP_K"]
        """搜索全局知识库（直接使用已构建的索引）"""
        if not VECTOR_SERVICES_AVAILABLE:
            print("⚠️ 向量搜索服务不可用")
            return []
        
        try:
            # 直接使用已构建的全局知识库索引
            results = await self.global_knowledge_service.search_global(query, top_k)
            
            print(f"🌍 全局知识库检索完成，找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            print(f"⚠️ 全局知识库搜索失败: {e}")
            print("⚠️ 全局知识库搜索失败，返回空结果")
            return []
    

