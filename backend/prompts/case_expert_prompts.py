"""
CaseExpertAgent's Prompts
存放案例专家(CaseExpertAgent)所有与LLM交互的提示词模板。
"""

def get_search_summary_prompt(search_results: list, expert_name: str) -> str:
    """获取用于生成搜索摘要的Prompt"""
    return f"""
# 指令：生成案例搜索摘要报告

你是案例专家{expert_name}，请根据以下搜索结果生成一份专业的搜索摘要报告。

## 搜索结果
{search_results}

## 要求
请生成一份包含以下内容的摘要报告：
1. 搜索概览（搜索的查询数量、时间等）
2. 主要发现（找到的关键案例和最佳实践）
3. 后续建议（如何利用这些案例）

## 格式要求
- 使用Markdown格式
- 包含搜索专家姓名和搜索时间
- 对每个搜索结果提供简要描述
- 总结主要发现和建议

请直接输出完整的摘要报告。
"""

def get_case_analysis_prompt(cases_content: list, expert_name: str) -> str:
    """获取用于案例分析的Prompt"""
    return f"""
# 指令：进行案例分析

你是案例专家{expert_name}，请对以下案例进行深入分析。

## 案例内容
{cases_content}

## 分析要求
请从以下角度分析每个案例：
1. 实施背景
2. 主要做法
3. 取得成效
4. 经验启示

## 输出格式
请生成一份结构化的案例分析报告，包含：
- 案例概述
- 关键要点分析
- 可借鉴的经验
- 实施建议

请直接输出完整的分析报告。
"""

def get_best_practices_prompt(analysis_files: list, expert_name: str) -> str:
    """获取用于整理最佳实践的Prompt"""
    return f"""
# 指令：整理最佳实践

你是案例专家{expert_name}，请基于以下分析结果整理出最佳实践。

## 分析文件
{analysis_files}

## 整理要求
请整理出以下内容：
1. 通用最佳实践原则
2. 具体实施方法
3. 成功关键因素
4. 风险防范措施

## 输出格式
请生成一份"最佳实践汇编"报告，包含：
- 实践原则总结
- 具体操作方法
- 成功案例分享
- 实施建议

请直接输出完整的实践汇编。
""" 