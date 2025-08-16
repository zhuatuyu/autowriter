#!/usr/bin/env python3
"""
配置加载器
加载项目配置和系统配置
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.project_root = config_path.parent.parent
        
    def load_project_config(self) -> Dict[str, Any]:
        """加载项目配置"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 提取项目信息
        project_info = config.get('project_info', {})
        workspace = config.get('workspace', {})
        
        # 获取项目ID
        project_id = workspace.get('project_id', 'project01')
        
        # 构建配置字典
        project_config = {
            'project_name': project_info.get('project_name', f'项目{project_id}'),
            'project_type': project_info.get('project_type', '未知类型'),
            'province': project_info.get('province', ''),
            'city': project_info.get('city', ''),
            'county': project_info.get('county', ''),
            'project_description': project_info.get('project_description', ''),
            'project_id': project_id,
            'project_root': str(self.project_root),
            'workspace_root': str(self.project_root / 'workspace'),
            'global_vector_storage': str(self.project_root / 'workspace' / 'vector_storage' / 'global_index'),
            'project_vector_storage': str(self.project_root / 'workspace' / project_id / 'vector_storage'),
            'output_dir': str(self.project_root / 'xsearch' / 'output'),
            'file_paths': config.get('file_paths', {}),
            'workspace': workspace
        }
        
        return project_config
    
    def load_system_config(self) -> Dict[str, Any]:
        """加载系统配置"""
        system_config_path = self.project_root / 'config' / 'config2.yaml'
        
        if system_config_path.exists():
            with open(system_config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            # 返回默认配置
            return {
                'llm': {
                    'api_key': os.getenv('GOOGLE_API_KEY', ''),
                    'base_url': 'https://generativelanguage.googleapis.com/v1beta/models',
                    'model': 'gemini-1.5-pro'
                },
                'embedding': {
                    'api_key': os.getenv('GOOGLE_API_KEY', ''),
                    'model': 'text-embedding-v3'
                }
            }
