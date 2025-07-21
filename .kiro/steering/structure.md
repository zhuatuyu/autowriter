# Project Structure

## Root Directory Layout

```
autowriter/
├── backend/                 # FastAPI backend application
├── frontend/               # React TypeScript frontend
├── MetaGPT/               # MetaGPT framework (git submodule)
├── local-db/              # Local database and documents
├── workspaces/            # Generated project workspaces
├── logs/                  # Application logs
├── venv/                  # Python virtual environment
├── requirements.txt       # Python dependencies
├── reportmodel.yaml       # Report template configuration
└── test_*.py             # Architecture and workflow tests
```

## Backend Structure (`backend/`)

```
backend/
├── main.py               # FastAPI application entry point
├── models/               # Data models and schemas
│   └── session.py       # Session, Agent, and workflow models
├── services/            # Business logic and agent services
│   ├── intelligent_manager.py      # Main workflow orchestrator
│   ├── metagpt_manager.py          # MetaGPT integration layer
│   ├── metagpt_sop_manager.py      # SOP workflow implementation
│   ├── iterative_sop_manager.py    # Iterative workflow mode
│   ├── intelligent_director.py     # Intelligent director agent
│   └── websocket_manager.py        # WebSocket connection management
└── tools/               # External tools and integrations
    ├── alibaba_search.py           # Search functionality
    └── report_template_analyzer.py # Template parsing and analysis
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

## Workspace Organization (`workspaces/`)

Each project gets its own workspace directory:
```
workspaces/
├── project_001/
│   ├── dynamic_template.yaml    # Project-specific template
│   ├── draft/                   # Generated drafts
│   └── files/                   # Project documents
└── demo-1/
    ├── report.md               # Final report output
    └── writing_progress.json   # Progress tracking
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