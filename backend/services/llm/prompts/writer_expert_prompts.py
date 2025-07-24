"""
WriterExpertAgent's Prompts
存放写作专家(WriterExpertAgent)所有与LLM交互的提示词模板。
"""

def get_content_creation_prompt(topic: str, outline: str, writer_name: str) -> str:
    """获取用于内容创作的Prompt"""
    return f"""
你是写作专家{writer_name}，请根据以下主题和大纲创作专业内容。

## 创作要求
主题：{topic}
大纲：{outline}

## 创作要求
请创作符合以下要求的内容：
1. 结构清晰，层次分明
2. 语言专业，表达准确
3. 逻辑连贯，论证有力
4. 内容丰富，信息充实
5. 符合学术或专业标准

## 输出格式
请直接输出创作的内容，使用Markdown格式，包含：
- 清晰的标题结构
- 段落分明的内容
- 适当的引用和说明
- 专业的语言表达

请直接输出创作的内容。
"""

def get_content_optimization_prompt(content: str, optimization_type: str, writer_name: str) -> str:
    """获取用于内容优化的Prompt"""
    return f"""
你是写作专家{writer_name}，请对以下内容进行{optimization_type}优化。

## 原始内容
{content}

## 优化要求
请进行以下优化：
1. 提升语言表达的专业性
2. 优化句式结构和可读性
3. 增强逻辑连贯性
4. 完善论证和论据
5. 统一术语和表达风格

## 输出格式
请直接输出优化后的内容，保持原有的核心信息和结构。
"""

def get_section_writing_prompt(section_title: str, requirements: str, context: str, writer_name: str) -> str:
    """获取用于章节写作的Prompt"""
    return f"""
你是写作专家{writer_name}，请根据要求撰写特定章节。

## 章节信息
章节标题：{section_title}
写作要求：{requirements}
上下文信息：{context}

## 写作要求
请撰写符合以下要求的内容：
1. 紧扣章节主题
2. 满足写作要求
3. 与上下文保持一致
4. 语言专业规范
5. 结构清晰合理

## 输出格式
请直接输出章节内容，使用Markdown格式。
""" 