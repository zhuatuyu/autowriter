from metagpt.actions import Action
from metagpt.logs import logger
from backend.configs.llm_provider import llm

DATA_ANALYST_NAME = "赵丽娅"

DATA_EXTRACTION_PROMPT = """
# 角色：数据提取专家

## 任务：从以下文本中，精准地提取出与 **{data_type}** 相关的所有数据和关键信息。

## 要求：
1.  **精准识别**：只提取与指定数据类型直接相关的信息，忽略无关内容。
2.  **结构化输出**：以清晰、结构化的格式（如Markdown列表、表格或JSON）呈现提取的数据。如果数据是数值型，请进行清晰的罗列。
3.  **保留上下文**：在提取数据的同时，简要说明数据点的上下文（例如，数据来源、时间点等）。
4.  **完整性**：确保提取所有相关数据，无遗漏。

## 待处理文本：
```text
{content}
```

## 输出格式示例（Markdown列表）：

*   **数据点1**: [提取的数据]
    *   **上下文**: [数据的简要背景]
*   **数据点2**: [提取的数据]
    *   **上下文**: [数据的简要背景]

请开始提取 **{data_type}** 数据：
"""

DATA_ANALYSIS_PROMPT = """
# 角色：高级数据分析师 - {analyst_name}

## 任务：对以下提供的数据进行深入的 **{analysis_type}**。

## 分析要求：
1.  **理解数据**：首先，清晰地陈述你对所提供数据的理解。
2.  **选择分析方法**：根据 **{analysis_type}** 的要求，选择并说明你将使用的分析方法（例如，趋势分析、相关性分析、SWOT分析等）。
3.  **执行分析**：
    *   进行详细的计算和逻辑推理。
    *   识别数据中的关键模式、趋势、异常值或重要发现。
4.  **得出结论**：
    *   基于分析结果，总结出2-3个核心结论。
    *   结论必须有数据支持，清晰、简洁、有说服力。
5.  **提出建议（如果适用）**：根据结论，提出1-2个可行的、具体的建议。

## 待分析数据：
```text
{data}
```

## 输出结构：

### 1. 数据理解
[你对数据的解读]

### 2. 分析方法
[你选择的分析方法和原因]

### 3. 分析过程与发现
[详细的分析步骤、计算和关键发现]

### 4. 核心结论
[总结的核心观点]

### 5. 建议
[基于结论的建议]

请开始你的 **{analysis_type}**：
"""

class DataExtraction(Action):
    """数据提取动作"""
    async def run(self, content: str, data_type: str = "数值数据") -> str:
        """从内容中提取数据"""
        prompt = DATA_EXTRACTION_PROMPT.format(content=content, data_type=data_type)
        try:
            extracted_data = await llm.acreate_text(prompt)
            return extracted_data.strip()
        except Exception as e:
            logger.error(f"数据提取失败: {e}")
            return f"数据提取失败: {str(e)}"

class DataAnalysis(Action):
    """数据分析动作"""
    async def run(self, data: str, analysis_type: str = "趋势分析") -> str:
        """分析数据并生成报告"""
        prompt = DATA_ANALYSIS_PROMPT.format(data=data, analysis_type=analysis_type, analyst_name=DATA_ANALYST_NAME)
        try:
            analysis_result = await llm.acreate_text(prompt)
            return analysis_result.strip()
        except Exception as e:
            logger.error(f"数据分析失败: {e}")
            return f"数据分析失败: {str(e)}"