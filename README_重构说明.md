# MetaGPT原生架构重构说明

## 重构目标

将项目完全迁移到MetaGPT原生架构，解决序列化问题和路径管理问题，确保系统稳定运行。

## 主要变更

### 1. 移除自定义模型
- 删除了 `backend/models/plan.py`
- 删除了 `backend/models/project.py` 
- 删除了 `backend/models/session.py`
- 使用MetaGPT原生的序列化机制

### 2. 阿里云搜索引擎原生集成
- **新增**: `example/MetaGPT_bak/metagpt/tools/search_engine_alibaba.py` - 原生风格的阿里云搜索引擎
- **修改**: `example/MetaGPT_bak/metagpt/configs/search_config.py` - 添加 `ALIBABA` 类型并设为默认
- **修改**: `example/MetaGPT_bak/metagpt/tools/search_engine.py` - 添加阿里云分支并设为默认引擎
- **删除**: `backend/tools/search_engine_alibaba.py` - 移除自定义实现
- **更新**: `config/config2.yaml` - 配置阿里云搜索引擎参数

### 3. 重构智能体角色
- **ProjectManagerAgent**: 完全使用MetaGPT原生的 `RoleZero` 架构
- **ArchitectAgent**: 新增架构师角色，使用原生的 `WriteDesign` Action
- **CaseExpertAgent**: 保持原有功能，使用原生 `SearchEngine`
- **DataAnalystAgent**: 简化实现，使用原生架构
- **WriterExpertAgent**: 简化实现，使用原生架构

### 4. 更新Actions
- 所有Actions都使用MetaGPT原生的 `ProjectRepo`
- 移除了自定义路径管理逻辑
- 使用标准的文件系统操作

### 5. 重构Company服务
- 使用MetaGPT原生的 `Team` 和 `Environment`
- 使用原生的项目路径管理
- 简化了消息路由逻辑

## 阿里云搜索引擎集成

### 配置方式

1. **通过配置文件** (`config/config2.yaml`):
```yaml
search:
  api_type: "alibaba"
  api_key: "OS-ykkz87t4q83335yl"
  endpoint: "http://default-0t01.platform-cn-shanghai.opensearch.aliyuncs.com"
  workspace: "default"
  service_id: "ops-web-search-001"
```

2. **通过代码**:
```python
from metagpt.tools.search_engine import SearchEngine
from metagpt.configs.search_config import SearchEngineType

# 方式1: 使用默认配置（自动读取config2.yaml）
search_engine = SearchEngine()

# 方式2: 显式指定参数
search_engine = SearchEngine(
    engine=SearchEngineType.ALIBABA,
    api_key="your_api_key",
    endpoint="your_endpoint",
    workspace="your_workspace",
    service_id="your_service_id"
)
```

### 测试方法

```bash
# 测试阿里云搜索引擎
python test_alibaba_search.py

# 测试完整集成
python test_native_integration.py
```

## 架构流程

```
用户输入 → Company服务 → Team环境 → 智能体协作
    ↓
ProjectManager (WriteTasks) → Architect (WriteDesign) → 专业智能体并行执行
    ↓
CaseExpert (案例研究) + DataAnalyst (数据分析) → WriterExpert (报告撰写)
    ↓
输出到 workspaces/{project_id}/ 目录
```

## 智能体职责

1. **ProjectManager (吴丽)**: 使用 `WriteTasks` 制定项目计划
2. **Architect (李明)**: 使用 `WriteDesign` 设计报告结构
3. **CaseExpert (王磊)**: 搜索和分析相关案例（使用原生阿里云搜索引擎）
4. **DataAnalyst (赵丽娅)**: 分析用户上传的数据文件
5. **WriterExpert (张翰)**: 根据前面的结果撰写最终报告

## 文件存储结构

```
workspaces/
└── {project_id}/
    ├── docs/                    # MetaGPT原生文档目录
    │   ├── prd/                # 产品需求文档
    │   ├── system_design/      # 系统设计文档
    │   └── tasks/              # 任务列表
    ├── research/
    │   └── cases/              # 案例研究报告
    ├── analysis/               # 数据分析报告
    ├── reports/                # 最终报告
    └── uploads/                # 用户上传文件
```

## 优势

1. **稳定性**: 使用MetaGPT原生架构，避免序列化问题
2. **兼容性**: 完全兼容MetaGPT的生态系统
3. **可维护性**: 代码结构更清晰，依赖关系更简单
4. **扩展性**: 可以轻松添加新的原生Actions和工具
5. **搜索引擎**: 阿里云搜索引擎完全集成到MetaGPT原生架构中

## 注意事项

1. 所有文件都保存在 `workspaces/{project_id}/` 目录下
2. 使用MetaGPT原生的序列化机制，无需自定义序列化逻辑
3. 智能体之间的通信通过标准的Message机制
4. 项目状态由MetaGPT原生环境管理
5. 阿里云搜索引擎现在是MetaGPT的默认搜索引擎

## 下一步计划

1. 测试重构后的代码
2. 优化智能体协作流程
3. 添加更多专业Actions
4. 集成前端界面 