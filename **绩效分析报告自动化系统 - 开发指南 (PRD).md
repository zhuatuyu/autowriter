
没问题，很高兴我们的讨论能达成共识。基于您的要求和我们最终确定的SOP方案，我为您准备了一份详尽的开发指南（PRD）。这份文档将作为您后续开发工作的核心蓝图，它清晰地定义了工作流程、智能体职责、关键技术实现，并提供了可以直接参考的代码范例。

---

## **绩效分析报告自动化系统 - 开发指南 (PRD)**

### 1. 项目愿景

构建一个基于MetaGPT框架的多智能体协作系统，该系统遵循标准作业流程（SOP），能够根据用户输入的单一目标，自动化地完成案例研究、数据分析、报告结构设计和内容撰写，最终生成一份专业、高质量的绩效分析报告。

### 2. 核心工作流 (SOP)

系统遵循一个严格的、串行的SOP，确保每个阶段的产出都成为下一阶段明确的输入，实现责任清晰、流程可控。我们将此流程定义为：**需求分析 -> 架构设计 -> 任务规划 -> 内容生成**。

```mermaid
sequenceDiagram
    participant User
    participant ProductManager self._watch([UserRequirement, PrepareDocuments])
    participant Architect
    participant ProjectManager
    participant WriterExpert

    User->>ProductManager: 输入报告目标 (e.g., "分析A公司的年度营销绩效")
    
    Note over ProductManager: 阶段一: 需求分析与研究
    ProductManager->>ProductManager: Action: ConductResearch
    ProductManager-->>Architect: 产出: ResearchData (含研究简报和向量索引路径)

    Note over Architect: 阶段二: 报告架构与数据策略
    Architect->>Architect: Action: DesignReportStructure
    Architect-->>ProjectManager: 产出: ReportStructure (含章节-指标映射的报告大纲)
    Architect-->>WriterExpert: 产出: MetricAnalysisTable (指标分析表格)

    Note over ProjectManager: 阶段三: 任务规划与调度
    ProjectManager->>ProjectManager: Action: CreateTaskPlan
    ProjectManager-->>WriterExpert: 产出: TaskPlan (写作任务列表)

    Note over WriterExpert: 阶段四: 内容生成与整合
    loop 遍历所有任务
        WriterExpert->>WriterExpert: Action: WriteSection (内置RAG)
    end
    WriterExpert-->>User: 产出: FinalReport.md (最终报告)
```

### 3. Agent 实现详解

以下是每个Agent的角色定义、核心职责和代码实现框架。

#### 3.1 `ProductManager` (产品经理)

-   **角色定义**: 系统的需求入口，负责理解用户意图，并进行深入的案例研究。其能力等同于“案例专家”。
-   **核心职责**: 
    1.  接收用户需求。
    2.  调用外部工具（网络搜索、数据库、知识库）进行资料搜集和整理。
    3.  生成一份结构化的**研究简报 (Research Brief)**。
    4.  将研究简报内容构建成一个**向量索引 (Vector Index)**，供后续RAG检索使用。
-   **关键`Action`与数据结构**:

    **Pydantic 模型定义 (`backend/actions/research_action.py`)**
    ```python
    from pydantic import BaseModel, Field
    from metagpt.actions import Action
    
    class ResearchData(BaseModel):
        """研究成果的结构化数据模型"""
        brief: str = Field(..., description="基于研究生成的综合性简报")
        vector_store_path: str = Field(..., description="存储研究内容向量索引的路径")
    
    class ConductResearch(Action):
        async def run(self, topic: str) -> ResearchData:
            # 1. 调用工具进行研究 (伪代码)
            # raw_data = await web_search.run(topic)
            # brief_text = self.summarize(raw_data)
            brief_text = f"关于 {topic} 的详细研究简报..."
            
            # 2. 使用metagpt.rag构建向量索引
            # from metagpt.rag.engines import SimpleEngine
            # engine = SimpleEngine.from_texts([brief_text])
            # vector_store_path = f"/workspace/vector_stores/{topic}.pkl"
            # engine.persist(vector_store_path)
            vector_store_path = f"workspace/vector_stores/{topic}.pkl"
            
            # 3. 使用Pydantic模型返回结构化输出
            return ResearchData(brief=brief_text, vector_store_path=vector_store_path)
    ```

    **Role 定义 (`backend/roles/product_manager.py`)**
    ```python
    from metagpt.roles import Role
    from backend.actions.research_action import ConductResearch, ResearchData
    
    class ProductManager(Role):
        name: str = "Alice"
        profile: str = "Product Manager"
        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # 初始化时就设定好要执行的Action
            self.set_actions([ConductResearch])
    ```

