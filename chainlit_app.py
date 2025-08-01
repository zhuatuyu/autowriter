import asyncio
import json
from pathlib import Path
from typing import Dict, List
import chainlit as cl
from datetime import datetime
import uuid

# 导入真正的后端服务
from backend.services.project_service import ProjectService
from backend.services.agent_service import AgentService
from backend.models.project import Project
from backend.services.environment import Environment
from metagpt.logs import logger

# 全局变量
project_service = ProjectService()
agent_service = AgentService()
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
                    label="📋 查看项目列表", 
                    message="/list_projects",
                    icon="/public/list.svg",
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

**简单三步开始工作：**

1. **创建项目** - 点击上方按钮或直接说出你的项目想法
2. **描述需求** - 告诉我你想要什么内容
3. **开始协作** - 多智能体团队自动开始工作

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
    
    # 检查是否在等待项目信息
    if cl.user_session.get("waiting_for_project_info"):
        await create_project_from_message(content)
        return
    
    # 获取当前会话的项目ID
    project_id = cl.user_session.get("current_project_id")
    
    if not project_id:
        # 直接从用户输入创建项目并开始工作
        await create_project_and_start_work(content)
        return
    
    # 在项目上下文中处理对话
    await handle_project_conversation(project_id, content)


async def handle_command(command: str):
    """处理命令"""
    if command == "/create_project":
        await show_create_project_form()
    elif command == "/list_projects":
        await show_project_list()
    elif command == "/help":
        await show_help()
    elif command.startswith("/select_project "):
        project_id = command.replace("/select_project ", "").strip()
        await select_project(project_id)
    elif command.startswith("/create_project "):
        # 支持直接创建项目的命令
        project_name = command.replace("/create_project ", "").strip()
        if project_name:
            await create_project_and_start_work(project_name)
        else:
            await show_create_project_form()
    else:
        await cl.Message(content="❌ 未知命令，使用 `/help` 查看可用命令").send()


async def create_project_and_start_work(content: str):
    """直接从用户输入创建项目并开始工作"""
    try:
        # 使用用户输入作为项目名称和描述
        project_name = content[:50] + "..." if len(content) > 50 else content
        project_desc = content
        
        # 创建项目对象
        project = Project(
            name=project_name,
            description=project_desc
        )
        
        # 创建项目
        created_project = await project_service.create_project(project)
        
        # 设置当前项目
        cl.user_session.set("current_project_id", created_project.id)
        
        await cl.Message(
            content=f"""
# ✅ 项目已创建，多智能体团队开始工作！

**项目**: {created_project.name}

🤖 **项目经理**: 正在分析需求和制定计划...
📊 **数据分析师**: 准备收集相关数据...
📝 **写作专家**: 准备开始内容创作...
🔍 **案例专家**: 搜索相关案例和资料...

---
*团队正在协作中，有问题会主动询问你的意见！*
            """
        ).send()
        
        # 立即开始处理项目对话
        await handle_project_conversation(created_project.id, content)
        
    except Exception as e:
        await cl.Message(
            content=f"❌ 启动失败: {str(e)}\n\n请重新尝试，或使用 `/create_project` 命令。"
        ).send()


async def show_create_project_form():
    """显示创建项目表单"""
    cl.user_session.set("waiting_for_project_info", True)
    
    await cl.Message(
        content="""
# 📝 创建新项目

请按以下格式提供项目信息：

```
项目名称: 你的项目名称
项目描述: 详细描述项目内容
```

**示例**:
```
项目名称: API文档编写
项目描述: 为新产品编写完整的API技术文档
```

---
*或者直接输入项目想法，我会自动创建项目！*
        """
    ).send()


async def create_project_from_message(content: str):
    """从消息内容创建项目"""
    try:
        # 解析项目信息
        lines = content.strip().split('\n')
        project_name = ""
        project_desc = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("项目名称:") or line.startswith("项目名称："):
                project_name = line.split(":", 1)[1].strip() if ":" in line else line.split("：", 1)[1].strip()
            elif line.startswith("项目描述:") or line.startswith("项目描述："):
                project_desc = line.split(":", 1)[1].strip() if ":" in line else line.split("：", 1)[1].strip()
        
        # 如果没有找到格式化的信息，将整个内容作为项目名称
        if not project_name:
            project_name = content[:50] + "..." if len(content) > 50 else content
            project_desc = content
        
        # 创建项目对象
        project = Project(
            id=str(uuid.uuid4()),
            name=project_name,
            description=project_desc,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 创建项目
        created_project = await project_service.create_project(project)
        
        # 设置当前项目
        cl.user_session.set("current_project_id", created_project.id)
        cl.user_session.set("waiting_for_project_info", False)
        
        await cl.Message(
            content=f"""
# ✅ 项目创建成功，多智能体开始工作！

**项目**: {created_project.name}

🤖 **多智能体团队已启动**
- 项目经理正在制定计划
- 数据分析师开始收集资料
- 写作专家准备内容框架
- 案例专家搜索相关案例

---
*现在开始处理你的需求...*
            """
        ).send()
        
        # 立即开始处理项目对话
        await handle_project_conversation(created_project.id, content)
        
    except Exception as e:
        cl.user_session.set("waiting_for_project_info", False)
        await cl.Message(
            content=f"❌ 创建项目失败: {str(e)}\n\n请重新尝试。"
        ).send()


async def show_project_list():
    """显示项目列表"""
    try:
        projects = await project_service.get_all_projects()
        
        if not projects:
            await cl.Message(
                content="📋 **项目列表为空**\n\n直接告诉我你想创建什么项目即可开始！"
            ).send()
            return
        
        content = "# 📋 项目列表\n\n"
        for project in projects:
            content += f"🟢 **{project.name}**\n"
            content += f"   - 描述: {project.description}\n"
            content += f"   - 选择: `/select_project {project.id}`\n\n"
        
        await cl.Message(content=content).send()
        
    except Exception as e:
        await cl.Message(content=f"❌ 获取项目列表失败: {str(e)}").send()


async def select_project(project_id: str):
    """选择项目"""
    try:
        project = await project_service.get_project(project_id)
        if not project:
            await cl.Message(content="❌ 项目不存在").send()
            return
        
        cl.user_session.set("current_project_id", project_id)
        
        await cl.Message(
            content=f"""
# ✅ 已选择项目: {project.name}

现在你可以开始与多智能体团队对话！

---
*直接说出你的需求，团队会立即开始工作*
            """
        ).send()
        
    except Exception as e:
        await cl.Message(content=f"❌ 选择项目失败: {str(e)}").send()


async def handle_project_conversation(project_id: str, message: str):
    """在项目上下文中处理对话"""
    try:
        # 使用真正的agent服务处理消息
        response = await agent_service.process_message(project_id, message, environment)
        
        await cl.Message(content=response).send()
        
    except Exception as e:
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
- `/list_projects` - 查看所有项目
- `/select_project <id>` - 选择项目
- `/help` - 显示帮助

---
*最简单的方式：直接告诉我你想要什么！*
        """
    ).send()


if __name__ == "__main__":
    import chainlit as cl
    cl.run()