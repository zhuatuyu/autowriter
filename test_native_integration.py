#!/usr/bin/env python
"""
测试MetaGPT原生集成
验证重构后的代码是否正常工作
"""
import asyncio
import uuid
from pathlib import Path

from metagpt.environment import Environment
from backend.services.company import Company


async def test_native_integration():
    """测试原生集成"""
    print("🚀 开始测试MetaGPT原生集成...")
    
    # 创建环境
    environment = Environment()
    
    # 创建公司服务
    company = Company()
    
    # 生成项目ID
    project_id = str(uuid.uuid4())
    
    # 测试消息
    test_message = """
    写一份祥符区2024年小麦"一喷三防"项目财政重点绩效评价报告。
    
    受开封市祥符区财政局委托，河南昭元绩效评价咨询有限公司于2025年4—5月对祥符区2024年小麦"一喷三防"项目进行财政重点绩效评价。
    
    根据委托方的要求，我公司通过制定绩效评价方案、资料数据核查、现场调查与访谈、指标分析与评价、撰写绩效评价报告等程序，完成编制《祥符区2024年小麦"一喷三防"项目财政重点绩效评价报告》。
    
    报告中的数据、资料来自开封市祥符区财政部门、项目单位提供的项目资料和其他来源可靠的信息渠道。
    
    本报告遵循河南省财政厅、开封市祥符区财政局有关预算绩效管理的规范要求编制，以纸质印刷版和电子版向开封市祥符区财政局报送，未经开封市祥符区财政局书面允许，不得随意翻印、发布。
    
    可以检索网络案例来辅助参考撰写。
    """
    
    try:
        print(f"📋 项目ID: {project_id}")
        print(f"📝 测试消息: {test_message[:100]}...")
        
        # 处理消息
        result = await company.process_message(project_id, test_message, environment)
        
        print(f"✅ 处理结果: {result}")
        
        # 检查工作空间
        workspace_path = Path(f"workspaces/{project_id}")
        if workspace_path.exists():
            print(f"📁 工作空间已创建: {workspace_path}")
            
            # 列出工作空间内容
            for item in workspace_path.rglob("*"):
                if item.is_file():
                    print(f"   📄 {item.relative_to(workspace_path)}")
        else:
            print("❌ 工作空间未创建")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_native_integration()) 