#!/usr/bin/env python3
"""
AutoWriter Chainlit应用启动脚本
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """启动Chainlit应用"""
    # 设置项目根目录
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # 检查依赖
    try:
        import chainlit
        print("✅ Chainlit已安装")
    except ImportError:
        print("❌ Chainlit未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "chainlit_requirements.txt"])
    
    # 设置环境变量
    os.environ["PYTHONPATH"] = str(project_root)
    
    # 启动Chainlit应用
    print("🚀 启动AutoWriter Chainlit应用...")
    print("📱 访问地址: http://localhost:8000")
    
    try:
        # 使用chainlit run命令启动
        subprocess.run([
            sys.executable, "-m", "chainlit", "run", "chainlit_app.py",
            "--host", "0.0.0.0",
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main()