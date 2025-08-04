#!/usr/bin/env python
"""
快速SOP测试脚本
用于快速验证ProductManager -> Architect -> ProjectManager -> WriterExpert流程
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 切换到项目根目录以确保正确的相对路径
os.chdir(project_root)

# 直接导入测试模块
try:
    from tests.test_complete_sop_flow import run_test
except ImportError:
    # 如果上面的导入失败，尝试直接执行文件
    import subprocess
    print("🔄 使用备用导入方式...")
    
    def run_test():
        """备用测试运行函数"""
        try:
            result = subprocess.run([sys.executable, "tests/test_complete_sop_flow.py"], 
                                  capture_output=True, text=True, cwd=project_root)
            return {"overall": {"success": result.returncode == 0}}
        except Exception as e:
            print(f"❌ 备用测试失败: {e}")
            return {"overall": {"success": False}}


def quick_test():
    """快速测试函数"""
    print("🚀 开始快速SOP测试...")
    
    results = run_test()
    
    if not results:
        print("❌ 测试失败 - 无结果返回")
        return False
    
    # 简化的成功标准
    success_criteria = {
        "至少3个智能体执行": sum(1 for key in ["product_manager", "architect", "project_manager", "writer_expert"] 
                           if results[key]["executed"]) >= 3,
        "生成至少2个文件": results["overall"]["total_files"] >= 2,
        "无严重错误": results["overall"]["success"],
        "执行时间合理": results["overall"]["execution_time"] < 300  # 5分钟内
    }
    
    print("\n📊 快速测试结果:")
    all_passed = True
    for criterion, passed in success_criteria.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {criterion}")
        if not passed:
            all_passed = False
    
    print(f"\n🎯 快速测试: {'✅ 通过' if all_passed else '❌ 失败'}")
    return all_passed


if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)