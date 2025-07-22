# MetaGPT记忆系统详解

## 1. 记忆系统架构

### 基础架构
```
BaseAgent (继承 MetaGPT Role)
    ↓
self.rc.memory = LongTermMemory()  # 长期记忆
    ↓  
MemoryStorage (FAISS向量存储)
    ↓
文件系统持久化 (DATA_PATH/role_mem/{role_id}/)
```

### 2. 记忆生命周期

#### 场景1: 客户开启新项目
```python
# 1. 创建Agent时
def __init__(self, agent_id, session_id, workspace_path):
    super().__init__(...)  # 继承MetaGPT Role
    
    # 2. 自动设置长期记忆
    self.rc.memory = LongTermMemory()
    
    # 3. 尝试恢复历史记忆
    self._recover_memory()

def _recover_memory(self):
    # 4. MetaGPT自动检查是否有历史记忆文件
    if hasattr(self.rc.memory, 'recover_memory'):
        self.rc.memory.recover_memory(self.agent_id, self.rc)
        # 如果是新项目，记忆为空
        # 如果是老项目，自动加载历史记忆
```

#### 场景2: 进行任务 - 记忆记录
```python
def record_work_memory(self, task_description: str, result: str):
    # 1. 创建工作记忆消息
    work_msg = Message(
        content=f"任务: {task_description}\n结果: {result}",
        role=self.profile,
        cause_by=BaseAgentAction,
        sent_from=self.name
    )
    
    # 2. 添加到记忆中
    self.rc.memory.add(work_msg)
    
    # 3. 自动持久化到文件
    if hasattr(self.rc.memory, 'persist'):
        self.rc.memory.persist()
```

#### 场景3: 重新继续 - 记忆恢复
```python
# 当系统重启或用户重新打开项目时
def _recover_memory(self):
    try:
        # MetaGPT自动从文件系统恢复记忆
        self.rc.memory.recover_memory(self.agent_id, self.rc)
        
        # 恢复工作状态
        self._load_workspace_state()
        
        logger.info(f"🧠 {self.name} 记忆恢复完成")
    except Exception as e:
        logger.error(f"❌ {self.name} 记忆恢复失败: {e}")
```

#### 场景4: 项目完结 - 记忆保存
```python
# 项目完成时，记忆自动持久化
def project_complete(self):
    # 1. 记录项目完成状态
    completion_msg = Message(
        content=f"项目完成: {datetime.now()}",
        role=self.profile
    )
    self.rc.memory.add(completion_msg)
    
    # 2. 强制持久化
    self.rc.memory.persist()
    
    # 3. 保存工作状态
    self._save_workspace_state()
```

## 3. MetaGPT原生记忆持久化机制

### 存储位置
```
DATA_PATH/role_mem/{role_id}/
├── default__vector_store.json    # FAISS向量索引
├── docstore.json                 # 文档存储
├── index_store.json              # 索引存储
└── vector_store.json             # 向量存储
```

### 存储引擎
- **FAISS**: Facebook AI Similarity Search，高效向量相似度搜索
- **文件系统**: JSON格式持久化
- **向量化**: 使用embedding将文本转换为向量

### 记忆检索机制
```python
async def get_relevant_memories(self, keyword: str) -> List[Message]:
    """获取相关记忆"""
    try:
        # 使用向量相似度搜索
        return self.rc.memory.try_remember(keyword)
    except Exception as e:
        return []

def get_work_context(self) -> str:
    """获取工作上下文"""
    # 获取最近的记忆
    recent_memories = self.rc.memory.get(k=5)
    
    context = f"=== {self.name} 的工作记忆 ===\n"
    for memory in recent_memories:
        context += f"• {memory.content[:100]}...\n"
    
    return context
```

## 4. 实际应用示例

### 文档专家的记忆应用
```python
class DocumentExpertAgent(BaseAgent):
    async def _execute_specific_task(self, task, context):
        # 1. 获取历史工作上下文
        work_context = self.get_work_context()
        
        # 2. 执行任务
        result = await self._process_documents(task)
        
        # 3. 记录工作记忆
        self.record_work_memory(
            task.get('description', '处理文档'),
            result.get('result', '任务完成')
        )
        
        return result
```

### 案例专家的记忆应用
```python
class CaseExpertAgent(BaseAgent):
    async def _search_cases(self, task):
        # 1. 检查是否有相关的历史搜索
        relevant_memories = self.get_relevant_memories(
            ' '.join(task.get('keywords', []))
        )
        
        # 2. 基于历史经验优化搜索策略
        if relevant_memories:
            # 使用历史经验改进搜索
            pass
        
        # 3. 执行搜索并记录结果
        result = await self._perform_search(task)
        
        # 4. 记录到长期记忆
        self.record_work_memory(
            f"案例搜索: {task.get('keywords')}",
            f"找到 {len(result.get('files_created', []))} 个相关案例"
        )
        
        return result
```

## 5. 记忆系统优势

### 持续学习
- Agent能从历史经验中学习
- 避免重复相同的错误
- 提高工作效率

### 上下文连续性
- 项目重启后能恢复工作状态
- 保持工作的连贯性
- 支持长期项目管理

### 智能检索
- 基于向量相似度的智能搜索
- 快速找到相关历史信息
- 支持模糊匹配和语义搜索