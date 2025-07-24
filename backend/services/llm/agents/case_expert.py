"""
🔍 案例专家（王磊） - 虚拟办公室的研究员
负责搜索相关案例和最佳实践，为报告提供参考依据
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger

from backend.services.llm.agents.base import BaseAgent
from backend.tools.alibaba_search import AlibabaSearchTool
# 导入新的摘要工具
from backend.tools.summary_tool import summary_tool

# 导入新的Prompt模块
from backend.services.llm.prompts import case_expert_prompts


class CaseSearchAction(Action):
    """案例搜索动作"""
    
    async def run(self, query: str) -> str:
        """执行案例搜索"""
        try:
            # 使用阿里巴巴搜索工具
            search_results = await self.search_tool.search(query)
            return search_results
        except Exception as e:
            logger.error(f"案例搜索失败: {e}")
            return f"搜索失败: {str(e)}"


class CaseAnalysisAction(Action):
    """案例分析动作"""
    
    async def run(self, cases: List[str]) -> str:
        """分析案例并提取关键信息"""
        analysis = "# 案例分析报告\n\n"
        
        for i, case in enumerate(cases, 1):
            analysis += f"## 案例 {i}\n\n"
            analysis += f"**内容**: {case[:200]}...\n\n"
            analysis += f"**关键要点**: \n"
            analysis += f"- 实施背景\n"
            analysis += f"- 主要做法\n" 
            analysis += f"- 取得成效\n"
            analysis += f"- 经验启示\n\n"
        
        return analysis


class CaseExpertAgent(BaseAgent):
    """
    🔍 案例专家（王磊） - 虚拟办公室的研究员
    """
    def __init__(self, agent_id: str, session_id: str, workspace_path: str, memory_manager=None):
        super().__init__(
            agent_id=agent_id,
            session_id=session_id,
            workspace_path=workspace_path,
            memory_manager=memory_manager,
            profile="案例专家",
            goal="搜索、分析和提供与项目相关的案例与最佳实践"
        )
        
        # 初始化案例搜索工具
        self.search_tool = AlibabaSearchTool()
        
        # 设置专家信息
        self.name = "王磊"
        self.avatar = "🔍"
        self.expertise = "案例搜索与分析"
        
        # 设置动作
        self.set_actions([CaseSearchAction, CaseAnalysisAction])
        
        # 创建专门的工作目录
        self.searches_dir = self.agent_workspace / "searches"
        self.cases_dir = self.agent_workspace / "cases"
        self.searches_dir.mkdir(exist_ok=True)
        self.cases_dir.mkdir(exist_ok=True)
        
        logger.info(f"🔍 案例专家 {self.name} 初始化完成")


    async def _execute_specific_task_with_messages(self, task: "Task", history_messages: List[Message]) -> Dict[str, Any]:
        """
        使用MetaGPT标准的Message历史执行案例研究任务
        """
        logger.info(f"🔍 {self.name} 开始执行任务: {task.description}")

        # 从任务描述中提取查询关键词 (简化处理)
        query = task.description.replace("研究", "").replace("搜索", "").replace("案例", "").replace("关于", "").replace("和相关", "").strip()

        try:
            # 统一调用搜索逻辑
            search_task_payload = {"query": query}
            search_result_dict = await self._search_cases(search_task_payload)

            # 检查子任务执行状态
            if search_result_dict.get("status") != "completed":
                 return search_result_dict # 直接返回带有错误信息的字典

            # 成功后，将结果格式化以符合新架构的期望
            # 关键：确保将 `content` 传递下去
            return {
                "status": "completed",
                "result": {
                    "message": f"关于 '{query}' 的案例研究已完成。",
                    "files_created": search_result_dict.get("files_created", []),
                    "content": search_result_dict.get("content", "") # 从搜索结果中提取content
                }
            }

        except Exception as e:
            error_msg = f"❌ 执行案例研究时出错: {e}"
            logger.error(error_msg, exc_info=True)
            return {"status": "error", "result": error_msg}

    async def _search_cases(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据给定的精确查询，执行单次网络搜索并保存结果。
        不再进行自作聪明的二次查询扩展。
        """
        try:
            query = task.get('query')
            if not query:
                raise ValueError("搜索任务必须包含'query'字段")
            
            self.current_task = f"正在搜索: {query}"
            self.progress = 10
            
            logger.info(f"🔍 {self.name} 正在执行精确搜索: {query}")
            
            # 执行单次精确搜索
            search_results_text = await self.search_tool.run(query)
            self.progress = 80

            # 保存单次搜索结果
            # 文件名使用查询内容，并进行安全处理
            safe_query_filename = "".join(c if c.isalnum() else '_' for c in query)[:50]
            result_file = self.searches_dir / f"search_{safe_query_filename}_{datetime.now().strftime('%H%M%S')}.md"
            
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(f"# 搜索结果: {query}\n\n")
                f.write(f"**搜索时间**: {datetime.now().strftime('%Y-%m-%d %H:%M%S')}\n\n")
                f.write(f"**搜索内容**:\n\n{search_results_text}\n\n")
                f.write(f"---\n*搜索执行: {self.name}*")
            
            files_created = [result_file.name]
            
            # (可选) 如果未来需要，可以在这里调用SummaryTool对单次结果做个快速摘要
            # summary = await summary_tool.run(search_results_text)
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成对 '{query}' 的搜索，结果已保存。",
                'files_created': files_created,
                'search_query': query,
                'content': search_results_text, # 将原始搜索结果内容也返回，便于后续任务直接使用
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 案例搜索失败: {e}", exc_info=True)
            return {
                'agent_id': self.agent_id,
                'status': 'error',
                'result': f"案例搜索失败: {e}",
            }

    async def _analyze_cases(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """分析已搜索的案例"""
        try:
            self.current_task = "正在分析案例内容"
            self.progress = 10
            
            # 读取已有的搜索结果
            search_files = list(self.searches_dir.glob("*.md"))
            if not search_files:
                return {
                    'agent_id': self.agent_id,
                    'status': 'completed',
                    'result': "暂无案例文件可供分析，请先执行案例搜索",
                    'files_created': []
                }
            
            cases_content = []
            for file_path in search_files[:5]:  # 分析最近的5个文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    cases_content.append(content)
            
            self.progress = 50
            
            # 执行案例分析
            analysis_action = CaseAnalysisAction()
            analysis_result = await analysis_action.run(cases_content)
            
            # 保存分析结果
            analysis_file = self.cases_dir / f"case_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write(f"# 案例分析报告\n\n")
                f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**分析专家**: {self.name}\n")
                f.write(f"**分析文件数**: {len(cases_content)}\n\n")
                f.write(analysis_result)
                f.write(f"\n\n---\n*分析完成: {self.name} 🔍*")
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成 {len(cases_content)} 个案例文件的分析",
                'files_created': [analysis_file.name],
                'analysis_summary': analysis_result[:300] + "..." if len(analysis_result) > 300 else analysis_result,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 案例分析失败: {e}")
            raise

    async def _compile_best_practices(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """整理最佳实践"""
        try:
            self.current_task = "正在整理最佳实践"
            self.progress = 10
            
            # 读取分析结果
            analysis_files = list(self.cases_dir.glob("case_analysis_*.md"))
            
            best_practices = "# 最佳实践汇编\n\n"
            best_practices += f"**整理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            best_practices += f"**整理专家**: {self.name}\n\n"
            
            if analysis_files:
                for file_path in analysis_files[-3:]:  # 使用最近的3个分析文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        best_practices += f"## 来源: {file_path.name}\n\n"
                        best_practices += content + "\n\n"
            else:
                best_practices += "## 通用最佳实践\n\n"
                best_practices += "1. **明确目标导向**: 确保评价指标与目标紧密对应\n"
                best_practices += "2. **数据驱动决策**: 基于客观数据进行评价分析\n"
                best_practices += "3. **多维度评估**: 从不同角度全面评价绩效\n"
                best_practices += "4. **持续改进机制**: 建立反馈和改进循环\n"
                best_practices += "5. **利益相关方参与**: 确保各方意见得到充分考虑\n\n"
            
            self.progress = 80
            
            # 保存最佳实践
            practices_file = self.cases_dir / f"best_practices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(practices_file, 'w', encoding='utf-8') as f:
                f.write(best_practices)
                f.write(f"\n\n---\n*整理完成: {self.name} 🔍*")
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成最佳实践整理，基于 {len(analysis_files)} 个分析文件",
                'files_created': [practices_file.name],
                'practices_summary': best_practices[:300] + "..." if len(best_practices) > 300 else best_practices,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 最佳实践整理失败: {e}")
            raise
    
    # _generate_search_summary 方法可以暂时移除或注释，因为总结任务将由Director明确下发
    # 并在新的、专门的总结任务中调用summary_tool
    # async def _generate_search_summary(self, search_results: List[Dict]) -> str:
    #    ...

    async def get_work_summary(self) -> str:
        """获取工作摘要"""
        try:
            search_count = len(list(self.searches_dir.glob("*.md")))
            analysis_count = len(list(self.cases_dir.glob("case_analysis_*.md")))
            practices_count = len(list(self.cases_dir.glob("best_practices_*.md")))
            
            summary = f"🔍 {self.name} 工作摘要:\n"
            summary += f"• 已执行搜索: {search_count} 次\n"
            summary += f"• 完成分析: {analysis_count} 份\n"
            summary += f"• 整理实践: {practices_count} 份\n"
            summary += f"• 当前状态: {self.status}\n"
            
            if self.current_task:
                summary += f"• 当前任务: {self.current_task}\n"
            
            return summary
            
        except Exception as e:
            return f"🔍 {self.name}: 工作摘要获取失败 - {str(e)}" 