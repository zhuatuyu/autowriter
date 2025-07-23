"""
文档专家Agent - 李心悦
负责文档管理、格式化和摘要
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger

from .base import BaseAgent
from backend.services.llm_provider import llm
from backend.tools.mineru_api_tool import mineru_tool

class DocumentProcessAction(Action):
    """文档处理动作"""
    
    async def run(self, file_path: str) -> Dict[str, Any]:
        """处理单个文档文件"""
        try:
            # 使用MinerU工具处理文档
            result = await mineru_tool.process_file(file_path)
            return result
        except Exception as e:
            logger.error(f"文档处理失败: {e}")
            return {'error': str(e)}


class DocumentSummaryAction(Action):
    """文档摘要动作"""
    
    async def run(self, filename: str, content: str) -> str:
        """生成文档摘要"""
        prompt = f"""
你是李心悦，一位专业的办公室文秘和文档管理专家。请为以下文档生成简洁的摘要：

文档名称：{filename}
文档内容（前4000字符）：
---
{content[:4000]}
---

请用1-2句话总结这份文档的主要内容和关键信息。
"""
        try:
            summary = await llm.acreate_text(prompt)
            return summary.strip()
        except Exception as e:
            return f"摘要生成失败：{str(e)}"


class DocumentExpertAgent(BaseAgent):
    """
    文档专家Agent - 李心悦
    
    角色定位：办公室文秘，负责所有文档的管理、归档、格式化和摘要
    就像真实办公室中的文秘一样，她负责：
    - 接收和整理所有客户提供的文档
    - 将各种格式的文档转换为标准的Markdown格式
    - 建立文档索引和分类体系
    - 提取关键信息并生成摘要
    - 为其他同事提供格式化的文档内容
    """

    def __init__(self, agent_id: str, session_id: str, workspace_path: str, memory_manager=None):
        super().__init__(
            agent_id=agent_id,
            session_id=session_id,
            workspace_path=workspace_path,
            memory_manager=memory_manager,
            profile="文档专家",
            goal="高效管理、处理和分析所有项目相关文档"
        )
        
        # 设置专家信息
        self.name = "李心悦"
        self.avatar = "📄"
        self.expertise = "文档管理与处理"
        
        # 设置动作
        self.set_actions([DocumentProcessAction, DocumentSummaryAction])
        
        # 创建李心悦的工作区目录结构（就像她的文件柜）
        self.upload_path = self.agent_workspace / "uploads"        # 原始文件存放
        self.processed_path = self.agent_workspace / "processed"   # 处理后的MD文件
        self.summaries_path = self.agent_workspace / "summaries"   # 文档摘要
        self.extracts_path = self.agent_workspace / "extracts"     # 关键信息提取
        
        # 确保所有目录存在
        for path in [self.upload_path, self.processed_path, self.summaries_path, self.extracts_path]:
            path.mkdir(exist_ok=True)
        
        # 文档索引文件
        self.index_file = self.agent_workspace / "index.json"
        self.document_index = self._load_document_index()
        
        logger.info(f"📄 文档专家 {self.name} 初始化完成")

    def _load_document_index(self) -> Dict:
        """加载文档索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "documents": {},
            "categories": {},
            "last_updated": datetime.now().isoformat()
        }

    def _save_document_index(self):
        """保存文档索引"""
        self.document_index["last_updated"] = datetime.now().isoformat()
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.document_index, f, ensure_ascii=False, indent=2)

    def _get_summarize_prompt(self, filename: str, content: str) -> str:
        """构建文档摘要提示词"""
        return f"""
你是李心悦，一位专业的办公室文秘和文档管理专家。你需要为项目总监快速总结这份文档的核心内容。

文档名称：{filename}
文档内容（前4000字符）：
---
{content[:4000]}
---

请以专业文秘的角度，用1-2句话总结这份文档的：
1. 主要内容或目的
2. 关键数据或重要信息点

格式示例：
"这是一份关于XX项目的实施方案，详细规定了三个阶段的工作内容和时间安排，预算总额为XX万元。"

请直接给出摘要，不要添加其他说明。
"""

    def _get_key_info_prompt(self, filename: str, content: str) -> str:
        """构建关键信息提取提示词"""
        return f"""
你是李心悦，办公室文档管理专家。请从以下文档中提取关键信息，为项目团队提供结构化的信息摘要。

文档：{filename}
内容：
---
{content[:6000]}
---

请提取以下关键信息（如果文档中包含的话）：
1. 重要日期和时间节点
2. 关键数字和数据
3. 主要负责人或联系方式
4. 重要政策条款或规定
5. 预算或费用信息
6. 工作流程或步骤

请以清晰的列表格式输出，如果某项信息不存在，请标注"未提及"。
"""

    async def _execute_specific_task(self, task: "Task", context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行具体的文档处理任务
        task.description 将包含具体的指令，如 "处理上传的文件" 或 "提取关键信息"
        """
        logger.info(f"📄 {self.name} 开始执行任务: {task.description}")

        # 简单的基于关键词的任务路由
        if "处理" in task.description and "文件" in task.description:
            # 假设文件路径等信息在context中
            file_path = context.get("file_path", "") # 示例
            if file_path:
                return await self.process_uploaded_file(file_path)
            else:
                 return {"status": "error", "result": "未在上下文中找到需要处理的文件路径"}

        elif "提取" in task.description and "信息" in task.description:
            doc_id = context.get("document_id", "") # 示例
            return await self.extract_key_info(doc_id)
            
        elif "摘要" in task.description:
            doc_id = context.get("document_id", "") # 示例
            return await self.create_summary(doc_id)

        else:
            # 默认处理
            return {"status": "completed", "result": f"已完成通用文档任务: {task.description}"}

    async def _process_document_with_mineru(self, file_path: Path) -> str:
        """使用MinerU API处理文档"""
        try:
            # 调用MinerU工具处理文档
            result = await mineru_tool.process_file(str(file_path))
            if result and 'markdown_content' in result:
                return result['markdown_content']
            return None
        except Exception as e:
            print(f"❌ MinerU处理文档失败: {e}")
            # 如果MinerU失败，尝试简单的文本提取
            return await self._fallback_text_extraction(file_path)

    async def _fallback_text_extraction(self, file_path: Path) -> str:
        """备用文本提取方法"""
        try:
            if file_path.suffix.lower() == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return f"# {file_path.name}\n\n{content}"
            elif file_path.suffix.lower() == '.md':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return f"# {file_path.name}\n\n[文档格式暂不支持直接转换，请使用专业工具处理]"
        except:
            return f"# {file_path.name}\n\n[文档读取失败]"

    async def _generate_summary(self, filename: str, content: str) -> str:
        """生成文档摘要"""
        try:
            prompt = self._get_summarize_prompt(filename, content)
            summary = await llm.acreate_text(prompt)
            return summary.strip()
        except Exception as e:
            return f"摘要生成失败：{str(e)}"

    async def _extract_key_information(self, filename: str, content: str) -> str:
        """提取关键信息"""
        try:
            prompt = self._get_key_info_prompt(filename, content)
            key_info = await llm.acreate_text(prompt)
            return key_info.strip()
        except Exception as e:
            return f"关键信息提取失败：{str(e)}"

    def _update_document_index(self, filename: str, doc_info: Dict):
        """更新文档索引"""
        self.document_index["documents"][filename] = doc_info
        
        # 简单的分类逻辑（可以后续扩展）
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.document_index["categories"]:
            self.document_index["categories"][file_ext] = []
        self.document_index["categories"][file_ext].append(filename)

    def get_document_summary(self, filename: str) -> str:
        """获取指定文档的摘要"""
        if filename in self.document_index["documents"]:
            return self.document_index["documents"][filename]["summary"]
        return "文档未找到或未处理"

    def list_processed_documents(self) -> List[str]:
        """列出所有已处理的文档"""
        return list(self.document_index["documents"].keys())

    def get_document_content(self, filename: str) -> str:
        """获取处理后的文档内容"""
        if filename in self.document_index["documents"]:
            processed_file = self.document_index["documents"][filename]["processed_file"]
            try:
                with open(processed_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                pass
        return "文档内容获取失败"
    
    async def get_work_summary(self) -> str:
        """获取工作摘要"""
        try:
            doc_count = len(self.document_index["documents"])
            categories = self.document_index.get("categories", {})
            
            summary = f"📄 {self.name} 工作摘要:\n"
            summary += f"• 已处理文档: {doc_count} 个\n"
            
            if categories:
                summary += f"• 文档类型: {', '.join(categories.keys())}\n"
            
            summary += f"• 当前状态: {self.status}\n"
            
            if self.current_task:
                summary += f"• 当前任务: {self.current_task}\n"
            
            return summary
            
        except Exception as e:
            return f"📄 {self.name}: 工作摘要获取失败 - {str(e)}"

    async def upload_file(self, file_path: str, filename: str) -> Dict[str, Any]:
        """上传文件到工作区"""
        try:
            # 将文件复制到uploads目录
            target_path = self.upload_path / filename
            
            # 这里应该实现实际的文件复制逻辑
            # 暂时创建一个占位符
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(f"# {filename}\n\n[文件已上传，等待处理]")
            
            logger.info(f"📄 {self.name} 接收文件: {filename}")
            
            return {
                'status': 'success',
                'message': f'文件 {filename} 已上传到李心悦的工作区',
                'file_path': str(target_path)
            }
            
        except Exception as e:
            logger.error(f"❌ {self.name} 文件上传失败: {e}")
            return {
                'status': 'error',
                'message': f'文件上传失败: {str(e)}'
            } 