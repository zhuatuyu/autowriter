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


    async def _execute_specific_task(self, task: "Task", context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行具体的案例研究任务
        task.description 会包含需要研究的主题或关键词
        """
        logger.info(f"🔍 {self.name} 开始执行任务: {task.description}")

        # 从任务描述中提取查询关键词 (简化处理)
        query = task.description.replace("研究", "").replace("搜索", "").replace("案例", "").strip()

        try:
            # 统一调用旧的、带文件保存的搜索逻辑
            search_task_payload = {"keywords": query.split(), "domain": "综合领域"}
            search_result_dict = await self._search_cases(search_task_payload)

            # 检查执行状态
            if search_result_dict.get("status") != "completed":
                 return {
                    "status": "error",
                    "result": search_result_dict.get("result", "案例搜索失败，详情未知。")
                }

            # 成功后，将结果格式化以符合新架构的期望
            return {
                "status": "completed",
                "result": {
                    "message": f"关于 '{query}' 的案例研究已完成。",
                    "summary": search_result_dict.get("summary", "无摘要"),
                    "files_created": search_result_dict.get("files_created", []),
                }
            }

        except Exception as e:
            error_msg = f"❌ 执行案例研究时出错: {e}"
            logger.error(error_msg, exc_info=True)
            return {"status": "error", "result": error_msg}

    async def _search_cases(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """搜索相关案例"""
        try:
            keywords = task.get('keywords', ['绩效评价', '案例'])
            domain = task.get('domain', '政府绩效')
            
            self.current_task = f"正在搜索 {domain} 相关案例"
            self.progress = 10
            
            # 构建搜索查询
            queries = [
                f"{domain} 成功案例",
                f"{' '.join(keywords)} 最佳实践",
                f"{domain} 实施经验",
                f"{' '.join(keywords)} 典型做法"
            ]
            
            all_results = []
            files_created = []
            
            for i, query in enumerate(queries):
                self.progress = 20 + (i * 20)
                logger.info(f"🔍 {self.name} 搜索: {query}")
                
                # 执行搜索 - 直接使用Agent自己的工具，不再创建临时的Action实例
                search_results = await self.search_tool.run(query)
                
                # 保存搜索结果
                result_file = self.searches_dir / f"search_{query.replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}.md"
                with open(result_file, 'w', encoding='utf-8') as f:
                    f.write(f"# 搜索结果: {query}\n\n")
                    f.write(f"**搜索时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(f"**搜索内容**:\n\n{search_results}\n\n")
                    f.write(f"---\n*搜索执行: {self.name}*")
                
                all_results.append({
                    'query': query,
                    'results': search_results,
                    'file': result_file.name
                })
                files_created.append(result_file.name)
                
                await asyncio.sleep(0.5)  # 避免请求过快
            
            # 生成搜索摘要
            self.progress = 90
            summary = await self._generate_search_summary(all_results)
            
            summary_file = self.cases_dir / f"search_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            files_created.append(summary_file.name)
            
            self.progress = 100
            
            result = {
                'agent_id': self.agent_id,
                'status': 'completed',
                'result': f"已完成 {domain} 相关案例搜索，共搜索 {len(queries)} 个关键词，生成 {len(files_created)} 个文件",
                'files_created': files_created,
                'search_queries': queries,
                'summary': summary, # 返回完整的摘要内容
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.name} 案例搜索失败: {e}")
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

    async def _generate_search_summary(self, search_results: List[Dict]) -> str:
        """生成搜索结果摘要"""
        summary = f"# 案例搜索摘要报告\n\n"
        summary += f"**搜索专家**: {self.name}\n"
        summary += f"**搜索时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        summary += f"**搜索查询数**: {len(search_results)}\n\n"
        
        summary += "## 搜索概览\n\n"
        for i, result in enumerate(search_results, 1):
            summary += f"{i}. **{result['query']}**\n"
            summary += f"   - 结果文件: {result['file']}\n"
            summary += f"   - 内容预览: {result['results'][:100]}...\n\n"
        
        summary += "## 主要发现\n\n"
        summary += "- 收集了多个相关案例和最佳实践\n"
        summary += "- 涵盖了不同领域的实施经验\n"
        summary += "- 为报告撰写提供了丰富的参考资料\n\n"
        
        summary += "## 后续建议\n\n"
        summary += "1. 对搜索结果进行深入分析\n"
        summary += "2. 提取关键成功因素\n"
        summary += "3. 整理可借鉴的经验做法\n"
        summary += "4. 为报告撰写提供案例支撑\n\n"
        
        return summary

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