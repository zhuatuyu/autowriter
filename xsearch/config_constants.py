#!/usr/bin/env python3
"""
xsearch系统配置常量
集中管理所有配置参数，避免循环导入
"""

# ========== 🔧 系统配置常量 ==========
"""
系统配置常量说明：

1. LANGEXTRACT_CONFIG: LangExtract信息提取配置
   - MODEL_ID: 使用的LLM模型，影响提取质量和速度
   - EXTRACTION_PASSES: 提取轮次，1=单次，2=双重提取（可能发现遗漏信息）
   - MAX_WORKERS: 并行工作线程，1=串行，3=平衡，10=高并发
   - MAX_CHAR_BUFFER: 字符缓冲区大小，影响单次处理的文本长度
   - MAX_DOCS_TO_PROCESS: 最大处理文档数，避免超时

2. VECTOR_SEARCH_CONFIG: 向量搜索配置
   - PROJECT_TOP_K: 项目文档召回数量，控制项目知识库返回结果数
   - GLOBAL_TOP_K: 全局知识库召回数量，控制全局知识库返回结果数
   - GLOBAL_METHODS_DISPLAY_LIMIT: 全局方法显示限制，在评价提示词中最多显示几条

3. EVALUATION_CONFIG: 评价结构配置（LLM解析失败时的默认值）
   - DEFAULT_STRUCTURE: 默认评价结构
   - DEFAULT_SEARCH_KEYWORDS: 默认检索关键词
   - DEFAULT_EXTRACTION_FIELDS: 默认提取字段

4. INTENT_ANALYSIS_CONFIG: 意图分析配置（LLM解析失败时的默认值）
   - DEFAULT_CORE_TOPIC: 默认核心主题
   - DEFAULT_DATA_REQUIREMENTS: 默认数据类型需求
   - DEFAULT_ANALYSIS_DIMENSIONS: 默认分析维度

调整建议：
- 提高召回数量：增加 PROJECT_TOP_K 和 GLOBAL_TOP_K
- 提高提取质量：增加 EXTRACTION_PASSES 到 2
- 提高处理速度：增加 MAX_WORKERS 到 5-10
- 处理长文本：增加 MAX_CHAR_BUFFER 到 3000-5000
"""

# LangExtract配置常量
LANGEXTRACT_CONFIG = {
    "MODEL_ID": "gemini-2.5-flash",           # 使用的LLM模型ID
    "EXTRACTION_PASSES": 1,                   # 信息提取轮次：1=单次提取，2=双重提取（可能发现遗漏信息）
    "MAX_WORKERS": 3,                         # 最大并行工作线程：1=串行处理，3=平衡性能，10=高并发
    "MAX_CHAR_BUFFER": 2000,                  # 最大字符缓冲区：1000=短文本块，2000=平衡，5000=长文本处理
    "MAX_DOCS_TO_PROCESS": 5                  # 最大处理文档数：避免处理过多文档导致超时
}

# 向量搜索配置常量
VECTOR_SEARCH_CONFIG = {
    "PROJECT_TOP_K": 5,                       # 项目文档召回数量：控制项目知识库返回结果数
    "GLOBAL_TOP_K": 6,                        # 全局知识库召回数量：控制全局知识库返回结果数
    "GLOBAL_METHODS_DISPLAY_LIMIT": 6         # 全局检索到多少就进多少进提示词,全局方法显示限制：在评价提示词中最多显示几条全局方法
}

# 评价结构配置常量
EVALUATION_CONFIG = {
    "DEFAULT_STRUCTURE": ["现状分析", "问题识别", "改进建议"],  # 默认评价结构（当LLM解析失败时使用）
    "DEFAULT_SEARCH_KEYWORDS": ["项目", "分析", "评价"],      # 默认检索关键词
    "DEFAULT_EXTRACTION_FIELDS": ["基本信息", "关键指标", "问题描述"]  # 默认提取字段
}

# 意图分析配置常量
INTENT_ANALYSIS_CONFIG = {
    "DEFAULT_CORE_TOPIC": "项目分析",          # 默认核心主题
    "DEFAULT_DATA_REQUIREMENTS": ["项目数据", "评价标准"],  # 默认数据类型需求
    "DEFAULT_ANALYSIS_DIMENSIONS": ["有效性", "合理性"]     # 默认分析维度
}
