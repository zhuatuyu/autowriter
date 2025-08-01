import json
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# from backend.models.project import Project


class ProjectService:
    """项目管理服务"""
    
    def __init__(self):
        self.projects_dir = Path("workspaces/projects")
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.projects_file = self.projects_dir / "projects.json"
    
    async def create_project(self, project: Project) -> Project:
        """创建新项目"""
        # 创建项目工作目录 - 使用更友好的命名格式
        timestamp = int(datetime.now().timestamp() * 1000)
        project_dir_name = f"project_{timestamp}"
        project_workspace = self.projects_dir / project_dir_name
        project_workspace.mkdir(exist_ok=True)
        
        # 创建标准的项目目录结构
        (project_workspace / "uploads").mkdir(exist_ok=True)
        (project_workspace / "research").mkdir(exist_ok=True)
        (project_workspace / "research" / "web").mkdir(exist_ok=True)
        (project_workspace / "research" / "cases").mkdir(exist_ok=True)
        (project_workspace / "analysis").mkdir(exist_ok=True)
        (project_workspace / "design").mkdir(exist_ok=True)
        (project_workspace / "drafts").mkdir(exist_ok=True)
        (project_workspace / "reports").mkdir(exist_ok=True)
        (project_workspace / "outputs").mkdir(exist_ok=True)
        
        # 创建项目说明文件
        readme_content = f"""# {project.name}

## 项目描述
{project.description}

## 项目信息
- 项目ID: {project.id}
- 创建时间: {project.created_at}
- 状态: {project.status}

## 目录结构
- uploads/: 上传的文件
- research/: 研究资料
  - web/: 网络搜索结果
  - cases/: 案例研究
- analysis/: 数据分析结果
- design/: 设计文档
- drafts/: 草稿文件
- reports/: 最终报告
- outputs/: 输出文件
"""
        
        with open(project_workspace / "README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        project.workspace_path = str(project_workspace)
        
        # 保存项目信息
        projects = await self._load_projects()
        # 使用model_dump()方法来序列化Pydantic模型
        projects[project.id] = project.model_dump()
        await self._save_projects(projects)
        
        return project
    
    async def get_project(self, project_id: str) -> Optional[Project]:
        """获取项目"""
        projects = await self._load_projects()
        project_data = projects.get(project_id)
        if project_data:
            return Project(**project_data)
        return None
    
    async def get_all_projects(self) -> List[Project]:
        """获取所有项目"""
        projects = await self._load_projects()
        return [Project(**data) for data in projects.values()]
    
    async def update_project(self, project_id: str, updates: dict) -> Optional[Project]:
        """更新项目"""
        projects = await self._load_projects()
        if project_id in projects:
            projects[project_id].update(updates)
            projects[project_id]["updated_at"] = datetime.now().isoformat()
            await self._save_projects(projects)
            return Project(**projects[project_id])
        return None
    
    async def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        projects = await self._load_projects()
        if project_id in projects:
            del projects[project_id]
            await self._save_projects(projects)
            
            # 删除项目工作目录
            project_workspace = self.projects_dir / project_id
            if project_workspace.exists():
                import shutil
                shutil.rmtree(project_workspace)
            
            return True
        return False
    
    async def _load_projects(self) -> dict:
        """加载项目数据"""
        if self.projects_file.exists():
            try:
                with open(self.projects_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {}
    
    async def _save_projects(self, projects: dict):
        """保存项目数据"""
        # 处理datetime序列化
        serializable_projects = {}
        for project_id, project_data in projects.items():
            serializable_data = project_data.copy()
            # 如果是datetime对象，转换为ISO格式字符串
            if isinstance(serializable_data.get('created_at'), datetime):
                serializable_data['created_at'] = serializable_data['created_at'].isoformat()
            if isinstance(serializable_data.get('updated_at'), datetime):
                serializable_data['updated_at'] = serializable_data['updated_at'].isoformat()
            serializable_projects[project_id] = serializable_data
        
        with open(self.projects_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_projects, f, ensure_ascii=False, indent=2)