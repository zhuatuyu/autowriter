"""
AutoWriter Enhanced - 主服务入口
基于 FastAPI + WebSocket 的多Agent协作系统
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import asyncio
from typing import Dict, List
import uuid
from datetime import datetime
from pathlib import Path

from backend.models.session import WorkSession, AgentMessage
# 使用新的核心管理器
from backend.services.orchestrator import core_manager
print("🚀 Using Core Manager")

from backend.services.websocket_manager import WebSocketManager

app = FastAPI(title="AutoWriter Enhanced", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局管理器
websocket_manager = WebSocketManager()

@app.get("/")
async def root():
    return {"message": "AutoWriter Enhanced API"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}



@app.post("/api/sessions")
async def create_session(project_info: dict):
    """创建新的工作会话"""
    session_id = str(uuid.uuid4())
    session = WorkSession(
        session_id=session_id,
        project_info=project_info,
        current_phase="analysis",
        current_chapter="",
        agent_reports={},
        editor_decisions=[],
        writing_drafts={},
        quality_scores={},
        client_interventions=[],
        checkpoints=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # 保存会话到数据库（暂时用内存）
    # TODO: 实现数据库持久化
    
    return {"session_id": session_id, "status": "created"}

@app.get("/api/sessions")
async def list_sessions():
    """获取会话列表"""
    try:
        sessions = core_manager.get_all_sessions()
        return {"sessions": sessions}
    except Exception as e:
        return {"sessions": [], "error": str(e)}

@app.get("/api/projects")
async def list_projects():
    """获取workspaces目录下的项目列表"""
    try:
        import os
        from pathlib import Path
        
        workspace_dir = Path("workspaces")
        projects = []
        
        if workspace_dir.exists():
            for project_path in workspace_dir.iterdir():
                if project_path.is_dir():
                    # 获取项目基本信息
                    project_info = {
                        'id': project_path.name,
                        'name': project_path.name.replace('_', ' ').replace('-', ' ').title(),
                        'type': '绩效评价',
                        'status': 'draft',
                        'lastModified': datetime.fromtimestamp(project_path.stat().st_mtime).strftime('%Y/%m/%d'),
                        'progress': 0
                    }
                    
                    # 检查是否有报告文件来判断进度
                    report_file = project_path / 'report.md'
                    if report_file.exists():
                        project_info['status'] = 'completed'
                        project_info['progress'] = 100
                    
                    # 检查是否有进度文件
                    progress_file = project_path / 'writing_progress.json'
                    if progress_file.exists():
                        try:
                            import json
                            with open(progress_file, 'r', encoding='utf-8') as f:
                                progress_data = json.load(f)
                                project_info['progress'] = progress_data.get('overall_progress', 0)
                                if project_info['progress'] > 0 and project_info['progress'] < 100:
                                    project_info['status'] = 'active'
                        except:
                            pass
                    
                    projects.append(project_info)
        
        return {"projects": projects}
    except Exception as e:
        return {"projects": [], "error": str(e)}

@app.get("/api/agents/{session_id}")
async def get_agents_status(session_id: str):
    """获取指定会话的所有Agent状态"""
    try:
        session_status = await core_manager.get_session_status(session_id)
        if 'error' in session_status:
            return {"agents": [], "error": session_status['error']}
        
        agents = session_status.get('agents', [])
        return {"agents": agents}
    except Exception as e:
        return {"agents": [], "error": str(e)}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket连接端点"""
    await websocket_manager.connect(websocket, session_id)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理不同类型的消息
            await handle_websocket_message(session_id, message)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(session_id)
        print(f"Client {session_id} disconnected")

async def handle_websocket_message(session_id: str, message: dict):
    """处理WebSocket消息"""
    message_type = message.get("type")
    
    if message_type == "user_message":
        # 用户插话
        await handle_user_intervention(session_id, message)
    elif message_type == "start_analysis":
        # 开始分析
        await start_agent_analysis(session_id, message)
    elif message_type == "pause_workflow":
        # 暂停工作流
        await pause_workflow(session_id)
    elif message_type == "resume_workflow":
        # 恢复工作流
        await resume_workflow(session_id)

async def handle_user_intervention(session_id: str, message: dict):
    """处理用户插话"""
    user_message = message.get("content", "")
    
    print(f"Received user message for session {session_id}: {user_message[:100]}...")
    
    # 立即回显用户消息
    await websocket_manager.send_message(session_id, {
        "type": "user_message",
        "sender": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat()
    })
    
    # 不再发送多余的“正在处理中”状态
    # await websocket_manager.send_message(session_id, {
    #     "type": "system_message",
    #     "sender": "system",
    #     "content": "正在处理您的消息...",
    #     "timestamp": datetime.now().isoformat()
    # })
    
    # 检查是否需要启动分析
    session_status = await core_manager.get_session_status(session_id)
    if 'error' in session_status:
        print(f"🚀 Detected new session, starting workflow for user message in session {session_id}")
        # 启动新的工作会话
        await core_manager.start_session(session_id)
        await core_manager.handle_user_message(session_id, user_message, websocket_manager)
    else:
        # 如果已经有活跃会话，作为用户输入处理
        await core_manager.handle_user_intervention(session_id, user_message, websocket_manager)

async def start_agent_analysis(session_id: str, message: dict):
    """启动Agent分析流程"""
    project_info = message.get("project_info", {})
    
    # 检查是否已经在运行分析
    session_status = await core_manager.get_session_status(session_id)
    if 'error' not in session_status and session_status.get("status") == "active":
        print(f"Analysis already started for session {session_id}, ignoring duplicate request")
        return
    
    # 启动工作流程
    await core_manager.start_session(session_id, project_info)
    await core_manager.handle_user_message(session_id, "开始分析", websocket_manager)

