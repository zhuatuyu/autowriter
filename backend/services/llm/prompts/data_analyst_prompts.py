"""
DataAnalystAgent's Prompts
存放数据分析师(DataAnalystAgent)所有与LLM交互的提示词模板。
"""

def get_data_extraction_prompt(content: str, data_type: str, analyst_name: str) -> str:
    """获取用于数据提取的Prompt"""
    return f"""
你是数据分析师{analyst_name}，请从以下内容中提取{data_type}：

## 内容
{content}

## 提取要求
请提取所有相关的数据，包括：
1. 数值数据（金额、百分比、数量等）
2. 时间数据（日期、期间等）
3. 分类数据（类别、等级等）
4. 关键指标（KPI、目标值等）

## 输出格式
请以结构化的格式输出，便于后续分析：
- 使用表格或列表格式
- 标注数据类型和单位
- 突出重要数据点
- 提供数据来源说明

请直接输出提取的数据。
"""

def get_data_analysis_prompt(data: str, analysis_type: str, analyst_name: str) -> str:
    """获取用于数据分析的Prompt"""
    return f"""
你是专业的数据分析师{analyst_name}，请对以下数据进行{analysis_type}：

## 数据
{data}

## 分析要求
请提供：
1. 数据概览和基本统计
2. 主要趋势和模式
3. 关键发现和洞察
4. 数据质量评估
5. 分析结论和建议

## 输出格式
请用专业的数据分析语言，提供清晰的分析结果：
- 使用专业术语
- 提供量化指标
- 给出趋势分析
- 提出改进建议

请直接输出分析结果。
"""

def get_chart_generation_prompt(analysis_content: str, analyst_name: str) -> str:
    """获取用于图表生成的Prompt"""
    return f"""
你是数据分析师{analyst_name}，请基于以下分析内容生成数据可视化建议：

## 分析内容
{analysis_content}

## 可视化要求
请建议以下图表类型：
1. **趋势图**: 展示数据随时间的变化趋势
2. **柱状图**: 比较不同类别的数据
3. **饼图**: 展示数据的构成比例
4. **散点图**: 展示变量间的相关关系
5. **热力图**: 展示数据的分布模式

## 输出格式
请为每个建议的图表提供：
- 图表类型
- 数据来源
- 展示目的
- 关键信息点

请直接输出图表建议。
""" 