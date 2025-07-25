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
pydantic==2.5.0
```

### Frontend
```
react@^18.2.0
typescript@^5.0.0
@tanstack/react-query@^5.0.0
zustand@^4.4.0
tailwindcss@^3.3.0
lucide-react@^0.294.0
```

## 核心技术架构

### 1. MetaGPT框架集成
- **Role-Action架构**: 完全遵循MetaGPT的Role-Action-Tool-Skill设计模式
- **标准继承**: 所有Agent继承自MetaGPT的Role基类
- **Action机制**: 使用MetaGPT的Action实现原子化操作
- **React模式**: 采用MetaGPT的React模式实现智能决策

### 2. Orchestrator模式
- **状态机管理**: 使用SessionState枚举管理会话状态
- **状态分发器**: 基于当前状态智能分发用户消息
- **原子操作**: 将复杂逻辑拆分为可复用的原子操作
- **错误恢复**: 完整的错误处理和状态恢复机制

### 3. 虚拟办公环境
- **职责分离**: Director只负责规划，Orchestrator只负责协调，Expert只负责执行
- **工作空间**: 每个Agent都有独立的工作空间和文件系统
- **实时协作**: WebSocket实现真正的实时多Agent协作
- **状态可视化**: 前端实时显示各Agent的工作状态

## Development Commands

### Backend
```bash
# Install MetaGPT from source
pip install -e ./MetaGPT

# Install dependencies
pip install -r requirements.txt

# Start development server
python start_backend.py
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

## 架构优势

### 1. MetaGPT对齐优势
- **标准化设计**: 完全遵循MetaGPT的Role-Action-Tool-Skill架构
- **可扩展性强**: 基于MetaGPT框架，易于添加新的Agent和功能
- **代码复用**: 利用MetaGPT的成熟组件，避免重复造轮子
- **最佳实践**: 采用MetaGPT推荐的设计模式和开发规范

### 2. Orchestrator模式优势
- **职责单一**: 每个组件都有明确的职责边界
- **状态明确**: 通过状态机管理，系统行为可预测
- **高度灵活**: 交互流程完全解耦，可轻松修改
- **易于维护**: 清晰的架构层次，便于调试和扩展

### 3. 技术栈优势
- **高性能**: FastAPI提供异步高性能Web服务
- **实时通信**: WebSocket实现真正的实时交互
- **现代化前端**: React 18 + TypeScript提供优秀的开发体验
- **响应式设计**: Tailwind CSS实现完美的响应式布局

## Testing
```bash
# Run architecture tests
python test_sop_architecture.py
python test_iterative_architecture.py
python test_template_workflow.py

# Test MetaGPT integration
python -c "from backend.services.orchestrator import core_manager; print('✅ Orchestrator导入成功')"

# Test Role implementations
python -c "from backend.roles.director import DirectorAgent; print('✅ Director导入成功')"
```

## 部署架构

### 开发环境
- **后端**: FastAPI + Uvicorn (热重载)
- **前端**: Vite开发服务器 (热重载)
- **数据库**: SQLite (本地开发)
- **WebSocket**: 原生WebSocket连接

### 生产环境
- **后端**: FastAPI + Gunicorn + Uvicorn
- **前端**: Nginx静态文件服务
- **数据库**: PostgreSQL (生产环境)
- **WebSocket**: 通过Nginx代理

## 性能优化

### 1. 后端优化
- **异步处理**: 所有I/O操作使用async/await
- **连接池**: 数据库连接池优化
- **缓存策略**: Redis缓存热点数据
- **负载均衡**: 多实例部署

### 2. 前端优化
- **代码分割**: 按路由分割代码
- **懒加载**: 组件和资源懒加载
- **缓存策略**: 浏览器缓存优化
- **CDN**: 静态资源CDN加速

## 安全考虑

### 1. 后端安全
- **输入验证**: Pydantic模型验证所有输入
- **认证授权**: JWT token认证
- **CORS**: 跨域资源共享配置
- **SQL注入防护**: 使用ORM防止SQL注入

### 2. 前端安全
- **XSS防护**: React自动转义防止XSS
- **CSRF防护**: CSRF token验证
- **内容安全策略**: CSP头部配置
- **HTTPS**: 生产环境强制HTTPS

## 监控和日志

### 1. 应用监控
- **性能监控**: 响应时间、吞吐量监控
- **错误监控**: 异常捕获和报告
- **资源监控**: CPU、内存、磁盘使用率
- **业务监控**: 关键业务指标监控

### 2. 日志管理
- **结构化日志**: JSON格式日志输出
- **日志级别**: DEBUG、INFO、WARNING、ERROR分级
- **日志聚合**: 集中式日志收集和分析
- **日志轮转**: 自动日志文件轮转

## 扩展性设计

### 1. 水平扩展
- **无状态设计**: 后端服务无状态，支持水平扩展
- **负载均衡**: 多实例部署，负载均衡
- **数据库分片**: 数据库水平分片
- **缓存集群**: Redis集群部署

### 2. 垂直扩展
- **模块化设计**: 功能模块化，支持独立扩展
- **微服务架构**: 可拆分为微服务
- **API网关**: 统一API网关管理
- **服务发现**: 服务注册和发现机制