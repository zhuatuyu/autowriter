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

## Backend Structure (`backend/`) - 虚拟办公环境架构

```
backend/
├── main.py                    # FastAPI application entry point
├── models/                    # Data models and schemas
│   └── session.py            # Session, Agent, and workflow models
├── services/                  # 核心基础设施层 (稳定层)
│   ├── core_manager.py        # 核心管理器 - Agent团队协调
│   ├── llm_provider.py        # LLM提供者 - 统一AI接口
│   ├── websocket_manager.py   # WebSocket管理器 - 实时通信
│   └── llm/                   # Agent层 (扩展层)
│       └── agents/            # 虚拟办公室员工
│           ├── base.py        # 基础Agent类
│           ├── director.py    # 🎯 智能项目总监
│           ├── document_expert.py  # 📄 文档专家 (李心悦)
│           ├── case_expert.py      # 🔍 案例专家 (王磊)
│           ├── data_analyst.py     # 📊 数据分析师 (赵丽娅)
│           ├── writer_expert.py    # ✍️ 写作专家 (张翰)
│           └── chief_editor.py     # 👔 总编辑 (钱敏)
└── tools/                     # 工具层 (功能层)
    ├── alibaba_search.py      # 阿里巴巴搜索工具
    └── mineru_api_tool.py     # MinerU文档处理API
```

## Frontend Structure (`frontend/src/`)

```
frontend/src/
├── App.tsx              # Main application component
├── main.tsx            # Application entry point
├── index.css           # Global styles
├── components/         # Reusable UI components
│   ├── Layout/         # Layout components (Sidebar, ChatArea, etc.)
│   └── Chat/           # Chat-related components
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
├── chief_editor/             # 👔 钱敏的工作区 (总编辑)
│   └── reviews/             # 审核记录
└── final_report.md           # 最终报告
```

## Naming Conventions

### Python Files
- **Services**: `*_manager.py` for orchestration services
- **Models**: Descriptive names like `session.py`
- **Tools**: `*_tool.py` or descriptive names for external integrations

### TypeScript Files
- **Components**: PascalCase (e.g., `HomePage.tsx`)
- **Hooks**: camelCase with `use` prefix (e.g., `useWebSocket.ts`)
- **Stores**: camelCase with descriptive suffix (e.g., `reportStore.ts`)

### API Endpoints
- **REST**: `/api/{resource}` pattern
- **WebSocket**: `/ws/{session_id}` pattern

## Import Patterns

### Backend
```python
# Relative imports within backend
from backend.models.session import WorkSession
from backend.services.intelligent_manager import intelligent_manager

# MetaGPT imports
from metagpt.roles import Role
from metagpt.schema import Message
```

### Frontend
```typescript
// Absolute imports with @ alias
import { useReportStore } from '@/stores/reportStore';
import Layout from '@/components/Layout/Layout';
```

## Testing Structure

- **Architecture tests**: `test_*_architecture.py` - Test different workflow modes
- **Workflow tests**: `test_*_workflow.py` - Test specific functionality
- **Integration tests**: Test end-to-end scenarios with MetaGPT