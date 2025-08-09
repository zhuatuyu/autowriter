#!/usr/bin/env python
"""
app2.py - 命令行启动版本的AutoWriter
替代chainlit启动方式，便于测试和调试

使用方式：
python app2.py -y config/project01.yaml
"""

import asyncio
import argparse
import yaml
import shutil
import sys
from pathlib import Path
from typing import Dict, List
import uuid

# 优先将本仓库自带的MetaGPT备份路径加入sys.path，避免环境未安装导致的导入失败
_ROOT = Path(__file__).resolve().parent
_VENDORED = _ROOT / "example" / "MetaGPT_bak"
if (_VENDORED / "metagpt").exists():
    sys.path.insert(0, str(_VENDORED))

# 导入真正的后端服务
from backend.services.company import Company
from metagpt.environment import Environment
from metagpt.logs import logger
from metagpt.config2 import config

class ProjectConfigLoader:
    """项目配置加载器"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.project_config = self._load_project_config()
    
    def _load_project_config(self) -> Dict:
        """加载项目配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                project_config = yaml.safe_load(f)
            logger.info(f"✅ 项目配置加载成功: {self.config_path}")
            return project_config
        except Exception as e:
            logger.error(f"❌ 项目配置加载失败: {e}")
            raise
    
    def get_project_info(self) -> Dict:
        """获取项目信息"""
        return self.project_config.get('project_info', {})
    
    def get_workspace_config(self) -> Dict:
        """获取工作区配置"""
        return self.project_config.get('workspace', {})
    
    def get_file_paths(self) -> Dict:
        """获取文件路径配置"""
        return self.project_config.get('file_paths', {})
    
    def get_user_message(self) -> str:
        """获取用户消息"""
        return self.project_config.get('user_message', '')
    
    def setup_workspace(self) -> str:
        """设置工作区环境"""
        workspace_config = self.get_workspace_config()
        project_id = workspace_config.get('project_id', 'project01')
        base_path = workspace_config.get('base_path', f'workspace/{project_id}')
        
        # 创建工作区目录
        workspace_path = Path(base_path)
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 创建上传目录
        uploads_path = workspace_path / "uploads"
        uploads_path.mkdir(exist_ok=True)
        
        logger.info(f"✅ 工作区已设置: {workspace_path}")
        logger.info(f"✅ 上传目录已设置: {uploads_path}")
        
        return project_id
    
    def prepare_documents(self) -> List[str]:
        """准备文档文件"""
        file_paths = self.get_file_paths()
        documents = file_paths.get('documents', [])
        
        prepared_files = []
        for doc_path in documents:
            doc_file = Path(doc_path)
            if doc_file.exists():
                prepared_files.append(str(doc_file))
                logger.info(f"✅ 文档已就绪: {doc_file}")
            else:
                logger.warning(f"⚠️ 文档不存在: {doc_file}")
        
        return prepared_files

class App2Runner:
    """App2运行器"""
    
    def __init__(self, config_loader: ProjectConfigLoader):
        self.config_loader = config_loader
        self.company = Company()
        self.environment = Environment()
    
    async def run(self):
        """运行主流程"""
        try:
            logger.info("🚀 App2启动中...")
            
            # 1. 设置工作区
            project_id = self.config_loader.setup_workspace()
            
            # 2. 准备文档
            file_paths = self.config_loader.prepare_documents()
            
            # 3. 获取用户消息
            user_message = self.config_loader.get_user_message()
            
            # 4. 显示项目信息
            self._display_project_info()
            
            # 5. 处理消息
            logger.info("📤 开始处理用户消息...")
            
            # 🎯 构建项目配置对象传递给company
            project_config = {
                'project_id': project_id,
                'workspace': self.config_loader.get_workspace_config(),
                'project_info': self.config_loader.get_project_info(),
                'file_paths': self.config_loader.get_file_paths()
            }
            
            response = await self.company.process_message(
                project_config=project_config,
                message=user_message,
                environment=self.environment,
                file_paths=file_paths
            )
            
            # 6. 显示结果
            logger.info("✅ 处理完成！")
            print("\n" + "="*80)
            print("📋 处理结果:")
            print("="*80)
            print(response)
            print("="*80)
            
        except Exception as e:
            logger.error(f"❌ App2运行失败: {e}")
            raise
    
    def _display_project_info(self):
        """显示项目信息"""
        project_info = self.config_loader.get_project_info()
        
        print("\n" + "="*80)
        print("📋 项目配置信息:")
        print("="*80)
        print(f"项目名称: {project_info['project_name']}")
        print(f"项目类型: {project_info['project_type']}")
        print(f"预算金额: {project_info['budget_amount']}")
        print(f"实施周期: {project_info['implementation_period']}")
        print(f"受益对象: {project_info['target_beneficiaries']}")
        print(f"主要目标: {', '.join(project_info['main_objectives'])}")
        print("="*80)

async def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='AutoWriter - 命令行版本')
    parser.add_argument('-y', '--yaml', required=True, 
                       help='项目配置文件路径 (例如: config/project01.yaml)')
    args = parser.parse_args()
    
    try:
        # 加载项目配置
        config_loader = ProjectConfigLoader(args.yaml)
        
        # 创建运行器
        runner = App2Runner(config_loader)
        
        # 运行主流程
        await runner.run()
        
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))