import asyncio
import json
from pathlib import Path
from typing import Dict, List
import chainlit as cl
from datetime import datetime
import uuid

# 导入真正的后端服务
from backend.services.company import Company
from metagpt.environment import Environment
from metagpt.logs import logger
from metagpt.config2 import config # 使用新的配置对象

# 全局变量
company = Company()
environment = Environment()


@cl.set_chat_profiles
async def chat_profile() -> List[cl.ChatProfile]:
    """设置聊天配置文件"""
    return [
        cl.ChatProfile(
            name="AutoWriter",
            icon="/public/logo.png",
            markdown_description="**AutoWriter** - 智能写作助手",
            starters=[
                cl.Starter(
                    label="📝 创建新项目",
                    message="/create_project",
                    icon="/public/idea.svg",
                ),
                cl.Starter(
                    label="💡 直接开始",
                    message="我想创建一个技术文档项目",
                    icon="/public/chat.svg",
                ),
            ],
        )
    ]


@cl.on_chat_start
async def start():
    """应用启动时的初始化"""
    await cl.Message(
        content="""
# 🎯 欢迎使用 AutoWriter！

**简单两步开始工作：**

1. **创建项目** - 点击上方按钮或直接说出你的项目想法
2. **开始协作** - 多智能体团队将自动开始工作

---

**示例：** 直接说 "我要写一份关于AI的研究报告" 即可开始！
        """
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """处理用户消息"""
    content = message.content.strip()
    
    # 处理命令
    if content.startswith("/"):
        await handle_command(content)
        return
    
    # 获取或创建项目ID
    project_id = cl.user_session.get("current_project_id")
    
    if not project_id:
        project_id = str(uuid.uuid4())
        cl.user_session.set("current_project_id", project_id)
    
    # 在项目上下文中处理对话
    await handle_project_conversation(project_id, content)


async def handle_command(command: str):
    """处理命令"""
    if command == "/create_project":
        project_id = str(uuid.uuid4())
        cl.user_session.set("current_project_id", project_id)
        await cl.Message(content=f"✅ 新项目已创建 (ID: {project_id})，请直接输入您的需求。").send()
    elif command == "/help":
        await show_help()
    else:
        await cl.Message(content="❌ 未知命令，使用 `/help` 查看可用命令").send()


async def handle_project_conversation(project_id: str, message: str):
    """在项目上下文中处理对话"""
    try:
        # 使用公司服务处理消息
        response = await company.process_message(project_id, message, environment)
        
        await cl.Message(content=response).send()
        
    except Exception as e:
        logger.error(f"处理消息失败: {e}")
        await cl.Message(content=f"❌ 处理消息失败: {str(e)}").send()


async def show_help():
    """显示帮助信息"""
    await cl.Message(
        content="""
# 📚 使用帮助

## 🚀 快速开始
直接说出你的项目想法，比如：
- "我要写一份技术文档"
- "帮我写个商业计划书"
- "创建一个研究报告"

## 📋 可用命令
- `/create_project` - 创建新项目
- `/help` - 显示帮助

---
*最简单的方式：直接告诉我你想要什么！*
        """
    ).send()


if __name__ == "__main__":
    cl.run()