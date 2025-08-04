#!/usr/bin/env python
"""
简化SOP测试 - 直接使用现有的Company服务
避免复杂的Team初始化问题
"""
import asyncio
import time
import tempfile
from pathlib import Path

from backend.services.company import Company
from metagpt.environment import Environment


async def simple_sop_test():
    """简单的SOP测试"""
    print("🧪 简化SOP流程测试")
    print("=" * 50)
    
    start_time = time.time()
    
    # 创建测试文档
    print("📄 创建测试文档...")
    test_content = """# 测试项目绩效评价

## 项目概述
本项目旨在通过数据分析和绩效评估，提升组织的整体运营效率。

## 关键指标
- **用户活跃度**: 月活跃用户数 (MAU)
- **转化效率**: 用户转化漏斗各阶段转化率
- **收入指标**: 月度经常性收入 (MRR)
- **客户满意度**: 净推荐值 (NPS)

## 数据源
- 用户行为数据
- 财务数据
- 客户反馈数据
- 市场竞争数据"""
    
    # 创建临时测试文件
    temp_dir = Path(tempfile.gettempdir()) / "simple_sop_test"
    temp_dir.mkdir(exist_ok=True)
    test_file = temp_dir / "test_document.md"
    test_file.write_text(test_content, encoding='utf-8')
    
    print(f"✅ 测试文档创建: {test_file}")
    
    try:
        # 使用现有的Company服务
        print("🏢 初始化Company服务...")
        company = Company()
        
        # 创建环境
        environment = Environment()
        
        # 执行SOP流程
        print("🚀 执行SOP流程...")
        test_message = "根据上传的文档内容作为辅助信息，同时可以检索网络案例找到合适的适配此项目的绩效评价指标，来辅助撰写《测试项目绩效分析报告》"
        
        result = await company.process_message(
            project_id="simple_sop_test",
            message=test_message,
            environment=environment,
            file_paths=[str(test_file)]
        )
        
        execution_time = time.time() - start_time
        
        print(f"✅ SOP流程执行完成 ({execution_time:.1f}秒)")
        print(f"📄 结果摘要: {result[:200]}..." if len(result) > 200 else f"📄 结果: {result}")
        
        # 检查生成的文件
        print("\n📁 检查生成的文件...")
        project_path = Path("workspace") / "simple_sop_test" / "docs"
        
        if project_path.exists():
            files = list(project_path.glob("*.md"))
            print(f"📊 生成文件数量: {len(files)}")
            
            for file_path in files:
                if file_path.stat().st_size > 0:
                    print(f"  📄 {file_path.name} ({file_path.stat().st_size} bytes)")
                else:
                    print(f"  📄 {file_path.name} (空文件)")
        else:
            print("⚠️  项目文件夹不存在")
            
        # 简单的成功判断
        has_files = project_path.exists() and len(list(project_path.glob("*.md"))) > 0
        has_content = len(result) > 100
        reasonable_time = execution_time < 300  # 5分钟内
        
        success = has_files and has_content and reasonable_time
        
        print(f"\n🎯 测试结果:")
        print(f"  📁 生成文件: {'✅' if has_files else '❌'}")
        print(f"  📝 有效内容: {'✅' if has_content else '❌'}")
        print(f"  ⏱️ 执行时间: {'✅' if reasonable_time else '❌'} ({execution_time:.1f}s)")
        print(f"  🎉 总体结果: {'✅ 成功' if success else '❌ 失败'}")
        
        return success
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理测试文件
        try:
            test_file.unlink()
            temp_dir.rmdir()
            print(f"🧹 清理测试文件: {test_file}")
        except:
            pass


if __name__ == "__main__":
    try:
        success = asyncio.run(simple_sop_test())
        if success:
            print("\n🎉 简化SOP测试通过！")
            exit(0)
        else:
            print("\n💥 简化SOP测试失败！")
            exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        exit(1)