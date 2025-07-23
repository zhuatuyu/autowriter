"""
数据分析师Agent - 赵丽娅
负责数据提取、分析和可视化
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import re # Added for regex in _execute_specific_task

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger

from .base import BaseAgent
from backend.services.llm_provider import llm


class DataExtractionAction(Action):
    """数据提取动作"""
    
    async def run(self, content: str, data_type: str = "数值数据") -> str:
        """从内容中提取数据"""
        prompt = f"""
你是数据分析师赵丽娅，请从以下内容中提取{data_type}：

内容：
{content}

请提取所有相关的数据，包括：
1. 数值数据（金额、百分比、数量等）
2. 时间数据（日期、期间等）
3. 分类数据（类别、等级等）

以结构化的格式输出，便于后续分析。
"""
        try:
            extracted_data = await llm.acreate_text(prompt)
            return extracted_data.strip()
        except Exception as e:
            logger.error(f"数据提取失败: {e}")
            return f"数据提取失败: {str(e)}"


class DataAnalysisAction(Action):
    """数据分析动作"""
    
    async def run(self, data: str, analysis_type: str = "趋势分析") -> str:
        """分析数据并生成报告"""
        prompt = f"""
你是专业的数据分析师赵丽娅，请对以下数据进行{analysis_type}：

数据：
{data}

请提供：
1. 数据概览和基本统计
2. 主要趋势和模式
3. 关键发现和洞察
4. 数据质量评估
5. 分析结论和建议

请用专业的数据分析语言，提供清晰的分析结果。
"""
        try:
            analysis_result = await llm.acreate_text(prompt)
            return analysis_result.strip()
        except Exception as e:
            logger.error(f"数据分析失败: {e}")
            return f"数据分析失败: {str(e)}"


class DataAnalystAgent(BaseAgent):
    """
    📊 数据分析师（赵丽娅） - 虚拟办公室的数据专家
    """
    def __init__(self, agent_id: str, session_id: str, workspace_path: str, memory_manager=None):
        super().__init__(
            agent_id=agent_id,
            session_id=session_id,
            workspace_path=workspace_path,
            memory_manager=memory_manager,
            profile="数据分析师",
            goal="进行数据收集、统计分析和可视化"
        )
        
        # 初始化数据分析工具
        self.analysis_tools = self._initialize_analysis_tools()
        
        # 设置专家信息
        self.name = "赵丽娅"
        self.avatar = "📊"
        self.expertise = "数据分析与可视化"
        
        # 设置动作
        self.set_actions([DataExtractionAction, DataAnalysisAction])
        
        # 创建专门的工作目录
        self.data_dir = self.agent_workspace / "data"
        self.charts_dir = self.agent_workspace / "charts"
        self.analysis_dir = self.agent_workspace / "analysis"
        
        for dir_path in [self.data_dir, self.charts_dir, self.analysis_dir]:
            dir_path.mkdir(exist_ok=True)
        
        logger.info(f"📊 数据分析师 {self.name} 初始化完成")
    
    def _initialize_analysis_tools(self) -> Dict[str, Any]:
        """初始化数据分析工具"""
        return {
            "statistical_analysis": {
                "description": "基础统计分析工具",
                "capabilities": ["均值计算", "标准差", "相关性分析", "趋势分析"]
            },
            "data_visualization": {
                "description": "数据可视化工具", 
                "capabilities": ["图表生成", "数据展示", "报告美化"]
            },
            "performance_metrics": {
                "description": "绩效指标分析工具",
                "capabilities": ["KPI分析", "目标达成率", "效率评估"]
            }
        }
    
    async def _execute_specific_task(self, task: "Task", context: Dict[str, Any]) -> Dict[str, Any]:
        """执行具体的数据分析任务"""
        logger.info(f"📊 {self.name} 开始执行任务: {task.description}")

        # 简单的基于关键词的任务路由
        if "提取" in task.description and "数据" in task.description:
            # 假设需要分析的内容在上下文中
            source_content = ""
            if context:
                # 尝试从上下文的任何来源提取内容
                for key, value in context.items():
                    if isinstance(value, dict) and 'result' in value:
                         # 优先使用上游任务的result字段
                        res = value['result']
                        if isinstance(res, dict) and 'content_preview' in res:
                            source_content = res['content_preview']
                            break
                        elif isinstance(res, str):
                            source_content = res
                            break
            
            if not source_content:
                return {"status": "error", "result": "未在上下文中找到可供提取数据的内容"}

            return await self._extract_data({"content": source_content, "data_type": "数值和关键信息"})

        elif "分析" in task.description and "数据" in task.description:
            # 假设数据在上下文中
            source_data = ""
            if context:
                 for key, value in context.items():
                    if isinstance(value, dict) and 'result' in value:
                        res = value['result']
                        if isinstance(res, dict) and 'extracted_data' in res:
                            source_data = res['extracted_data']
                            break
                        elif isinstance(res, str):
                            source_data = res
                            break
            
            if not source_data:
                return {"status": "error", "result": "未在上下文中找到可供分析的数据"}
            
            analysis_type_match = re.search(r"进行(.*?)分析", task.description)
            analysis_type = analysis_type_match.group(1).strip() if analysis_type_match else "综合"
            
            return await self._analyze_data({"data": source_data, "analysis_type": analysis_type})

        else:
            return {"status": "completed", "result": f"已完成通用数据任务: {task.description}"}

    async def _extract_data(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """提取数据"""
        try:
            content = task.get('content', '')
            data_type = task.get('data_type', '数值数据')
            
            self.current_task = f"正在提取{data_type}"
            self.progress = 10
            
            # 执行数据提取
            extraction_action = DataExtractionAction()
            extracted_data = await extraction_action.run(content, data_type)
            
            self.progress = 80
            
            # 保存提取结果
            data_file = self.data_dir / f"extracted_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(data_file, 'w', encoding='utf-8') as f:
                f.write(f"# 数据提取报告\n\n")
                f.write(f"**提取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**分析师**: {self.name}\n")
                f.write(f"**数据类型**: {data_type}\n\n")
                f.write(f"## 提取结果\n\n{extracted_data}\n\n")
                f.write(f"---\n*数据提取: {self.name} 📊*")
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成{data_type}的提取",
                'files_created': [data_file.name],
                'extracted_data': extracted_data, # 返回完整数据
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 数据提取失败: {e}")
            raise

    async def _analyze_data(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """分析数据"""
        try:
            data = task.get('data', '')
            analysis_type = task.get('analysis_type', '趋势分析')
            
            self.current_task = f"正在进行{analysis_type}"
            self.progress = 10
            
            # 如果没有提供数据，从已提取的数据中读取
            if not data:
                data_files = list(self.data_dir.glob("extracted_data_*.md"))
                if data_files:
                    with open(data_files[-1], 'r', encoding='utf-8') as f:
                        data = f.read()
                else:
                    return {
                        'agent_id': self.agent_id,
                        'status': 'completed',
                        'result': "暂无数据可供分析，请先执行数据提取",
                        'files_created': []
                    }
            
            self.progress = 30
            
            # 执行数据分析
            analysis_action = DataAnalysisAction()
            analysis_result = await analysis_action.run(data, analysis_type)
            
            self.progress = 80
            
            # 保存分析结果
            analysis_file = self.analysis_dir / f"analysis_{analysis_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write(f"# 数据分析报告 - {analysis_type}\n\n")
                f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**分析师**: {self.name}\n")
                f.write(f"**分析类型**: {analysis_type}\n\n")
                f.write(f"## 分析结果\n\n{analysis_result}\n\n")
                f.write(f"---\n*数据分析: {self.name} 📊*")
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成{analysis_type}",
                'files_created': [analysis_file.name],
                'analysis_summary': analysis_result, # 返回完整分析
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 数据分析失败: {e}")
            raise

    async def _generate_charts(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """生成图表"""
        try:
            self.current_task = "正在生成数据图表"
            self.progress = 10
            
            # 读取分析结果
            analysis_files = list(self.analysis_dir.glob("analysis_*.md"))
            
            if not analysis_files:
                return {
                    'agent_id': self.agent_id,
                    'status': 'completed',
                    'result': "暂无分析结果可供图表生成，请先执行数据分析",
                    'files_created': []
                }
            
            chart_files = []
            
            for analysis_file in analysis_files[-2:]:  # 为最近的2个分析生成图表
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    analysis_content = f.read()
                
                # 生成图表描述（实际项目中这里会生成真实图表）
                chart_description = f"""# 数据可视化图表

