#!/usr/bin/env python3
"""
测试修复后的 Agent 工作状态
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from metagpt.config2 import Config
from metagpt.context import Context
from metagpt.schema import Message

# 导入各个 Agent
from backend.roles.director import DirectorAgent
from backend.roles.case_expert import CaseExpertAgent
from backend.roles.writer_expert import WriterExpertAgent
from backend.roles.data_analyst import DataAnalystAgent
from backend.utils.project_repo import ProjectRepo

async def test_director_agent():
    """测试 DirectorAgent"""
    print("🧪 测试 DirectorAgent...")
    try:
        # 配置 MetaGPT
        config = Config.default()
        config.llm.model = "qwen-max-latest"
        
        # 创建 Agent
        director = DirectorAgent(config=config)
        
        # 测试创建计划
        user_request = "帮我分析一下国内养老院建设项目的绩效评估案例"
        plan = await director.process_request(user_request)
        
        if plan:
            print(f"✅ DirectorAgent 测试成功，生成了 {len(plan.tasks)} 个任务")
            for i, task in enumerate(plan.tasks, 1):
                print(f"   {i}. {task.agent}: {task.description}")
        else:
            print("❌ DirectorAgent 测试失败：未生成计划")
            
    except Exception as e:
        print(f"❌ DirectorAgent 测试失败：{e}")

async def test_case_expert_agent():
    """测试 CaseExpertAgent"""
    print("\n🧪 测试 CaseExpertAgent...")
    try:
        # 配置 MetaGPT
        config = Config.default()
        config.llm.model = "qwen-max-latest"
        
        # 创建 ProjectRepo
        project_repo = ProjectRepo(session_id="test_session")
        
        # 创建上下文
        context = Context(config=config, project_repo=project_repo)
        
        # 创建 Agent
        case_expert = CaseExpertAgent(config=config, context=context)
        
        # 创建测试消息
        test_message = Message(
            content="搜索国内养老院建设项目的绩效评估案例",
            role="user"
        )
        
        # 添加消息到内存并初始化状态
        case_expert.rc.memory.add(test_message)
        case_expert.rc.todo = case_expert.actions[0]  # 设置第一个 Action
        
        # 执行第一个 Action
        result = await case_expert._act()
        
        if result:
            print(f"✅ CaseExpertAgent 测试成功，返回消息类型：{type(result)}")
            print(f"   消息内容长度：{len(result.content) if result.content else 0}")
        else:
            print("❌ CaseExpertAgent 测试失败：未返回结果")
            
    except Exception as e:
        print(f"❌ CaseExpertAgent 测试失败：{e}")

async def test_writer_expert_agent():
    """测试 WriterExpertAgent"""
    print("\n🧪 测试 WriterExpertAgent...")
    try:
        # 配置 MetaGPT
        config = Config.default()
        config.llm.model = "qwen-max-latest"
        
        # 创建 ProjectRepo
        project_repo = ProjectRepo(session_id="test_session")
        
        # 创建上下文
        context = Context(config=config, project_repo=project_repo)
        
        # 创建 Agent
        writer_expert = WriterExpertAgent(config=config, context=context)
        
        # 创建测试消息
        test_message = Message(
            content="根据案例研究结果撰写养老院建设项目绩效评估报告",
            role="user"
        )
        
        # 添加消息到内存并初始化状态
        writer_expert.rc.memory.add(test_message)
        writer_expert.rc.todo = writer_expert.actions[0]  # 设置第一个 Action
        
        # 执行第一个 Action
        result = await writer_expert._act()
        
        if result:
            print(f"✅ WriterExpertAgent 测试成功，返回消息类型：{type(result)}")
            print(f"   消息内容长度：{len(result.content) if result.content else 0}")
        else:
            print("❌ WriterExpertAgent 测试失败：未返回结果")
            
    except Exception as e:
        print(f"❌ WriterExpertAgent 测试失败：{e}")

async def test_data_analyst_agent():
    """测试 DataAnalystAgent"""
    print("\n🧪 测试 DataAnalystAgent...")
    try:
        # 创建 ProjectRepo
        project_repo = ProjectRepo(session_id="test_session")
        
        # 创建上下文
        context = Context(project_repo=project_repo)
        
        # 创建 Agent（不传递 config，让它使用内部的 qwen_long_config）
        data_analyst = DataAnalystAgent(context=context)
        
        # 创建测试消息
        test_message = Message(
            content="分析养老院建设项目的绩效数据",
            role="user"
        )
        
        # 添加消息到内存并初始化状态
        data_analyst.rc.memory.add(test_message)
        data_analyst.rc.todo = data_analyst.actions[0]  # 设置第一个 Action
        
        # 执行第一个 Action
        result = await data_analyst._act()
        
        if result:
            print(f"✅ DataAnalystAgent 测试成功，返回消息类型：{type(result)}")
            print(f"   消息内容长度：{len(result.content) if result.content else 0}")
        else:
            print("❌ DataAnalystAgent 测试失败：未返回结果")
            
    except Exception as e:
        print(f"❌ DataAnalystAgent 测试失败：{e}")

async def main():
    """主测试函数"""
    print("🚀 开始测试各个 Agent...")
    
    # 设置配置文件路径
    config_path = project_root / "config" / "config2.yaml"
    if config_path.exists():
        os.environ["METAGPT_CONFIG_PATH"] = str(config_path)
        print(f"📁 使用配置文件：{config_path}")
    else:
        print("⚠️  配置文件不存在，使用默认配置")
    
    # 依次测试各个 Agent
    await test_director_agent()
    await test_case_expert_agent()
    await test_writer_expert_agent()
    await test_data_analyst_agent()
    
    print("\n🎉 测试完成！")

if __name__ == "__main__":
    asyncio.run(main())