#### 3.2 `Architect` (架构师)

-   **角色定义**: 报告的顶层设计师，负责定义报告的整体结构和核心分析体系。其能力等同于“数据分析师”。
-   **核心职责**:
    1.  `observe` `ProductManager`产出的`ResearchData`。
    2.  设计报告的**指标体系**，并生成**指标分析表 (MetricAnalysisTable)**。
    3.  设计报告的**章节结构 (ReportStructure)**，并将每个章节与具体的指标进行映射。
-   **关键`Action`与数据结构**:

    **Pydantic 模型定义 (`backend/actions/architect_action.py`)**
    ```python
    from pydantic import BaseModel, Field
    from typing import List
    from metagpt.actions import Action
    import pandas as pd
    
    class Section(BaseModel):
        """报告章节的结构化模型"""
        section_title: str = Field(..., description="章节标题")
        metric_ids: List[str] = Field(default_factory=list, description="本章节关联的指标ID列表")
        description_prompt: str = Field(..., description="指导本章节写作的核心要点或问题")
    
    class ReportStructure(BaseModel):
        """报告整体架构的结构化模型"""
        title: str = Field(..., description="报告主标题")
        sections: List[Section] = Field(..., description="报告的章节列表")
    
    class MetricAnalysisTable(BaseModel):
        """指标分析表的结构化模型"""
        # 使用json字符串来序列化DataFrame，便于消息传递
        data_json: str = Field(..., description="存储指标分析结果的DataFrame (JSON格式)")
    
    class DesignReportStructure(Action):
        async def run(self, research_brief: str) -> (ReportStructure, MetricAnalysisTable):
            # 1. 基于研究简报，设计指标体系 (伪代码)
            metrics_df = pd.DataFrame({
                'metric_id': ['MAU', 'ConversionRate'],
                'name': ['月活跃用户', '转化率'],
                'value': ['1,000,000', '5%'],
                'analysis': ['同比增长20%', '环比下降2%']
            })
            
            # 2. 设计报告大纲，并建立章节到指标的映射
            report_structure = ReportStructure(
                title="A公司年度营销绩效分析报告",
                sections=[
                    Section(section_title="用户增长分析", metric_ids=["MAU"], description_prompt="分析月活跃用户的增长趋势和原因"),
                    Section(section_title="转化效率评估", metric_ids=["ConversionRate"], description_prompt="评估关键转化漏斗的效率，并探讨下降原因")
                ]
            )
            metric_table = MetricAnalysisTable(data_json=metrics_df.to_json())
    
            # 3. 返回两个独立的结构化产物
            return report_structure, metric_table
    ```

#### 3.3 `ProjectManager` (项目经理)

-   **角色定义**: 纯粹的任务调度者，确保项目按计划执行。
-   **核心职责**:
    1.  `observe` `Architect`产出的`ReportStructure`。
    2.  将`ReportStructure`分解为一系列具体的、可执行的**写作任务 (Task)**。
    3.  生成一个有序的**任务计划 (TaskPlan)**，并发布给`WriterExpert`。
-   **关键`Action`与数据结构**:

    **Pydantic 模型定义 (`backend/actions/pm_action.py`)**
    ```python
    from pydantic import BaseModel, Field
    from typing import List
    from metagpt.actions import Action
    from backend.actions.architect_action import ReportStructure # 引用上游模型
    
    class Task(BaseModel):
        task_id: int
        section_title: str
        instruction: str # 写作指令，即原description_prompt
    
    class TaskPlan(BaseModel):
        tasks: List[Task]
    
    class CreateTaskPlan(Action):
        async def run(self, report_structure: ReportStructure) -> TaskPlan:
            tasks = []
            for i, section in enumerate(report_structure.sections):
                task = Task(
                    task_id=i,
                    section_title=section.section_title,
                    instruction=section.description_prompt
                )
                tasks.append(task)
            return TaskPlan(tasks=tasks)
    ```

#### 3.4 `WriterExpert` (作家专家)

