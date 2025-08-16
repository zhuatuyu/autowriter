#!/usr/bin/env python3
"""
知识图谱客户端
复用现有的知识图谱服务
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from backend.services.knowledge_graph import performance_kg
    KG_SERVICES_AVAILABLE = True
except ImportError:
    KG_SERVICES_AVAILABLE = False
    print("⚠️ 知识图谱服务不可用")


class KnowledgeGraphClient:
    """知识图谱客户端"""
    
    def __init__(self, project_config: Dict[str, Any]):
        self.project_config = project_config
        self.project_vector_storage = project_config.get('project_vector_storage', '')
        
        if not KG_SERVICES_AVAILABLE:
            print("⚠️ 知识图谱服务不可用，将使用模拟推理")
    
    async def query_knowledge_graph(self, query: str, mode: str = "keyword", max_results: int = 3) -> str:
        """查询知识图谱"""
        if not KG_SERVICES_AVAILABLE:
            return self._get_mock_kg_result(query)
        
        try:
            # 使用现有的performance_kg服务
            result = await performance_kg.query_knowledge_graph(
                query=query,
                mode=mode,
                max_knowledge_sequence=max_results
            )
            
            print(f"🧠 知识图谱查询完成")
            return result
            
        except Exception as e:
            print(f"⚠️ 知识图谱查询失败: {e}")
            return self._get_mock_kg_result(query)
    
    def _get_mock_kg_result(self, query: str) -> str:
        """获取模拟的知识图谱结果"""
        return f"""
        ### 🧠 知识图谱推理结果（模拟）
        
        基于查询"{query}"，知识图谱发现以下关系：
        
        ### 🕸️ 发现的实体关系
        - **项目类型**: 基础设施建设项目
        - **评价维度**: 质量、进度、成本、效益
        - **关键指标**: 质量控制、进度管理、成本控制
        
        ### 💡 绩效分析洞察
        - 项目应建立完整的评价指标体系
        - 重点关注质量控制和进度管理
        - 建议采用标准化评价方法
        """
