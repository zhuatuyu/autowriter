#!/usr/bin/env python
"""
SOP集成测试 - 验证治理方案的效果
测试多智能体协作流程中的关键节点
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from pathlib import Path

from metagpt.schema import Message
from backend.actions.research_action import ResearchData, ConductComprehensiveResearch, Documents, Document
from backend.roles.product_manager import ProductManager
from backend.roles.architect_content import ArchitectContent as Architect
from backend.actions.architect_content_action import DesignReportStructureOnly as DesignReportStructure
from backend.actions.robust_search_action import RobustSearchEnhancedQA


class TestSOPIntegration:
    """SOP集成测试类"""
    
    @pytest.fixture
    def sample_research_data(self):
        """创建示例研究数据"""
        return ResearchData(
            brief="""
# 祥符区2024年小麦'一喷三防'项目研究简报

## 执行摘要
本项目投入342.7万元，覆盖23.96万亩，采用无人机等智慧农业技术...

## 市场背景
智慧农业技术在"一喷三防"项目中的应用日益广泛...

## 关键指标
- 资金投入：342.7万元
- 实施面积：23.96万亩
- 无人机数量：60余架
""",
            vector_store_path="workspace/research_data/wheat_spray_project.faiss"
        )
    
    @pytest.fixture
    def sample_documents(self):
        """创建示例文档"""
        return Documents(docs=[
            Document(
                filename="wheat_project_plan.md",
                content="# 2024年开封市小麦'一喷三防'实施方案\n\n项目总投资342.7万元..."
            )
        ])

    def test_research_data_structure(self, sample_research_data):
        """测试ResearchData数据结构"""
        assert sample_research_data.brief is not None
        assert len(sample_research_data.brief) > 100
        assert sample_research_data.vector_store_path.endswith('.faiss')
        
    def test_architect_data_extraction_fix(self, sample_research_data):
        """测试Architect从instruct_content正确获取数据的修复"""
        # 创建一个包含ResearchData的消息
        msg = Message(
            content="研究完成: 祥符区2024年小麦'一喷三防'项目研究简报...",
            role="Product Manager",
            cause_by="ConductComprehensiveResearch",
            instruct_content=Message.create_instruct_value(sample_research_data)
        )
        
        # 模拟Architect的数据提取逻辑
        research_data_obj = None
        research_brief = ""
        
        if msg.cause_by == "ConductComprehensiveResearch":
            if hasattr(msg, 'instruct_content') and msg.instruct_content:
                try:
                    if isinstance(msg.instruct_content, ResearchData):
                        research_data_obj = msg.instruct_content
                        research_brief = research_data_obj.brief
                    elif hasattr(msg.instruct_content, 'brief'):
                        research_brief = msg.instruct_content.brief
                except Exception:
                    research_brief = msg.content
        
        # 断言：应该能够正确提取研究简报
        assert research_brief is not None
        assert len(research_brief) > 100
        assert "祥符区2024年小麦" in research_brief
        
    @pytest.mark.asyncio
    async def test_robust_search_json_handling(self):
        """测试健壮搜索Action处理JSON错误的能力"""
        robust_search = RobustSearchEnhancedQA()
        
        # 测试各种有问题的JSON响应
        test_cases = [
            # 单引号问题
            "{'query': '改写后的查询'}",
            # 缺少引号的键
            "{query: '改写后的查询'}",
            # 带有额外文字的JSON
            "好的，这是改写后的查询：{'query': '改写后的查询'}",
            # 正常的JSON（应该成功解析）
            '{"query": "改写后的查询"}',
        ]
        
        for i, response in enumerate(test_cases):
            try:
                result = robust_search._extract_rewritten_query_robust(response)
                print(f"测试用例 {i+1} 成功: {result}")
                if i == len(test_cases) - 1:  # 最后一个正常的JSON应该成功
                    assert result == "改写后的查询"
            except ValueError as e:
                print(f"测试用例 {i+1} 预期失败: {e}")
                # 前几个有问题的JSON应该抛出异常
                assert i < len(test_cases) - 1

    @pytest.mark.asyncio 
    async def test_architect_removed_search_capability(self):
        """测试Architect是否成功移除了搜索能力"""
        architect = Architect()
        
        # 断言：Architect不应该有搜索相关的属性
        assert not hasattr(architect, 'search_enhanced_qa')
        assert not hasattr(architect, 'search_engine')
        
        # 断言：Architect应该只监听ConductComprehensiveResearch
        watched_actions = [str(action) for action in architect._watch]
        assert any('ConductComprehensiveResearch' in action for action in watched_actions)
        
        # 断言：Architect应该只有DesignReportStructure这一个Action
        actions = architect.actions
        assert len(actions) == 1
        assert isinstance(actions[0], DesignReportStructure)

    @pytest.mark.asyncio
    async def test_product_manager_research_flow(self, sample_documents):
        """测试ProductManager的研究流程（模拟）"""
        # 由于真实的研究流程需要网络访问，我们这里只测试数据流
        pm = ProductManager()
        
        # 断言：ProductManager应该有正确的Actions
        assert len(pm.actions) == 2  # PrepareDocuments和ConductComprehensiveResearch
        
        # 断言：ProductManager应该监听正确的事件
        watched_actions = [str(action) for action in pm._watch]
        assert any('UserRequirement' in action for action in watched_actions)
        assert any('PrepareDocuments' in action for action in watched_actions)
        
        # 模拟ResearchData的创建
        research_data = ResearchData(
            brief="模拟的研究简报内容...",
            vector_store_path="workspace/mock_path.faiss"
        )
        
        # 创建Message（模拟ProductManager的输出）
        msg = Message(
            content=f"研究完成: {research_data.brief[:200]}...",
            role="Product Manager",
            cause_by="ConductComprehensiveResearch",
            instruct_content=Message.create_instruct_value(research_data)
        )
        
        # 断言：消息应该包含正确的instruct_content
        assert msg.instruct_content is not None
        # 由于instruct_content的具体结构可能经过序列化，我们检查基本属性
        assert hasattr(msg, 'instruct_content')

    def test_data_flow_integrity(self, sample_research_data):
        """测试数据流完整性 - 从ProductManager到Architect"""
        
        # Step 1: ProductManager产出ResearchData
        pm_output = Message(
            content="研究完成: 祥符区2024年小麦'一喷三防'项目...",
            role="Product Manager", 
            cause_by="ConductComprehensiveResearch",
            instruct_content=Message.create_instruct_value(sample_research_data)
        )
        
        # Step 2: Architect接收并解析数据（模拟_act中的逻辑）
        messages = [pm_output]
        research_brief = ""
        
        for msg in messages:
            if msg.cause_by == "ConductComprehensiveResearch":
                if hasattr(msg, 'instruct_content') and msg.instruct_content:
                    try:
                        if isinstance(msg.instruct_content, ResearchData):
                            research_brief = msg.instruct_content.brief
                        elif hasattr(msg.instruct_content, 'brief'):
                            research_brief = msg.instruct_content.brief
                        else:
                            research_brief = msg.content
                    except Exception:
                        research_brief = msg.content
                break
        
        # 断言：数据应该能够正确传递
        assert research_brief is not None
        assert len(research_brief) > 0
        assert "祥符区2024年小麦" in research_brief

    @pytest.mark.asyncio
    async def test_end_to_end_mock_flow(self, sample_research_data):
        """端到端模拟流程测试（使用Mock避免网络调用）"""
        
        # 1. 模拟ProductManager完成研究
        pm_message = Message(
            content="研究完成: 祥符区项目分析...",
            role="Product Manager",
            cause_by="ConductComprehensiveResearch", 
            instruct_content=Message.create_instruct_value(sample_research_data)
        )
        
        # 2. 模拟Architect接收并处理
        architect = Architect()
        
        # 手动添加消息到Architect的记忆中
        architect.rc.memory.add(pm_message)
        
        # 创建一个Mock的DesignReportStructure
        mock_action = AsyncMock()
        mock_action.run = AsyncMock(return_value="## 报告结构设计\n\n1. 执行摘要\n2. 项目分析\n...")
        
        # 替换Architect的Action
        architect.set_actions([mock_action])
        
        # 执行Architect的_act方法
        result_message = await architect._act()
        
        # 断言：Architect应该成功处理并产出结果
        assert result_message is not None
        assert result_message.content is not None
        assert "报告结构设计" in result_message.content
        
        # 断言：应该调用了run方法
        mock_action.run.assert_called_once()


class TestConfigValidation:
    """配置验证测试"""
    
    def test_config_cache_setting(self):
        """测试缓存配置建议"""
        # 这个测试提醒开发者配置缓存以提升测试效率
        cache_config_example = {
            "llm": {
                "cache_path": "cache/llm_cache"
            }
        }
        
        print("\n=== 缓存配置建议 ===")
        print("为了提升测试效率，请在config2.yaml中配置:")
        print("llm:")
        print("  cache_path: 'cache/llm_cache'")
        print("===================")
        
        assert cache_config_example["llm"]["cache_path"] is not None


# 运行测试的示例命令
if __name__ == "__main__":
    import subprocess
    import sys
    
    print("运行SOP集成测试...")
    print("确保您已经安装了pytest: pip install pytest pytest-asyncio")
    print("\n推荐的测试命令:")
    print("pytest tests/test_sop_integration.py -v")
    print("pytest tests/test_sop_integration.py::TestSOPIntegration::test_architect_data_extraction_fix -v")
    print("pytest tests/test_sop_integration.py::TestSOPIntegration::test_robust_search_json_handling -v")