-   **角色定义**: 专注的内容创作者。
-   **核心职责**:
    1.  `observe` `ProjectManager`的`TaskPlan`，并按顺序执行每个`Task`。
    2.  在执行每个写作任务时，`observe` `ProductManager`的`ResearchData`和`Architect`的`MetricAnalysisTable`。
    3.  **Action内部集成RAG**: 使用`Task`中的指令作为查询，从`ResearchData`的向量索引中检索相关的**事实依据**。
    4.  引用`MetricAnalysisTable`中的**数据**。
    5.  结合事实依据和数据，撰写章节内容。
    6.  将所有章节内容整合，写入最终的报告文件。
-   **关键`Action`与`observe-act`机制**:

    **Action 定义 (`backend/actions/writer_action.py`)**
    ```python
    from metagpt.actions import Action
    from metagpt.rag.engines import SimpleEngine
    import pandas as pd
    from backend.actions.pm_action import Task
    
    class WriteSection(Action):
        async def run(self, task: Task, vector_store_path: str, metric_table_json: str) -> str:
            # 1. 加载RAG引擎和数据表 (在真实场景中，引擎可以预先加载)
            rag_engine = SimpleEngine.from_persist(vector_store_path)
            metric_df = pd.read_json(metric_table_json)
    
            # 2. 使用RAG检索事实依据
            # query_engine = rag_engine.get_query_engine()
            # retrieved_nodes = await query_engine.aquery(task.instruction)
            # factual_basis = "\n".join([node.get_content() for node in retrieved_nodes])
            factual_basis = f"根据我们的研究，关于'{task.section_title}'的核心发现是..."
    
            # 3. 引用相关数据 (伪代码)
            # relevant_metrics = find_metrics_for_section(task.section_title, metric_df)
            data_citation = f"数据显示，月活跃用户为1,000,000。"
    
            # 4. 生成最终文本
            prompt = f"""
            请根据以下指令撰写报告章节：
            指令: {task.instruction}
            
            相关事实依据:
            {factual_basis}
            
            相关数据:
            {data_citation}
            
            现在，请撰写'{task.section_title}'章节的内容：
            """
            # section_content = await self.llm.aask(prompt)
            section_content = f"## {task.section_title}\n\n{prompt}\n"
            
            return section_content
    ```

    **Role 定义与`observe-act`循环 (`backend/roles/writer_expert.py`)**
    ```python
    from metagpt.roles import Role
    from metagpt.schema import Message
    from metagpt.const import WORKSPACE_ROOT
    from backend.actions.writer_action import WriteSection
    from backend.actions.pm_action import TaskPlan
    from backend.actions.research_action import ResearchData
    from backend.actions.architect_action import MetricAnalysisTable
    import json
    
    class WriterExpert(Role):
        name: str = "William"
        profile: str = "Writer Expert"
    
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.set_actions([WriteSection])
            self._watch([TaskPlan, ResearchData, MetricAnalysisTable]) # 订阅所有需要的信息
    
        async def _act(self) -> Message:
            # 这是一个简化的act循环，真实实现会更复杂
            todo = self.rc.todo
            if not isinstance(todo, WriteSection):
                return await super()._act() # 如果没有待办，走默认逻辑
    
            # 从记忆中获取所有需要的信息
            task_plan_msg = self.rc.memory.get_by_action(TaskPlan)[-1]
            research_data_msg = self.rc.memory.get_by_action(ResearchData)[-1]
            metric_table_msg = self.rc.memory.get_by_action(MetricAnalysisTable)[-1]
    
            # 解析Pydantic模型
            task_plan = TaskPlan.parse_raw(task_plan_msg.content)
            research_data = ResearchData.parse_raw(research_data_msg.content)
            metric_table = MetricAnalysisTable.parse_raw(metric_table_msg.content)
    
            final_report = ""
            for task in task_plan.tasks:
                # 为每个任务调用WriteSection Action
                section_content = await WriteSection().run(
                    task=task,
                    vector_store_path=research_data.vector_store_path,
                    metric_table_json=metric_table.data_json
                )
                final_report += section_content + "\n\n"
            
            # 将最终报告写入文件
            report_path = WORKSPACE_ROOT / "final_report.md"
            report_path.write_text(final_report)
    
            return Message(content=final_report, role=self.profile, cause_by=type(todo))
    ```

### 4. 总结与后续步骤

