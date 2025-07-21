"""
WebSocket连接管理器 - 简化版本参考magentic-ui
"""
from fastapi import WebSocket
from typing import Dict
import json
from datetime import datetime

class WebSocketManager:
    def __init__(self):
        # 简化：每个session只保持一个连接
        self.connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        
        # 如果已有连接，先关闭旧连接
        if session_id in self.connections:
            try:
                await self.connections[session_id].close()
            except:
                pass
        
        # 保存新连接
        self.connections[session_id] = websocket
        print(f"✅ Client connected to session {session_id}")
        
        # 发送连接确认消息
        await self.send_message(session_id, {
            "type": "connection_established",
            "session_id": session_id,
            "message": "Connected to AutoWriter Enhanced"
        })
    
    def disconnect(self, session_id: str):
        """断开WebSocket连接"""
        if session_id in self.connections:
            del self.connections[session_id]
            print(f"❌ Client disconnected from session {session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """发送消息到指定session"""
        if session_id not in self.connections:
            print(f"❌ No connection found for session {session_id}")
            return False
            
        try:
            websocket = self.connections[session_id]
            await websocket.send_text(json.dumps(message))
            print(f"✅ Message sent to session {session_id}: {message.get('type', 'unknown')}")
            return True
        except Exception as e:
            print(f"❌ Error sending message to session {session_id}: {e}")
            # 连接出错，移除连接
            if session_id in self.connections:
                del self.connections[session_id]
            return False
    
    def get_connection_count(self, session_id: str) -> int:
        """获取指定session的连接数"""
        return 1 if session_id in self.connections else 0
    
    async def broadcast_agent_message(self, session_id: str, agent_type: str, agent_name: str, content: str, status: str = "sent"):
        """广播Agent消息"""
        message = {
            "type": "agent_message",
            "agent_type": agent_type,
            "agent_name": agent_name,
            "content": content,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        print(f"🔥 Broadcasting agent message: {agent_name} - {content[:50]}...")
        return await self.send_message(session_id, message)
    
    async def broadcast_report_update(self, session_id: str, chapter: str, content: str, version: int):
        """广播报告更新"""
        message = {
            "type": "report_update",
            "chapter": chapter,
            "content": content,
            "version": version,
            "timestamp": datetime.now().isoformat()
        }
        return await self.send_message(session_id, message)
    
    async def broadcast_workflow_status(self, session_id: str, phase: str, progress: int):
        """广播工作流状态"""
        message = {
            "type": "workflow_status",
            "phase": phase,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        }
        return await self.send_message(session_id, message)