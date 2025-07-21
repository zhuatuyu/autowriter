#!/usr/bin/env python3
"""
AutoWriter Enhanced 后端启动脚本
"""
import sys
import os
import subprocess

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def activate_venv_and_run():
    """激活虚拟环境并启动服务"""
    venv_path = os.path.join(os.path.dirname(__file__), 'venv')
    
    if os.path.exists(venv_path):
        # 使用虚拟环境中的Python
        python_path = os.path.join(venv_path, 'bin', 'python')
        if not os.path.exists(python_path):
            print("❌ 虚拟环境中找不到Python，请重新创建虚拟环境")
            return
        
        print("🚀 启动 AutoWriter Enhanced 后端服务...")
        print("📡 WebSocket 端点: ws://localhost:8000/ws/{session_id}")
        print("🌐 API 文档: http://localhost:8000/docs")
        print("❤️  健康检查: http://localhost:8000/api/health")
        print("-" * 50)
        
        # 使用虚拟环境中的uvicorn
        cmd = [
            python_path, '-m', 'uvicorn',
            'backend.main:app',
            '--host', '0.0.0.0',
            '--port', '8000',
            '--reload',
            '--log-level', 'info'
        ]
        
        subprocess.run(cmd)
    else:
        print("❌ 找不到虚拟环境，请先运行 ./fix_dependencies.sh")

if __name__ == "__main__":
    activate_venv_and_run()