@app.post("/api/upload/{session_id}")
async def upload_file(session_id: str, file: UploadFile = File(...)):
    """处理文件上传，并直接将其存入文档专家的工作区"""
    try:
        # 直接定位到文档专家的工作目录
        # 注意: 'document_expert' 是我们在 prompts.py 中定义的 agent_id
        workspace_path = Path("workspaces") / session_id / "document_expert"
        upload_path = workspace_path / "uploads"
        upload_path.mkdir(parents=True, exist_ok=True)

        # 保存文件
        file_location = upload_path / file.filename
        with open(file_location, "wb+") as file_object:
            file_object.write(file.file.read())
        
        print(f"📄 文件已上传至文档专家工作区: {file_location}")

        # 通知项目总监有新文件
        user_message = f"用户上传了新文件 '{file.filename}'，已存入文档专家工作区，请您指示处理。"
        await core_manager.handle_user_message(session_id, user_message, websocket_manager)

        return {"status": "success", "filename": file.filename, "location": str(file_location)}
    except Exception as e:
        print(f"❌ 文件上传失败: {e}")
        return {"status": "error", "message": str(e)}


async def pause_workflow(session_id: str):
    """暂停工作流"""
    # TODO: 实现暂停功能
    await websocket_manager.send_message(session_id, {
        "type": "workflow_status",
        "status": "paused",
        "timestamp": datetime.now().isoformat()
    })

async def resume_workflow(session_id: str):
    """恢复工作流"""
    # TODO: 实现恢复功能
    await websocket_manager.send_message(session_id, {
        "type": "workflow_status",
        "status": "resumed",
        "timestamp": datetime.now().isoformat()
    })

@app.get("/api/test-agent-message/{session_id}")
async def test_agent_message(session_id: str):
    """测试Agent消息发送"""
    print(f"Testing agent message for session {session_id}")
    
    # 检查连接
    connection_count = websocket_manager.get_connection_count(session_id)
    print(f"Active connections: {connection_count}")
    
    if connection_count == 0:
        return {"error": "No active WebSocket connections for this session"}
    
    # 发送测试消息
    test_messages = [
        {
            "agent_type": "chief_editor",
            "agent_name": "总编",
            "content": "这是一条测试消息，测试WebSocket通信是否正常工作。",
            "status": "completed"
        },
        {
            "agent_type": "data_analyst",
            "agent_name": "数据分析师",
            "content": "开始分析项目数据...\n\n**分析要点**：\n1. 数据完整性评估\n2. 指标体系构建\n3. 质量评估",
            "status": "thinking"
        },
        {
            "agent_type": "policy_researcher",
            "agent_name": "政策研究员",
            "content": "正在检索相关政策法规...",
            "status": "completed"
        }
    ]
    
    # 依次发送测试消息
    for i, msg in enumerate(test_messages):
        await asyncio.sleep(1)  # 间隔1秒
        success = await websocket_manager.broadcast_agent_message(
            session_id=session_id,
            **msg
        )
        print(f"Message {i+1} sent: {success}")
    
    return {
        "status": "success",
        "messages_sent": len(test_messages),
        "active_connections": connection_count
    }

@app.get("/api/simple-test/{session_id}")
async def simple_test(session_id: str):
    """简单测试 - 直接发送消息"""
    print(f"Simple test for session {session_id}")
    
    # 直接发送一条消息
    success = await websocket_manager.broadcast_agent_message(
        session_id=session_id,
        agent_type="data_analyst",
        agent_name="数据分析师",
        content="这是一条直接的测试消息，检查WebSocket是否正常工作。",
        status="completed"
    )
    
    return {"success": success}

@app.get("/api/workflow-status/{session_id}")
async def get_workflow_status(session_id: str):
    """获取工作流程状态"""
    try:
        summary = await core_manager.get_session_status(session_id)
        return {"status": "success", "data": summary}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/user-intervention/{session_id}")
async def post_user_intervention(session_id: str, request: dict):
    """POST方式处理用户介入"""
    try:
        message = request.get("message", "")
        await core_manager.handle_user_intervention(session_id, message, websocket_manager)
        return {"status": "success", "message": "用户介入已处理"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/sessions/start-intelligent")
async def start_intelligent_workflow(request: dict):
    """启动智能项目总监工作流程"""
    try:
        session_id = request.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
        
        print(f"🧠 启动智能项目总监工作流程: {session_id}")
        
        # 启动智能项目总监工作流程
        await core_manager.start_session(session_id)
        await core_manager.handle_user_message(session_id, "启动智能项目总监工作流程", websocket_manager)
        
        return {
            "status": "success", 
            "session_id": session_id,
            "message": "智能项目总监工作流程已启动",
            "mode": "intelligent"
        }
    except Exception as e:
        print(f"❌ 启动智能项目总监工作流程失败: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/sessions/start-iterative")  
async def start_iterative_workflow(request: dict):
    """启动迭代式工作流程"""
    try:
        session_id = request.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
        
        print(f"🎯 启动迭代式工作流程: {session_id}")
        
        # 启动迭代式工作流程
        await core_manager.start_session(session_id)
        await core_manager.handle_user_message(session_id, "启动迭代式工作流程", websocket_manager)
        
        return {
            "status": "success", 
            "session_id": session_id,
            "message": "迭代式工作流程已启动",
            "mode": "iterative"
        }
    except Exception as e:
        print(f"❌ 启动迭代式工作流程失败: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)