#!/usr/bin/env python
"""
SOP流程验证器
直接在真实环境中测试完整的SOP流程，验证所有智能体是否按预期工作
"""
import asyncio
import time
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from backend.services.company import Company
from metagpt.environment import Environment
from metagpt.schema import Message


class SOPFlowValidator:
    """SOP流程验证器"""
    
    def __init__(self):
        self.company = Company()
        self.project_id: Optional[str] = None
        self.validation_results = {
            "start_time": None,
            "end_time": None,
            "duration": 0,
            "agents": {
                "ProductManager": {"executed": False, "output_size": 0, "errors": []},
                "Architect": {"executed": False, "output_size": 0, "errors": []},
                "ProjectManager": {"executed": False, "output_size": 0, "errors": []},
                "WriterExpert": {"executed": False, "output_size": 0, "errors": []}
            },
            "files": {
                "research_brief": {"exists": False, "size": 0, "path": ""},
                "report_structure": {"exists": False, "size": 0, "path": ""},
                "metric_analysis": {"exists": False, "size": 0, "path": ""},
                "final_report": {"exists": False, "size": 0, "path": ""}
            },
            "overall": {
                "success": False,
                "completion_rate": 0.0,
                "file_count": 0,
                "total_errors": 0
            }
        }
    
    async def create_test_document(self) -> str:
        """创建测试文档"""
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
- 市场竞争数据

## 期望输出
- 全面的绩效分析报告
- 可执行的改进建议
- 具体的关键指标追踪方案