基于分析文件: {analysis_file.name}

## 建议图表类型

1. **趋势图**: 展示数据随时间的变化趋势
2. **柱状图**: 比较不同类别的数据
3. **饼图**: 展示数据的构成比例
4. **散点图**: 展示变量间的相关关系

## 图表说明

{analysis_content[:500]}...

*图表生成: {self.name} 📊*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
                
                chart_file = self.charts_dir / f"chart_{analysis_file.stem}.md"
                with open(chart_file, 'w', encoding='utf-8') as f:
                    f.write(chart_description)
                
                chart_files.append(chart_file.name)
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已生成 {len(chart_files)} 个数据图表",
                'files_created': chart_files,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 图表生成失败: {e}")
            raise

    async def get_work_summary(self) -> str:
        """获取工作摘要"""
        try:
            data_count = len(list(self.data_dir.glob("*.md")))
            analysis_count = len(list(self.analysis_dir.glob("*.md")))
            chart_count = len(list(self.charts_dir.glob("*.md")))
            
            summary = f"📊 {self.name} 工作摘要:\n"
            summary += f"• 数据提取: {data_count} 次\n"
            summary += f"• 完成分析: {analysis_count} 份\n"
            summary += f"• 生成图表: {chart_count} 个\n"
            summary += f"• 当前状态: {self.status}\n"
            
            if self.current_task:
                summary += f"• 当前任务: {self.current_task}\n"
            
            return summary
            
        except Exception as e:
            return f"📊 {self.name}: 工作摘要获取失败 - {str(e)}"