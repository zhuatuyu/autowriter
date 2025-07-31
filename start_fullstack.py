#!/usr/bin/env python3
"""
AutoWriter Enhanced 全栈启动脚本
同时启动前端和后端服务，避免端口冲突
"""
import sys
import os
import subprocess
import threading
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def start_backend():
    """启动后端服务"""
    print("🚀 启动后端服务 (端口: 8001)")
    import uvicorn
    uvicorn.run(
        "backend.main:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=True,
        reload_dirs=[str(project_root / "backend")]
    )

def start_frontend():
    """启动前端服务"""
    print("🌐 启动前端服务 (端口: 3003)")
    frontend_dir = project_root / "frontend"
    
    # 等待后端启动
    time.sleep(3)
    
    try:
        # 使用npm启动前端
        subprocess.run([
            "npm", "run", "dev"
        ], cwd=frontend_dir, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 前端启动失败: {e}")
    except FileNotFoundError:
        print("❌ 未找到npm命令，请确保已安装Node.js")

if __name__ == "__main__":
    print("🚀 启动 AutoWriter Enhanced 全栈服务")
    print(f"📁 项目根目录: {project_root}")
    print("=" * 50)
    
    # 在后台线程启动前端
    frontend_thread = threading.Thread(target=start_frontend, daemon=True)
    frontend_thread.start()
    
    # 在主线程启动后端
    try:
        start_backend()
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
        sys.exit(0)