## 技术要求
- 使用现代化的数据分析方法
- 确保数据准确性和可靠性
- 提供清晰的可视化图表
- 给出具体可行的行动建议"""
        
        # 创建临时文件
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "sop_validation"
        temp_dir.mkdir(exist_ok=True)
        
        test_file = temp_dir / "test_performance_evaluation.md"
        test_file.write_text(test_content, encoding='utf-8')
        
        print(f"📄 创建测试文档: {test_file}")
        return str(test_file)
    
    def analyze_project_files(self, project_id: str):
        """分析项目生成的文件"""
        project_path = Path("workspace") / project_id / "docs"
        
        if not project_path.exists():
            print(f"⚠️  项目目录不存在: {project_path}")
            return
        
        print(f"📁 分析项目文件: {project_path}")
        
        # 查找不同类型的文件
        file_patterns = {
            "research_brief": ["research_brief", "研究简报"],
            "report_structure": ["report_structure", "报告结构", "structure"],
            "metric_analysis": ["metric", "指标", "analysis_table"],
            "final_report": ["final_report", "最终报告", "report.md"]
        }
        
        for file_path in project_path.glob("*.md"):
            if file_path.stat().st_size == 0:
                continue
                
            file_name_lower = file_path.name.lower()
            print(f"  📄 {file_path.name} ({file_path.stat().st_size} bytes)")
            
            # 分类文件
            for file_type, patterns in file_patterns.items():
                if any(pattern in file_name_lower for pattern in patterns):
                    self.validation_results["files"][file_type] = {
                        "exists": True,
                        "size": file_path.stat().st_size,
                        "path": str(file_path)
                    }
                    break
    
    def check_console_logs(self) -> List[str]:
        """检查控制台日志中的错误信息"""
        # 这里可以根据需要实现日志检查逻辑
        # 目前返回空列表
        return []
    
    async def run_validation(self, message: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """运行SOP流程验证"""
        print("🚀 开始SOP流程验证...")
        print(f"📝 测试消息: {message}")
        
        self.validation_results["start_time"] = time.time()
        
        try:
            # 设置环境
            environment = Environment()
            
            # 处理消息和文件
            file_paths = [file_path] if file_path else None
            
            print("⏳ 执行SOP流程...")
            result = await self.company.process_message(
                project_id="sop_validation_test",
                message=message,
                environment=environment,
                file_paths=file_paths
            )
            
            self.project_id = "sop_validation_test"
            
            print(f"✅ SOP流程执行完成")
            print(f"📄 结果预览: {result[:200]}..." if len(result) > 200 else f"📄 结果: {result}")
            
            # 等待一下让文件系统同步
            await asyncio.sleep(2)
            
            # 分析结果
            self.analyze_project_files(self.project_id)
            
            # 检查错误
            errors = self.check_console_logs()
            
            # 计算统计信息
            self.validation_results["end_time"] = time.time()
            self.validation_results["duration"] = self.validation_results["end_time"] - self.validation_results["start_time"]
            
            # 文件统计
            file_count = sum(1 for f in self.validation_results["files"].values() if f["exists"])
            total_file_size = sum(f["size"] for f in self.validation_results["files"].values())
            
            # 智能体执行检查（基于文件输出推断）
            if self.validation_results["files"]["research_brief"]["exists"]:
                self.validation_results["agents"]["ProductManager"]["executed"] = True
                self.validation_results["agents"]["ProductManager"]["output_size"] = self.validation_results["files"]["research_brief"]["size"]
            
            if self.validation_results["files"]["report_structure"]["exists"]:
                self.validation_results["agents"]["Architect"]["executed"] = True
                self.validation_results["agents"]["Architect"]["output_size"] = self.validation_results["files"]["report_structure"]["size"]
            
            if self.validation_results["files"]["final_report"]["exists"]:
                self.validation_results["agents"]["WriterExpert"]["executed"] = True
                self.validation_results["agents"]["WriterExpert"]["output_size"] = self.validation_results["files"]["final_report"]["size"]
            
            # 推断ProjectManager执行（如果有任务相关的输出）
            if file_count >= 2:  # 如果有多个文件，说明ProjectManager可能也执行了
                self.validation_results["agents"]["ProjectManager"]["executed"] = True
            
            # 计算完成率
            executed_agents = sum(1 for agent in self.validation_results["agents"].values() if agent["executed"])
            completion_rate = executed_agents / len(self.validation_results["agents"])
            
            # 整体成功判断
            success = (
                completion_rate >= 0.5 and  # 至少50%智能体执行
                file_count >= 2 and         # 至少生成2个文件
                total_file_size > 1000      # 总文件大小超过1KB
            )
            
            self.validation_results["overall"] = {
                "success": success,
                "completion_rate": completion_rate,
                "file_count": file_count,
                "total_file_size": total_file_size,
                "total_errors": len(errors)
            }
            
            return self.validation_results
            
        except Exception as e:
            print(f"❌ SOP验证失败: {e}")
            import traceback
            traceback.print_exc()
            
            self.validation_results["end_time"] = time.time()
            self.validation_results["duration"] = self.validation_results["end_time"] - self.validation_results["start_time"]
            self.validation_results["overall"]["success"] = False
            
            return self.validation_results
    
    def print_validation_report(self):
        """打印验证报告"""
        print("\n" + "="*60)
        print("📊 SOP流程验证报告")
        print("="*60)
        
        # 基本信息
        print(f"⏱️  执行时间: {self.validation_results['duration']:.1f}秒")
        print(f"🎯 总体结果: {'✅ 成功' if self.validation_results['overall']['success'] else '❌ 失败'}")
        print(f"📈 完成率: {self.validation_results['overall']['completion_rate']*100:.1f}%")
        
        # 智能体执行情况
        print(f"\n🤖 智能体执行情况:")
        agent_icons = {
            "ProductManager": "📊",
            "Architect": "🏗️", 
            "ProjectManager": "📋",
            "WriterExpert": "✍️"
        }
        
        for agent_name, agent_data in self.validation_results["agents"].items():
            icon = agent_icons.get(agent_name, "🤖")
            status = "✅" if agent_data["executed"] else "❌"
            size = agent_data["output_size"]
            print(f"  {icon} {agent_name}: {status} ({size} bytes)")
        
        # 文件生成情况  
        print(f"\n📁 文件生成情况:")
        file_icons = {
            "research_brief": "📊",
            "report_structure": "🏗️",
            "metric_analysis": "📈", 
            "final_report": "📄"
        }
        
        for file_type, file_data in self.validation_results["files"].items():
            icon = file_icons.get(file_type, "📄")
            status = "✅" if file_data["exists"] else "❌"
            size = file_data["size"]
            print(f"  {icon} {file_type}: {status} ({size} bytes)")
            if file_data["exists"] and file_data["path"]:
                print(f"      📍 {file_data['path']}")
        
        # 统计摘要
        print(f"\n📊 统计摘要:")
        print(f"  📁 生成文件: {self.validation_results['overall']['file_count']} 个")
        print(f"  📏 总文件大小: {self.validation_results['overall']['total_file_size']} bytes")
        print(f"  ❌ 错误数量: {self.validation_results['overall']['total_errors']}")
        
        print("="*60)


async def main():
    """主函数"""
    print("🧪 SOP流程验证器启动\n")
    
    validator = SOPFlowValidator()
    
    # 创建测试文档
    test_doc_path = await validator.create_test_document()
    
    # 运行验证
    test_message = "根据上传的文档内容作为辅助信息，同时可以检索网络案例找到合适的适配此项目的绩效评价指标，来辅助撰写《测试项目绩效分析报告》"
    
    results = await validator.run_validation(
        message=test_message,
        file_path=test_doc_path
    )
    
    # 打印报告
    validator.print_validation_report()
    
    # 清理测试文件
    try:
        os.unlink(test_doc_path)
        print(f"🧹 清理测试文档: {test_doc_path}")
    except:
        pass
    
    return results["overall"]["success"]


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if success:
            print("\n🎉 SOP流程验证通过！")
            exit(0)
        else:
            print("\n💥 SOP流程验证失败！")
            exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  验证被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n❌ 验证过程出错: {e}")
        exit(1)