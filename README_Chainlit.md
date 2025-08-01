# AutoWriter Chainlit版本

基于Chainlit框架的简化版AutoWriter，提供直观的Web界面和流畅的对话体验。

## 🌟 特性

- **🎯 简洁界面**: 类似ChatGPT的对话界面，易于使用
- **📁 项目管理**: 支持多项目创建、切换和管理
- **💬 智能对话**: 与MetaGPT智能体进行自然语言交互
- **📝 实时输出**: 支持流式输出，实时查看AI思考过程
- **🎨 现代UI**: 深色主题，美观的用户界面

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r chainlit_requirements.txt
```

### 2. 启动应用

```bash
python start_chainlit.py
```

或者直接使用chainlit命令：

```bash
chainlit run chainlit_app.py
```

### 3. 访问应用

打开浏览器访问: http://localhost:8000

## 📋 功能说明

### 项目管理
- **创建项目**: 点击"创建新项目"或使用 `/create_project` 命令
- **查看项目**: 使用 `/list_projects` 查看所有项目
- **选择项目**: 使用 `/select_project <project_id>` 切换项目

### 对话功能
- **智能对话**: 在项目上下文中与AI助手对话
- **命令支持**: 支持斜杠命令快速操作
- **流式输出**: 实时查看AI生成过程

### 支持的命令
- `/create_project` - 创建新项目
- `/list_projects` - 查看项目列表
- `/select_project <id>` - 选择项目
- `/help` - 显示帮助信息

## 🎯 使用流程

1. **启动应用** → 访问Web界面
2. **创建项目** → 提供项目信息
3. **开始对话** → 在项目上下文中交互
4. **管理项目** → 随时切换或创建新项目

## 🔧 配置说明

### Chainlit配置
配置文件: `chainlit_config.toml`
- 主题设置: 默认深色主题
- 会话超时: 3600秒
- 功能开关: 可自定义各种UI功能

### 项目配置
- 项目数据存储在 `workspaces/` 目录
- 支持多种项目类型: 技术文档、商业报告、学术论文等
- 自动保存对话历史和项目状态

## 🆚 与原版对比

| 特性 | 原版 (WebSocket) | Chainlit版本 |
|------|------------------|--------------|
| 界面复杂度 | 复杂 | 简洁 |
| 开发维护 | 需要前后端分离 | 单一应用 |
| 用户体验 | 需要自定义UI | 开箱即用 |
| 实时输出 | WebSocket | 原生支持 |
| 部署难度 | 较高 | 简单 |

## 🎨 界面预览

- **项目工作台**: 卡片式项目展示
- **创建项目**: 表单式项目创建
- **对话界面**: ChatGPT风格的对话体验

## 🔍 技术架构

```
chainlit_app.py          # 主应用文件
├── ChainlitProjectEnv   # 项目环境管理
├── 聊天配置             # 启动器和配置文件
├── 命令处理             # 斜杠命令处理
├── 项目管理             # 项目CRUD操作
└── 对话处理             # AI对话逻辑
```

## 📝 开发说明

### 扩展功能
- 修改 `chainlit_app.py` 添加新功能
- 在 `@cl.on_message` 中处理新的消息类型
- 使用 `cl.Message().send()` 发送响应

### 自定义UI
- 修改 `chainlit_config.toml` 调整主题
- 添加自定义CSS/JS文件
- 配置启动器和聊天配置文件

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📄 许可证

MIT License