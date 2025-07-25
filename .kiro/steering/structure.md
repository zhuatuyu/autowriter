# Project Structure

## Root Directory Layout

```
autowriter/
├── backend/                 # FastAPI backend application
├── frontend/               # React TypeScript frontend
├── MetaGPT/               # MetaGPT framework (git submodule)
├── workspaces/            # Generated project workspaces (Agent工作区)
├── venv/                  # Python virtual environment
├── requirements.txt       # Python dependencies
├── reportmodel.yaml       # Report template configuration (legacy)
└── test_*.py             # Architecture and workflow tests
```

## Backend Structure (`backend/`) - MetaGPT对齐的虚拟办公环境架构

```
backend/
├── main.py                    # FastAPI application entry point
├── models/                    # 数据模型层
│   ├── session.py            # 会话状态枚举和模型定义
│   └── plan.py               # 计划数据模型 (Plan, Task)
├── services/                  # 核心服务层 (稳定层)
│   ├── orchestrator.py        # 🎯 Orchestrator核心协调器 (原core_manager.py)
│   ├── websocket_manager.py   # WebSocket管理器 - 实时通信
│   └── llm_provider.py       # LLM提供者 - 统一AI接口
├── roles/                     # MetaGPT标准Role层 (扩展层)
│   ├── base.py               # 基础Agent类 (继承MetaGPT Role)
│   ├── director.py           # 🎯 智能项目总监 (DirectorAgent)
│   ├── document_expert.py    # 📄 文档专家 (DocumentExpertAgent)
│   ├── case_expert.py        # 🔍 案例专家 (CaseExpertAgent)
│   ├── data_analyst.py       # 📊 数据分析师 (DataAnalystAgent)
│   └── writer_expert.py      # ✍️ 写作专家 (WriterExpertAgent)
├── actions/                   # MetaGPT标准Action层 (功能层)
│   ├── write_content_action.py    # 写作Action
│   ├── summarize_action.py        # 摘要Action
│   ├── polish_action.py           # 润色Action
│   └── __init__.py               # Action导出
├── memory/                    # 应用特定记忆系统
│   ├── unified_memory_adapter.py
│   └── unified_memory_storage.py
├── prompts/                   # 提示词模板层
│   ├── director_prompts.py
│   ├── writer_expert_prompts.py
│   ├── document_expert_prompts.py
│   ├── data_analyst_prompts.py
│   └── core_manager_prompts.py
├── configs/                   # 配置层
│   └── llm_provider.py       # LLM统一配置
├── utils/                     # 工具函数层
└── tools/                     # 外部工具集成层
    ├── alibaba_search.py      # 阿里巴巴搜索工具
    ├── mineru_api_tool.py     # MinerU文档处理API
    ├── summary_tool.py        # 摘要工具
    └── writing_tools.py       # 写作工具
```

## Frontend Structure (`frontend/src/`) - 现代化前端架构

```
frontend/src/
├── App.tsx              # Main application component
├── main.tsx            # Application entry point
├── index.css           # Global styles
├── components/         # Reusable UI components
│   ├── Layout/         # Layout components
│   │   ├── ChatArea.tsx      # 聊天区域 (已修复输入框聚焦问题)
│   │   └── ...
│   └── Chat/           # Chat-related components
│       └── AgentMessage.tsx  # Agent消息组件
├── pages/              # Page components
│   └── HomePage.tsx    # Main application page
├── stores/             # Zustand state management
│   └── reportStore.ts  # Report and session state
└── hooks/              # Custom React hooks
    └── useWebSocket.ts # WebSocket connection hook
```

## Key Configuration Files

- **`reportmodel.yaml`**: Defines report template structure, chapters, and indicators
- **`MetaGPT/config/config2.yaml`**: MetaGPT framework configuration
- **`frontend/vite.config.ts`**: Frontend build configuration with proxy settings
- **`frontend/tailwind.config.js`**: Tailwind CSS configuration