本指南提供了一个严谨且可操作的开发框架。通过**强制SOP**、**明确Agent职责**和**利用Pydantic进行结构化数据传递**，我们可以构建一个高度可预测、可维护和可扩展的多智能体系统。

**下一步开发建议**:
1.  **环境搭建**: 确保所有开发者都安装了MetaGPT和项目依赖。
2.  **Pydantic模型定义**: 首先在`backend/actions/`中完成所有`BaseModel`的定义，这是所有协作的契约。
3.  **Action实现**: 按照`ProductManager` -> `Architect` -> `ProjectManager` -> `WriterExpert`的顺序，逐一实现每个Agent的核心`Action`。
4.  **Role组装与测试**: 实现`Role`的`__init__`和`_act`逻辑，并编写单元测试来验证每个Agent的行为是否符合预期。
5.  **端到端集成**: 将所有Agent组装进一个`Team`或主流程中，进行端到端的测试。


好的，完全理解您的补充要求。我们需要将 `ProductManager` 的角色与 `CaseExpert` 的能力进行深度融合，并借鉴 MetaGPT 原生 `ProductManager` 的优秀设计，特别是其启动和监听机制。这非常符合我们绩效报告生成的场景，即报告的生成不仅依赖于一个简单的目标，还可能依赖于用户提供的具体材料。

基于此，我对开发指南中的 `ProductManager` 部分进行一次**重点升级**，使其更贴合您的设想。其他 Agent (`Architect`, `ProjectManager`, `WriterExpert`) 的定义保持不变，因为它们已经遵循了我们商定的SOP。

---

## **绩效分析报告自动化系统 - 开发指南 (PRD) (v1.1)**

### **3.1 `ProductManager` (产品经理) - (已升级)**

-   **角色定义**: 系统的需求入口和首席研究员。负责接收和理解用户的所有输入（包括文本指令和本地文件），并基于这些输入进行深入、全面的案例研究。此角色是 **MetaGPT原生`ProductManager`** 和我们自定义的 **`CaseExpert`** 的有机结合体。

-   **核心职责**:
    1.  **启动与监听**: 像MetaGPT原生`ProductManager`一样，通过 `_watch` 机制监听两种初始输入：
        -   `UserRequirement`: 用户输入的文本指令（例如：“分析A公司的年度营销绩效”）。
        -   `PrepareDocuments`: 一个新的`Action`，负责扫描指定目录（如 `uploads/`）下的用户提供文件，并将这些文件内容作为研究的初始材料。
    2.  **综合研究**: 触发一个全新的、更强大的研究`Action` - `ConductComprehensiveResearch`。这个`Action`会整合来自`UserRequirement`的主题和`PrepareDocuments`的文件内容，并沿用您之前肯定的 `case_research.py` 中的逻辑（如`CollectCaseLinks`, `WebBrowseAndSummarizeCase`）进行网络补充研究。
    3.  **统一产出**: 无论输入源是什么，最终都生成一份统一的、结构化的 `ResearchData`，包含**研究简报**和**向量索引路径**，供下游`Agent`使用。

