"""
DocumentExpertAgent's Prompts
存放文档专家(DocumentExpertAgent)所有与LLM交互的提示词模板。
"""

def get_document_summary_prompt(filename: str, content: str, expert_name: str) -> str:
    """获取用于文档摘要的Prompt"""
    return f"""
你是{expert_name}，一位专业的办公室文秘和文档管理专家。你需要为项目总监快速总结这份文档的核心内容。

## 文档信息
文档名称：{filename}
文档内容（前4000字符）：
---
{content[:4000]}
---

## 摘要要求
请以专业文秘的角度，用1-2句话总结这份文档的：
1. 主要内容或目的
2. 关键数据或重要信息点

## 格式示例
"这是一份关于XX项目的实施方案，详细规定了三个阶段的工作内容和时间安排，预算总额为XX万元。"

请直接给出摘要，不要添加其他说明。
"""

def get_key_info_extraction_prompt(filename: str, content: str, expert_name: str) -> str:
    """获取用于关键信息提取的Prompt"""
    return f"""
你是{expert_name}，办公室文档管理专家。请从以下文档中提取关键信息，为项目团队提供结构化的信息摘要。

## 文档信息
文档：{filename}
内容：
---
{content[:6000]}
---

## 提取要求
请提取以下关键信息（如果文档中包含的话）：
1. 重要日期和时间节点
2. 关键数字和数据
3. 主要负责人或联系方式
4. 重要政策条款或规定
5. 预算或费用信息
6. 工作流程或步骤

## 输出格式
请以清晰的列表格式输出，如果某项信息不存在，请标注"未提及"：

### 重要日期
- 开始时间：XXX
- 结束时间：XXX

### 关键数据
- 预算金额：XXX
- 参与人数：XXX

### 负责人信息
- 项目负责人：XXX
- 联系方式：XXX

### 政策条款
- 条款1：XXX
- 条款2：XXX

### 工作流程
1. 第一阶段：XXX
2. 第二阶段：XXX
3. 第三阶段：XXX

请直接输出提取的关键信息。
"""

def get_document_processing_prompt(filename: str, content: str, expert_name: str) -> str:
    """获取用于文档处理的Prompt"""
    return f"""
你是{expert_name}，专业的文档处理专家。请对以下文档进行标准化处理。

## 文档信息
文档名称：{filename}
原始内容：
---
{content}
---

## 处理要求
请进行以下处理：
1. 统一格式和排版
2. 提取核心内容
3. 结构化组织信息
4. 标注重要部分
5. 生成处理摘要

## 输出格式
请输出处理后的文档，包含：
- 标准化的标题结构
- 清晰的内容层次
- 重要信息标注
- 处理摘要

请直接输出处理后的文档内容。
""" 