## Workspace Organization (`workspaces/`) - 虚拟办公室工作区

每个项目都有自己的虚拟办公室，每个Agent都有独立的工作区：
```
workspaces/{session_id}/
├── director/                  # 🎯 项目总监工作区
│   └── plans/               # 生成的计划文件
├── document_expert/           # 📄 李心悦的工作区 (文档专家)
│   ├── uploads/              # 客户上传的原始文件
│   ├── processed/            # MinerU处理后的Markdown文件
│   ├── summaries/            # 文档摘要
│   └── index.json           # 文档索引
├── case_expert/              # 🔍 王磊的工作区 (案例专家)
│   ├── searches/            # 搜索结果
│   └── cases/               # 整理的案例
├── data_analyst/             # 📊 赵丽娅的工作区 (数据分析师)
│   ├── data/                # 提取的数据
│   └── charts/              # 生成的图表
├── writer_expert/            # ✍️ 张翰的工作区 (写作专家)
│   └── drafts/              # 写作草稿
└── final_report.md           # 最终报告
```

## 架构层次说明

### 1. 核心基础设施层 (稳定层)
- **orchestrator.py**: Orchestrator核心协调器，状态机管理
- **websocket_manager.py**: WebSocket通信管理
- **llm_provider.py**: LLM统一接口

### 2. MetaGPT标准层 (扩展层)
- **roles/**: 所有Agent继承自MetaGPT的Role基类
- **actions/**: 使用MetaGPT的Action机制实现原子化操作
- **memory/**: 应用特定的记忆系统

### 3. 业务逻辑层 (功能层)
- **prompts/**: 提示词模板
- **configs/**: 配置文件
- **tools/**: 外部工具集成

## Naming Conventions

### Python Files
- **Services**: `*_manager.py` for orchestration services
- **Roles**: `*_agent.py` for MetaGPT Role implementations
- **Actions**: `*_action.py` for MetaGPT Action implementations
- **Models**: Descriptive names like `session.py`, `plan.py`
- **Tools**: `*_tool.py` for external integrations

### TypeScript Files
- **Components**: PascalCase (e.g., `ChatArea.tsx`)
- **Hooks**: camelCase with `use` prefix (e.g., `useWebSocket.ts`)
- **Stores**: camelCase with descriptive suffix (e.g., `reportStore.ts`)

### API Endpoints
- **REST**: `/api/{resource}` pattern
- **WebSocket**: `/ws/{session_id}` pattern

## Import Patterns

### Backend
```python
# MetaGPT imports
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.actions import Action

# Internal imports
from backend.models.session import SessionState
from backend.services.orchestrator import core_manager
from backend.roles.director import DirectorAgent
from backend.actions.write_content_action import WriteContentAction
```

### Frontend
```typescript
// Absolute imports with @ alias
import { useReportStore } from '@/stores/reportStore';
import Layout from '@/components/Layout/Layout';
import { useWebSocket } from '@/hooks/useWebSocket';
```

## 重构后的关键变化

### 1. 文件重命名
- `core_manager.py` → `orchestrator.py` (更精确的命名)
- 所有Agent文件移至 `roles/` 目录

### 2. 新增目录
- `actions/`: MetaGPT标准Action层
- `configs/`: 配置层
- `utils/`: 工具函数层

### 3. 架构优化
- **Orchestrator模式**: 状态机驱动的协调器
- **MetaGPT对齐**: 完全遵循MetaGPT的Role-Action架构
- **职责分离**: Director只负责规划，Orchestrator只负责协调

## Testing Structure

- **Architecture tests**: `test_*_architecture.py` - Test different workflow modes
- **Workflow tests**: `test_*_workflow.py` - Test specific functionality
- **Integration tests**: Test end-to-end scenarios with MetaGPT
- **Orchestrator tests**: Test state machine and coordination logic