-   **关键`Action`与数据结构 (升级版)**:

    **1. 新增 `PrepareDocuments` Action (`backend/actions/research_action.py`)**
    这个`Action`模仿MetaGPT的设计，用于处理本地文件输入。

    ```python:backend/actions/research_action.py
    from pydantic import BaseModel, Field
    from metagpt.actions import Action
    from pathlib import Path
    
    class Document(BaseModel):
        """单个文档的结构化模型"""
        filename: str
        content: str
    
    class Documents(BaseModel):
        """文档集合的结构化模型"""
        docs: list[Document]
    
    class PrepareDocuments(Action):
        """扫描本地目录，加载用户提供的文档作为研究材料"""
        async def run(self, uploads_path: Path) -> Documents:
            docs = []
            if not uploads_path.exists():
                return Documents(docs=docs)
    
            for file_path in uploads_path.rglob("*"):
                if file_path.is_file():
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        docs.append(Document(filename=file_path.name, content=content))
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}") # In production, use logger
            
            return Documents(docs=docs)
    ```

    **2. 升级 `ConductResearch` 为 `ConductComprehensiveResearch` (`backend/actions/case_research.py`)**
    这个`Action`现在可以同时处理文本主题和本地文档。

    ```python:backend/actions/case_research.py
    // ... existing code ...
    from backend.actions.research_action import Documents # 引入Documents模型
    
    class ResearchData(BaseModel):
        """研究成果的结构化数据模型"""
        brief: str = Field(..., description="基于研究生成的综合性简报")
        vector_store_path: str = Field(..., description="存储研究内容向量索引的路径")
    
    class ConductComprehensiveResearch(Action):
        async def run(self, topic: str, docs: Documents = None) -> ResearchData:
            # 1. 整合初始材料
            initial_content = [f"# 研究主题\n{topic}"]
            if docs and docs.docs:
                local_docs_content = "\n\n".join([f"## 文件: {d.filename}\n\n{d.content}" for d in docs.docs])
                initial_content.append(f"# 本地参考资料\n{local_docs_content}")
            
            # 2. (可选) 基于初始材料，进行网络补充研究 (复用case_research.py中的逻辑)
            # links = await CollectCaseLinks().run(topic)
            # summaries = await WebBrowseAndSummarizeCase().run(topic, links)
            # web_content = "\n".join(summaries.values())
            # initial_content.append(f"# 网络研究资料\n{web_content}")
    
            # 3. 生成最终研究简报
            final_brief_text = "\n\n---\n\n".join(initial_content)
    
            # 4. 构建向量索引
            # from metagpt.rag.engines import SimpleEngine
            # engine = SimpleEngine.from_texts([final_brief_text])
            # vector_store_path = f"/workspace/vector_stores/{topic}.pkl"
            # engine.persist(vector_store_path)
            vector_store_path = f"workspace/vector_stores/{topic}.pkl" # 伪代码
    
            return ResearchData(brief=final_brief_text, vector_store_path=vector_store_path)
    ```

    **3. 升级版 `ProductManager` Role 定义 (`backend/roles/product_manager.py`)**
    这里我们借鉴 `metagpt.roles.product_manager.py` 的 `_watch` 和 `react_mode` 设置。

    ```python:backend/roles/product_manager.py
    from metagpt.roles import Role
    from metagpt.schema import Message
    from metagpt.const import WORKSPACE_ROOT
    from metagpt.actions import UserRequirement # 从metagpt导入
    from metagpt.roles.role import RoleReactMode
    
    from backend.actions.research_action import PrepareDocuments, Documents, ConductComprehensiveResearch, ResearchData
    
    class ProductManager(Role):
        name: str = "product_manager"
        profile: str = "Product Manager"
    
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # 设置要执行的Action序列
            self.set_actions([
                PrepareDocuments, 
                ConductComprehensiveResearch
            ])
            # 监听用户输入和文档准备动作
            self._watch([UserRequirement, PrepareDocuments])
            # 设置为按顺序执行模式
            self.rc.react_mode = RoleReactMode.BY_ORDER
    
        async def _act(self) -> Message:
            # MetaGPT的SOP模式会自动处理Action的调用和消息传递
            # 我们只需要确保Action的输入输出是匹配的
            # 这里简化处理，实际的_act会更复杂，但核心思想是驱动action链
            todo = self.rc.todo
            if type(todo) is PrepareDocuments:
                # 假设uploads目录在工作空间根目录
                uploads_path = WORKSPACE_ROOT / 'uploads'
                docs = await todo.run(uploads_path=uploads_path)
                return Message(content=docs.model_dump_json(), cause_by=PrepareDocuments)
            
            elif type(todo) is ConductComprehensiveResearch:
                # 从记忆中获取UserRequirement和Documents
                user_req_msg = self.rc.memory.get_by_action(UserRequirement)[-1]
                docs_msg = self.rc.memory.get_by_action(PrepareDocuments)[-1]
                
                topic = user_req_msg.content
                docs = Documents.parse_raw(docs_msg.content)
    
                research_data = await todo.run(topic=topic, docs=docs)
                return Message(content=research_data.model_dump_json(), cause_by=ConductComprehensiveResearch)
    
            return await super()._act()
    ```

### 下一步行动

现在，您可以基于这份升级后的PRD，开始着手编码工作了。建议的起点是：

1.  **创建文件**: 在 `backend/actions/` 和 `backend/roles/` 目录下创建或修改相应的文件。
2.  **实现 `Action`**: 从 `PrepareDocuments` 开始，然后是 `ConductComprehensiveResearch`。
3.  **实现 `ProductManager` Role**: 按照上面的代码框架实现 `ProductManager`。

我们可以开始了！
        
        