import asyncio
from pathlib import Path
from typing import Dict, Any, List

from metagpt.actions import Action
from metagpt.logs import logger
from metagpt.utils.common import CodeParser
from metagpt.actions.di.execute_nb_code import ExecuteNbCode

DATA_ANALYST_NAME = "赵丽娅"

# --- 新的、基于代码执行的Action --- #

ANALYZE_DATA_PROMPT = """
# 角色: 数据分析代码生成器

## 任务: 根据用户的分析指令，生成可直接执行的Python代码（使用Pandas）。

## 要求:
1.  **代码必须完整且可执行**：代码应该包含所有必要的库导入（主要是 `pandas`）。
2.  **读取数据**: 代码需要能够从指定的路径 (`{file_path}`) 读取数据文件（CSV或Excel）。
3.  **执行分析**: 根据用户的具体指令 (`{instruction}`) 进行数据操作和分析。
4.  **输出结果**: 
    *   **必须**使用 `print()` 函数输出最终的分析结果（例如, `print(df.describe())` 或 `print(final_result)`）。这是捕获结果的关键。
    *   如果需要生成图表，请将图表保存到指定的分析目录 (`{analysis_path}`)，并打印保存路径。
5.  **不要包含任何解释性文本**：只输出纯Python代码块。

## 用户指令:
{instruction}

## 可用文件:
你的代码应该处理以下文件之一：`{file_path}`

请生成代码：
"""

SUMMARIZE_ANALYSIS_PROMPT = """
# 角色: 数据分析报告撰写专家

## 任务: 将以下Python脚本的执行结果，总结成一份清晰、结构化的Markdown报告。

## 要求:
1.  **理解结果**: 首先，解读Python脚本的输出，理解其核心发现。
2.  **结构化呈现**: 使用Markdown格式（如标题、列表、表格）来组织报告。
3.  **突出重点**: 明确指出分析得出的关键结论、趋势或异常值。
4.  **客观准确**: 报告内容必须严格基于所提供的执行结果，不能臆测。

## Python脚本执行结果:
```
{analysis_result}
```

请开始撰写你的分析报告：
"""

class AnalyzeData(Action):
    """生成并执行代码以分析数据"""
    async def run(self, instruction: str, file_path: Path, analysis_path: Path) -> str:
        """根据指令，生成并执行代码分析文件"""
        prompt = ANALYZE_DATA_PROMPT.format(
            instruction=instruction,
            file_path=str(file_path),
            analysis_path=str(analysis_path)
        )
        
        # 1. 生成代码
        code_rsp = await self.llm.aask(prompt)
        code = CodeParser.parse_code(text=code_rsp)
        logger.info(f"生成的数据分析代码:\n{code}")

        # 2. 执行代码
        executor = ExecuteNbCode() # 使用沙箱执行代码
        await executor.init_code() # 初始化环境
        success, result = await executor.run(code)
        await executor.terminate()

        if not success:
            logger.error(f"数据分析代码执行失败: {result}")
            return f"代码执行失败: {result}"
        
        logger.info(f"代码执行成功，输出: \n{result}")
        
        # 3. 生成分析报告并保存
        summarize_action = SummarizeAnalysis(config=self.config)
        report = await summarize_action.run(result)
        
        # 4. 保存报告到文件
        analysis_path = Path(analysis_path)
        analysis_path.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名（基于指令的前20个字符）
        safe_instruction = "".join(c for c in instruction[:20] if c.isalnum() or c in (' ', '-', '_')).strip()
        report_filename = f"analysis_report_{safe_instruction}.md"
        report_path = analysis_path / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"分析报告已保存至: {report_path}")
        return str(report_path)

class SummarizeAnalysis(Action):
    """将分析结果总结成报告"""
    async def run(self, analysis_result: str) -> str:
        """将分析结果总结成Markdown报告"""
        prompt = SUMMARIZE_ANALYSIS_PROMPT.format(analysis_result=analysis_result)
        report = await self.llm.aask(prompt)
        return report.strip()

