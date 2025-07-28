#!/usr/bin/env python3
"""
AutoWriter Enhanced 重启脚本
清理端口并同时启动前端和后端服务
"""
import sys
import os
import subprocess
import time
import signal
from pathlib import Path
from threading import Thread

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

class ServiceManager:
    def __init__(self):
        self.processes = []
        self.project_root = project_root
        
    def kill_ports(self):
        """清理指定端口上的进程"""
        ports = [3000, 8001, 5173]  # 前端可能的端口和后端端口
        print("🧹 清理端口...")
        
        for port in ports:
            try:
                # 查找占用端口的进程
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"],
                    capture_output=True,
                    text=True
                )
                
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            try:
                                subprocess.run(["kill", "-9", pid], check=True)
                                print(f"✅ 已清理端口 {port} 上的进程 {pid}")
                            except subprocess.CalledProcessError:
                                print(f"⚠️  无法清理进程 {pid}")
                else:
                    print(f"✅ 端口 {port} 未被占用")
                    
            except subprocess.CalledProcessError:
                print(f"✅ 端口 {port} 未被占用")
            except Exception as e:
                print(f"⚠️  检查端口 {port} 时出错: {e}")
        
        print("🧹 端口清理完成")
        time.sleep(1)  # 等待端口释放
        
    def start_backend(self):
        """启动后端服务"""
        print("🚀 启动后端服务...")
        try:
            # 检查是否有虚拟环境
            venv_python = None
            possible_venv_paths = [
                self.project_root / "venv" / "bin" / "python",
                self.project_root / ".venv" / "bin" / "python",
                self.project_root / "env" / "bin" / "python"
            ]
            
            for venv_path in possible_venv_paths:
                if venv_path.exists():
                    venv_python = str(venv_path)
                    print(f"🐍 找到虚拟环境: {venv_python}")
                    break
            
            # 如果没有找到虚拟环境，使用系统Python
            if not venv_python:
                venv_python = sys.executable
                print(f"🐍 使用系统Python: {venv_python}")
            
            # 使用子进程启动后端
            backend_process = subprocess.Popen(
                [venv_python, "start_backend.py"],
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 将stderr重定向到stdout
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )
            
            self.processes.append(backend_process)
            
            # 等待一段时间检查进程是否正常启动
            time.sleep(2)
            if backend_process.poll() is not None:
                # 进程已经退出，读取错误信息
                stdout, _ = backend_process.communicate()
                print(f"❌ 后端服务启动失败，退出码: {backend_process.returncode}")
                print(f"错误信息: {stdout}")
                return None
            
            print("✅ 后端服务已启动在 http://localhost:8001")
            return backend_process
            
        except Exception as e:
            print(f"❌ 后端启动失败: {e}")
            return None
    
    def start_frontend(self):
        """启动前端服务（固定端口3000）"""
        print("🎨 启动前端服务...")
        try:
            frontend_dir = self.project_root / "frontend"
            
            # 检查是否存在node_modules
            if not (frontend_dir / "node_modules").exists():
                print("📦 安装前端依赖...")
                install_process = subprocess.run(
                    ["npm", "install"], 
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True
                )
                if install_process.returncode != 0:
                    print(f"❌ 前端依赖安装失败: {install_process.stderr}")
                    return None
                print("✅ 前端依赖安装完成")
            
            # 启动前端开发服务器（固定端口3000）
            frontend_process = subprocess.Popen(
                ["npm", "run", "dev", "--", "--port", "3000", "--host"],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes.append(frontend_process)
            print("✅ 前端服务已启动在 http://localhost:3000")
            return frontend_process
            
        except Exception as e:
            print(f"❌ 前端启动失败: {e}")
            return None
    
    def cleanup(self):
        """清理所有进程"""
        print("\n🛑 正在关闭服务...")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        print("✅ 所有服务已关闭")

def signal_handler(signum, frame):
    """处理Ctrl+C信号"""
    print("\n收到退出信号...")
    manager.cleanup()
    sys.exit(0)

if __name__ == "__main__":
    print("🔄 重启 AutoWriter Enhanced 全栈服务")
    print(f"📁 项目根目录: {project_root}")
    
    manager = ServiceManager()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 先清理端口
        manager.kill_ports()
        
        # 启动后端服务
        backend_process = manager.start_backend()
        if not backend_process:
            print("❌ 后端启动失败，退出")
            sys.exit(1)
        
        # 等待后端启动
        print("⏳ 等待后端服务启动...")
        time.sleep(3)
        
        # 启动前端服务
        frontend_process = manager.start_frontend()
        if not frontend_process:
            print("❌ 前端启动失败，但后端仍在运行")
        
        print("\n🎉 服务重启完成!")
        print("📱 前端地址: http://localhost:3000")
        print("🔧 后端地址: http://localhost:8001")
        print("📚 API文档: http://localhost:8001/docs")
        print("\n按 Ctrl+C 退出所有服务")
        
        # 保持主进程运行并监控服务状态
        restart_count = 0
        max_restarts = 3
        
        while True:
            time.sleep(5)  # 每5秒检查一次
            
            # 检查后端进程是否还在运行
            if backend_process and backend_process.poll() is not None:
                print("❌ 后端服务意外退出")
                if restart_count < max_restarts:
                    restart_count += 1
                    print(f"🔄 尝试重启后端服务 ({restart_count}/{max_restarts})")
                    time.sleep(2)
                    backend_process = manager.start_backend()
                    if backend_process:
                        print("✅ 后端服务重启成功")
                        time.sleep(3)  # 等待后端启动
                    else:
                        print("❌ 后端服务重启失败")
                else:
                    print("❌ 后端服务重启次数过多，停止重试")
                    break
                
            # 检查前端进程是否还在运行
            if frontend_process and frontend_process.poll() is not None:
                print("❌ 前端服务意外退出")
                if restart_count < max_restarts:
                    print(f"🔄 尝试重启前端服务")
                    time.sleep(2)
                    frontend_process = manager.start_frontend()
                    if frontend_process:
                        print("✅ 前端服务重启成功")
                    else:
                        print("❌ 前端服务重启失败")
                else:
                    print("❌ 前端服务重启次数过多，停止重试")
                
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ 启动过程中出现错误: {e}")
    finally:
        manager.cleanup()