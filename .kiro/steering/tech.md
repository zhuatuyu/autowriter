# Technology Stack

## Backend
- **Framework**: FastAPI with async/await support
- **WebSocket**: Real-time communication via WebSocket connections
- **AI Framework**: MetaGPT for multi-agent orchestration
- **Database**: SQLAlchemy ORM (SQLite for local development)
- **Python Version**: Python 3.8+

## Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Styling**: Tailwind CSS
- **WebSocket Client**: Native WebSocket API
- **Routing**: React Router DOM

## Key Dependencies

### Backend
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==11.0.3
sqlalchemy==2.0.23
metagpt (installed from source)
```

### Frontend
```
react@^18.2.0
typescript@^5.0.0
@tanstack/react-query@^5.0.0
zustand@^4.4.0
tailwindcss@^3.3.0
```

## Development Commands

### Backend
```bash
# Install MetaGPT from source
pip install -e ./MetaGPT

# Install dependencies
pip install -r requirements.txt

# Start development server
python backend/main.py
# or
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check
```

## Configuration

### MetaGPT Configuration
- Configuration file: `MetaGPT/config/config2.yaml`
- Required for LLM API settings and agent behavior
- Must be properly configured before running the system

### Environment Setup
- Backend runs on port 8000
- Frontend development server on port 3000
- WebSocket endpoint: `/ws/{session_id}`
- API endpoints: `/api/*`

## Testing
```bash
# Run architecture tests
python test_sop_architecture.py
python test_iterative_architecture.py
python test_template_workflow.py
```