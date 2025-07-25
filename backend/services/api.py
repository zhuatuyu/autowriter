from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
from pydantic import BaseModel
import os
from pathlib import Path

from backend.utils.file_utils import workspace_manager

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

class FileInfo(BaseModel):
    name: str
    path: str
    full_path: str
    size: int
    modified: str
    type: str
    extension: str

class FileContent(BaseModel):
    name: str
    content: str
    size: int
    modified: str
    type: str
    extension: str

class WorkspaceInfo(BaseModel):
    exists: bool
    path: str
    files: List[Dict]
    total_files: int
    total_size: int

@router.get("/files/{project_id}/{agent_id}")
async def list_agent_files(
    project_id: str,
    agent_id: str,
    sub_dir: Optional[str] = Query(None, description="子目录路径")
) -> List[FileInfo]:
    """列出智能体工作区中的文件"""
    try:
        files = workspace_manager.list_agent_files(project_id, agent_id, sub_dir or "")
        return [FileInfo(**file_info) for file_info in files]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@router.get("/file/content")
async def get_file_content(file_path: str) -> FileContent:
    """读取指定文件的内容"""
    try:
        file_info = workspace_manager.read_file_content(file_path)
        if file_info is None:
            raise HTTPException(status_code=404, detail="File not found")
        return FileContent(**file_info)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

@router.get("/info/{project_id}/{agent_id}")
async def get_workspace_info(project_id: str, agent_id: str) -> WorkspaceInfo:
    """获取工作区信息"""
    try:
        info = workspace_manager.get_workspace_info(project_id, agent_id)
        return WorkspaceInfo(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workspace info: {str(e)}")

@router.get("/preview/{project_id}/{agent_id}")
async def get_latest_file_preview(
    project_id: str,
    agent_id: str,
    sub_dir: Optional[str] = Query(None, description="子目录路径")
) -> Dict:
    """获取最新文件的预览"""
    try:
        files = workspace_manager.list_agent_files(project_id, agent_id, sub_dir or "")
        if not files:
            return {"preview": None, "message": "No files found"}
        
        # 获取最新的文件
        latest_file = files[0]
        file_content = workspace_manager.read_file_content(latest_file["full_path"])
        
        if file_content is None:
            return {"preview": None, "message": "Failed to read latest file"}
        
        # 生成预览
        preview = workspace_manager.get_markdown_preview(file_content["content"])
        
        return {
            "preview": preview,
            "file_info": latest_file,
            "full_content": file_content["content"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get preview: {str(e)}")

# 案例专家特定的API端点
@router.get("/case-expert/{project_id}/reports")
async def get_case_expert_reports(project_id: str) -> List[Dict]:
    """获取案例专家的报告列表"""
    try:
        files = workspace_manager.list_agent_files(project_id, "case_expert", "cases")
        
        # 过滤出markdown文件并格式化
        reports = []
        for file_info in files:
            if file_info["type"] == "markdown":
                # 从文件名提取信息
                name = file_info["name"]
                # 移除扩展名
                title = name.replace(".md", "")
                
                # 截取文件名前40个字符，避免界面被撑破
                display_title = title[:40] + "..." if len(title) > 40 else title
                
                # 尝试从文件名提取日期
                date_str = "未知日期"
                if "_" in title:
                    parts = title.split("_")
                    if len(parts) >= 3:
                        # 假设最后两部分是日期
                        date_str = f"{parts[-2]}_{parts[-1]}"
                
                report = {
                    "id": file_info["path"],
                    "title": display_title,
                    "full_title": title,  # 保留完整标题用于其他用途
                    "date": date_str,
                    "status": "completed",
                    "summary": workspace_manager.get_markdown_preview(
                        workspace_manager.read_file_content(file_info["full_path"])["content"], 
                        200
                    ),
                    "taskType": "案例研究报告",
                    "file_info": file_info
                }
                reports.append(report)
        
        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get case expert reports: {str(e)}")

@router.get("/case-expert/{project_id}/report/{report_id:path}")
async def get_case_expert_report(project_id: str, report_id: str) -> Dict:
    """获取案例专家的特定报告内容"""
    try:
        # 构建文件路径
        file_path = workspace_manager.get_agent_workspace_path(project_id, "case_expert") / "cases" / report_id
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        file_content = workspace_manager.read_file_content(str(file_path))
        if file_content is None:
            raise HTTPException(status_code=500, detail="Failed to read report content")
        
        # 截取文件名前40个字符
        full_title = file_content["name"].replace(".md", "")
        display_title = full_title[:40] + "..." if len(full_title) > 40 else full_title
        
        return {
            "id": report_id,
            "title": display_title,
            "full_title": full_title,
            "content": file_content["content"],
            "modified": file_content["modified"],
            "size": file_content["size"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get report: {str(e)}") 