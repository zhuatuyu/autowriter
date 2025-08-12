#!/usr/bin/env python
"""
完整SOP流程测试
测试 ProductManager -> Architect -> ProjectManager -> WriterExpert 的完整工作流
"""
import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# 添加项目路径到sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagpt.environment import Environment
from metagpt.team import Team
from metagpt.schema import Message
from metagpt.utils.project_repo import ProjectRepo

from backend.roles.product_manager import ProductManager
from backend.roles.architect_content import ArchitectContent as Architect
from backend.roles.project_manager import ProjectManager as PM
from backend.roles.section_writer import SectionWriter as WriterExpert
from backend.roles.custom_team_leader import CustomTeamLeader


class SOPFlowTester:
    """SOP流程测试器"""
    
    def __init__(self):
        self.temp_dir = None
        self.project_repo = None
        self.team = None
        self.test_results = {
            "product_manager": {"executed": False, "files_created": [], "errors": []},
            "architect": {"executed": False, "files_created": [], "errors": []},
            "project_manager": {"executed": False, "files_created": [], "errors": []},
            "writer_expert": {"executed": False, "files_created": [], "errors": []},
            "overall": {"success": False, "total_files": 0, "execution_time": 0}
        }
    
    async def setup_test_environment(self):
        """设置测试环境"""
        print("🔧 设置测试环境...")
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="sop_test_")
        print(f"📁 临时目录: {self.temp_dir}")
        
        # 创建ProjectRepo
        self.project_repo = ProjectRepo(Path(self.temp_dir))
        
        # 创建上传目录和测试文件
        upload_dir = Path(self.temp_dir) / "uploads"
        upload_dir.mkdir(exist_ok=True)
        
        # 创建测试文档
        test_doc = upload_dir / "test_document.md"
        test_doc.write_text("""
# 测试项目文档

## 项目背景
这是一个测试项目，用于验证SOP流程的完整性。

## 关键指标
- 用户活跃度：提升20%
- 转化率：目标5%
- 收入增长：年增长15%

## 技术要求
- 使用现代化的分析方法
- 确保数据准确性
- 提供可操作的建议
        """)
        
        print(f"✅ 测试文档创建: {test_doc}")
        return str(test_doc)
    
    async def create_test_team(self):
        """创建测试团队"""
        print("👥 创建测试团队...")
        
        # 创建环境
        environment = Environment()
        
        # 创建智能体
        team_leader = CustomTeamLeader()
        product_manager = ProductManager()
        architect = Architect()
        project_manager = PM()
        writer_expert = WriterExpert()
        
        # 为需要文件访问的智能体注入project_repo
        product_manager._project_repo = self.project_repo
        architect._project_repo = self.project_repo
        writer_expert._project_repo = self.project_repo
        
        # 创建团队
        self.team = Team(
            investment=10.0,
            environment=environment,
            roles=[team_leader, product_manager, architect, project_manager, writer_expert]
        )
        
        print("✅ 团队创建完成")
        return self.team
    
    def check_agent_execution(self, agent_name: str, memory_messages):
        """检查智能体是否执行并生成了预期输出"""
        executed = False
        files_created = []
        errors = []
        
        for msg in memory_messages:
            # 检查是否是该智能体发送的消息
            if hasattr(msg, 'sent_from') and msg.sent_from:
                sender_class = msg.sent_from.__class__.__name__
                if agent_name.lower() in sender_class.lower():
                    executed = True
                    print(f"✅ {agent_name} 已执行，输出: {msg.content[:100]}...")
            
            # 检查是否有错误
            if "错误" in str(msg.content) or "失败" in str(msg.content):
                errors.append(str(msg.content))
        
        # 检查文件输出
        docs_dir = Path(self.project_repo.workdir) / "docs"
        if docs_dir.exists():
            for file_path in docs_dir.glob("*.md"):
                if file_path.stat().st_size > 0:  # 文件非空
                    files_created.append(str(file_path.name))
        
        return {
            "executed": executed,
            "files_created": files_created,
            "errors": errors
        }
    
    def analyze_file_outputs(self):
        """分析文件输出"""
        expected_files = {
            "research_brief.md": "ProductManager的研究简报",
            "report_structure.md": "Architect的报告结构", 
            "metric_analysis_table.md": "Architect的指标分析表",
            "task_plan.md": "ProjectManager的任务计划",
            "final_report.md": "WriterExpert的最终报告"
        }
        
        docs_dir = Path(self.project_repo.workdir) / "docs"
        actual_files = []
        
        if docs_dir.exists():
            for file_path in docs_dir.glob("*.md"):
                if file_path.stat().st_size > 0:
                    actual_files.append(file_path.name)
                    print(f"📄 文件: {file_path.name} ({file_path.stat().st_size} bytes)")
        
        print(f"\n📊 文件分析:")
        print(f"   预期文件类型: {len(expected_files)}")
        print(f"   实际生成文件: {len(actual_files)}")
        
        # 检查是否包含关键文件模式
        key_patterns = ["research_brief", "report_structure", "metric", "final_report"]
        found_patterns = []
        
        for pattern in key_patterns:
            for actual_file in actual_files:
                if pattern in actual_file.lower():
                    found_patterns.append(pattern)
                    break
        
        print(f"   关键文件模式匹配: {len(found_patterns)}/{len(key_patterns)}")
        return len(actual_files), found_patterns
    
    async def run_sop_test(self, test_message: str, file_paths: list = None):
        """运行完整的SOP测试"""
        import time
        start_time = time.time()
        
        print("🚀 开始SOP流程测试...")
        print(f"📝 测试消息: {test_message}")
        
        try:
            # 发布初始消息
            initial_message = Message(
                content=test_message,
                role="user"
            )
            
            # 如果有文件路径，设置到环境中
            if file_paths:
                # 模拟文件上传
                for file_path in file_paths:
                    print(f"📎 处理文件: {file_path}")
            
            # 运行团队
            print("⏳ 执行SOP流程 (最多5轮)...")
            await self.team.run(n_round=5)
            
            # 分析结果
            print("\n📈 分析执行结果...")
            
            # 获取所有消息记忆
            all_messages = []
            # Team对象的roles属性可能不存在，尝试通过environment获取
            if hasattr(self.team, 'roles'):
                roles = self.team.roles
            elif hasattr(self.team, 'env') and hasattr(self.team.env, 'roles'):
                roles = self.team.env.roles.values()
            else:
                print("⚠️  无法获取团队角色，使用空消息列表")
                roles = []
            
            for role in roles:
                if hasattr(role, 'rc') and hasattr(role.rc, 'memory'):
                    role_messages = role.rc.memory.get()
                    all_messages.extend(role_messages)
            
            # 检查各智能体执行情况
            agents = {
                "ProductManager": "product_manager",
                "Architect": "architect", 
                "ProjectManager": "project_manager",
                "WriterExpert": "writer_expert"
            }
            
            for agent_class, agent_key in agents.items():
                result = self.check_agent_execution(agent_class, all_messages)
                self.test_results[agent_key] = result
                
                print(f"\n🤖 {agent_class}:")
                print(f"   执行状态: {'✅' if result['executed'] else '❌'}")
                print(f"   错误数量: {len(result['errors'])}")
                if result['errors']:
                    for error in result['errors'][:3]:  # 只显示前3个错误
                        print(f"   ❌ {error[:100]}...")
            
            # 分析文件输出
            total_files, found_patterns = self.analyze_file_outputs()
            
            # 计算总体成功率
            executed_agents = sum(1 for agent_key in agents.values() 
                                if self.test_results[agent_key]["executed"])
            success_rate = executed_agents / len(agents)
            
            execution_time = time.time() - start_time
            
            self.test_results["overall"] = {
                "success": success_rate >= 0.75 and total_files >= 3,  # 至少75%智能体执行且生成至少3个文件
                "total_files": total_files,
                "execution_time": execution_time,
                "success_rate": success_rate,
                "key_patterns_found": len(found_patterns) if found_patterns else 0
            }
            
            print(f"\n🎯 整体评估:")
            print(f"   成功率: {success_rate*100:.1f}% ({executed_agents}/{len(agents)} 智能体)")
            print(f"   文件生成: {total_files} 个")
            print(f"   关键模式: {len(found_patterns)}/4")
            print(f"   执行时间: {execution_time:.1f}秒")
            print(f"   总体结果: {'✅ 成功' if self.test_results['overall']['success'] else '❌ 失败'}")
            
            return self.test_results
            
        except Exception as e:
            print(f"❌ SOP测试失败: {e}")
            import traceback
            traceback.print_exc()
            self.test_results["overall"] = {
                "success": False,
                "total_files": 0,
                "execution_time": time.time() - start_time,
                "success_rate": 0.0,
                "key_patterns_found": 0
            }
            return self.test_results
    
    def cleanup(self):
        """清理测试环境"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                print(f"🧹 清理临时目录: {self.temp_dir}")
            except Exception as e:
                print(f"⚠️  清理失败: {e}")
    
    def generate_test_report(self):
        """生成测试报告"""
        report = []
        report.append("# SOP流程测试报告\n")
        report.append(f"**执行时间**: {self.test_results['overall']['execution_time']:.1f}秒\n")
        report.append(f"**总体结果**: {'✅ 通过' if self.test_results['overall']['success'] else '❌ 失败'}\n")
        
        report.append("\n## 智能体执行情况\n")
        
        agent_names = {
            "product_manager": "📊 ProductManager",
            "architect": "🏗️ Architect",
            "project_manager": "📋 ProjectManager", 
            "writer_expert": "✍️ WriterExpert"
        }
        
        for agent_key, agent_name in agent_names.items():
            result = self.test_results[agent_key]
            status = "✅" if result["executed"] else "❌"
            report.append(f"- {agent_name}: {status}")
            report.append(f"  - 文件输出: {len(result['files_created'])} 个")
            report.append(f"  - 错误数量: {len(result['errors'])}")
            if result["files_created"]:
                report.append(f"  - 生成文件: {', '.join(result['files_created'])}")
            report.append("")
        
        report.append(f"\n## 文件输出统计\n")
        report.append(f"- 总文件数: {self.test_results['overall']['total_files']}")
        report.append(f"- 关键模式匹配: {self.test_results['overall']['key_patterns_found']}/4")
        
        return "\n".join(report)


async def main():
    """主测试函数"""
    print("🧪 启动完整SOP流程测试\n")
    
    tester = SOPFlowTester()
    
    try:
        # 设置测试环境
        test_doc_path = await tester.setup_test_environment()
        
        # 创建测试团队
        await tester.create_test_team()
        
        # 运行测试
        test_message = "根据上传的文档内容作为辅助信息，同时可以检索网络案例找到合适的适配此项目的绩效评价指标，来辅助撰写《测试项目绩效分析报告》"
        
        results = await tester.run_sop_test(
            test_message=test_message,
            file_paths=[test_doc_path]
        )
        
        # 生成报告
        print("\n" + "="*60)
        print(tester.generate_test_report())
        print("="*60)
        
        # 返回结果供外部使用
        return results
        
    finally:
        # 清理
        tester.cleanup()


def run_test():
    """运行测试的便捷函数"""
    try:
        results = asyncio.run(main())
        return results
    except Exception as e:
        print(f"❌ 测试运行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    results = run_test()
    
    if results and results["overall"]["success"]:
        print("\n🎉 SOP流程测试通过！")
        sys.exit(0)
    else:
        print("\n💥 SOP流程测试失败！")
        sys.exit(1)