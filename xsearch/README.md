# 🧠 智能分析系统 - 端到端验证

基于向量检索 + LangExtract + 知识图谱 + LLM的完整智能分析流程。

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行分析
```bash
# 使用默认查询
python xsearch/app.py -f /Users/xuchuang/Desktop/PYTHON3/autowriter/config/project01.yaml

# 使用自定义查询
python xsearch/app.py -f /Users/xuchuang/Desktop/PYTHON3/autowriter/config/project01.yaml --query "分析项目进度管理效果"

# 指定输出文件名
python xsearch/app.py -f /Users/xuchuang/Desktop/PYTHON3/autowriter/config/project01.yaml --output my_analysis
```

## 🏗️ 系统架构

### 核心组件
- **智能分析器** (`intelligent_analyzer.py`): 协调整个分析流程
- **LLM客户端** (`llm_client.py`): 与Google Gemini API交互
- **向量搜索客户端** (`vector_searcher.py`): 复用现有向量搜索服务
- **知识图谱客户端** (`kg_client.py`): 复用现有知识图谱服务

### 分析流程
1. **动态理解查询意图** → LLM分析用户查询
2. **动态生成检索策略** → 基于意图生成检索关键词和提取字段
3. **动态执行检索与提取** → 向量检索 + LangExtract提取
4. **动态生成评价提示词** → 基于提取结果生成评价提示
5. **LLM生成评价结果** → 综合分析并给出评价意见

## 📊 输出结果

系统会生成一个JSON文件，包含：
- 查询意图分析结果
- 检索策略详情
- 提取的结构化数据
- LLM生成的评价结果
- 数据源统计信息

## 🔧 配置说明

系统会自动从项目配置文件读取：
- 项目向量存储路径
- 全局向量存储路径
- 输出目录等配置

## 💡 使用场景

适用于任何类型的项目分析需求：
- 资金使用合理性分析
- 质量控制体系评估
- 进度管理效果分析
- 成本控制评价
- 等等...

## 🎯 技术特点

- **完全动态**: 不依赖硬编码的查询词和字段
- **智能理解**: LLM自动理解用户意图
- **策略生成**: 动态生成检索和提取策略
- **通用性强**: 适用于任何类型的项目分析需求
- **可扩展性**: 新项目类型无需修改代码
