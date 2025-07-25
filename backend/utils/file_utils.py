import os
import json
from pathlib import Path
from typing import List, Dict, Optional
import markdown
from datetime import datetime

class WorkspaceFileManager:
    """工作区文件管理器"""
    
    def __init__(self, base_workspace_path: str = "workspaces"):
        self.base_workspace_path = Path(base_workspace_path)
    
    def get_agent_workspace_path(self, project_id: str, agent_id: str) -> Path:
        """获取指定智能体的工作区路径"""
        return self.base_workspace_path / project_id / agent_id
    
    def list_agent_files(self, project_id: str, agent_id: str, sub_dir: str = "") -> List[Dict]:
        """列出智能体工作区中的文件"""
        workspace_path = self.get_agent_workspace_path(project_id, agent_id)
        if sub_dir:
            workspace_path = workspace_path / sub_dir
        
        if not workspace_path.exists():
            return []
        
        files = []
        for file_path in workspace_path.rglob("*"):
            if file_path.is_file():
                # 获取相对路径
                relative_path = file_path.relative_to(workspace_path)
                
                # 获取文件信息
                stat = file_path.stat()
                file_info = {
                    "name": file_path.name,
                    "path": str(relative_path),
                    "full_path": str(file_path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": self._get_file_type(file_path),
                    "extension": file_path.suffix.lower()
                }
                files.append(file_info)
        
        # 按修改时间排序，最新的在前
        files.sort(key=lambda x: x["modified"], reverse=True)
        return files
    
    def read_file_content(self, file_path: str) -> Optional[Dict]:
        """读取文件内容"""
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            content = path.read_text(encoding='utf-8')
            stat = path.stat()
            
            return {
                "name": path.name,
                "content": content,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "type": self._get_file_type(path),
                "extension": path.suffix.lower()
            }
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    def get_markdown_preview(self, content: str, max_length: int = 500) -> str:
        """生成Markdown预览"""
        if len(content) <= max_length:
            return content
        
        # 截取前max_length个字符，并确保在完整句子处截断
        preview = content[:max_length]
        last_period = preview.rfind('.')
        if last_period > max_length * 0.8:  # 如果句号在80%位置之后，就在句号处截断
            preview = preview[:last_period + 1]
        
        return preview + "..."
    
    def _get_file_type(self, file_path: Path) -> str:
        """获取文件类型"""
        extension = file_path.suffix.lower()
        if extension in ['.md', '.markdown']:
            return 'markdown'
        elif extension in ['.txt']:
            return 'text'
        elif extension in ['.json']:
            return 'json'
        elif extension in ['.py']:
            return 'python'
        else:
            return 'unknown'
    
    def get_workspace_info(self, project_id: str, agent_id: str) -> Dict:
        """获取工作区信息"""
        workspace_path = self.get_agent_workspace_path(project_id, agent_id)
        
        if not workspace_path.exists():
            return {
                "exists": False,
                "path": str(workspace_path),
                "files": [],
                "total_files": 0
            }
        
        # 统计文件信息
        files = []
        total_size = 0
        for file_path in workspace_path.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                total_size += stat.st_size
                files.append({
                    "name": file_path.name,
                    "path": str(file_path.relative_to(workspace_path)),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return {
            "exists": True,
            "path": str(workspace_path),
            "files": files,
            "total_files": len(files),
            "total_size": total_size
        }

# 全局实例
workspace_manager = WorkspaceFileManager() 