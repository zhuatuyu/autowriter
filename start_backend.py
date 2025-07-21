#!/usr/bin/env python3
"""
AutoWriter Enhanced 后端启动脚本
正确设置Python路径并启动服务
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

# 现在可以正常导入模块
if __name__ == "__main__":
    import uvicorn
    
    print("🚀 启动 AutoWriter Enhanced 后端服务")
    print(f"📁 项目根目录: {project_root}")
    print(f"🐍 Python路径: {sys.path[:3]}")
    
    # 使用字符串导入方式以支持reload
    uvicorn.run(
        "backend.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=[str(project_root / "backend")]
    )