"""
简化的Agent基类
大幅减少原有服务的代码复杂度
"""
import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


class BaseAgent:
    """简化的Agent基类"""
    
    def __init__(self, agent_id: str, session_id: str, workspace_path: str):
        self.agent_id = agent_id
        self.session_id = session_id
        self.agent_workspace = Path(workspace_path)
        
        # 默认属性，子类应重写这些
        self.name = agent_id
        self.role = 'Agent'
        self.avatar = '🤖'
        
        # Agent状态
        self.status = 'idle'  # idle, working, completed, error
        self.current_task = None
        self.progress = 0
        self.workspace_files = []
        
        # 创建工作目录
        self.agent_workspace.mkdir(parents=True, exist_ok=True)
    
    async def assign_task(self, task: Dict[str, Any]) -> bool:
        """分配任务给Agent"""
        try:
            self.current_task = task.get('description', '执行任务')
            self.status = 'working'
            self.progress = 0
            
            # 保存任务信息
            await self._save_task_info(task)
            
            return True
        except Exception as e:
            print(f"❌ {self.name} 任务分配失败: {e}")
            self.status = 'error'
            return False
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务 - 子类需要重写此方法"""
        try:
            self.status = 'working'
            
            # 模拟工作进度
            for i in range(0, 101, 20):
                self.progress = i
                await asyncio.sleep(0.5)  # 模拟工作时间
            
            # 生成结果
            result = {
                'agent_id': self.agent_id,
                'agent_name': self.name,
                'task': task,
                'status': 'completed',
                'result': f"{self.name} 已完成任务: {task.get('description', '未知任务')}",
                'files_created': [],
                'timestamp': datetime.now().isoformat()
            }
            
            self.status = 'completed'
            self.progress = 100
            
            # 保存结果
            await self._save_result(result)
            
            return result
            
        except Exception as e:
            print(f"❌ {self.name} 任务执行失败: {e}")
            self.status = 'error'
            return {
                'agent_id': self.agent_id,
                'agent_name': self.name,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        # 更新工作文件列表
        await self._update_workspace_files()
        
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'role': self.role,
            'avatar': self.avatar,
            'status': self.status,
            'current_task': self.current_task,
            'progress': self.progress,
            'workspace_files': self.workspace_files
        }
    
    async def _save_task_info(self, task: Dict[str, Any]):
        """保存任务信息到工作目录"""
        task_file = self.agent_workspace / 'current_task.json'
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump({
                'task': task,
                'assigned_at': datetime.now().isoformat(),
                'status': self.status
            }, f, ensure_ascii=False, indent=2)
    
    async def _save_result(self, result: Dict[str, Any]):
        """保存任务结果"""
        result_file = self.agent_workspace / f'result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    
    async def _update_workspace_files(self):
        """更新工作文件列表"""
        try:
            files = []
            for file_path in self.agent_workspace.iterdir():
                if file_path.is_file():
                    files.append(file_path.name)
            self.workspace_files = sorted(files)
        except Exception as e:
            print(f"⚠️ 更新 {self.name} 工作文件列表失败: {e}")
            self.workspace_files = []


class WriterAgent(BaseAgent):
    """写作专家Agent"""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行写作任务"""
        try:
            self.status = 'working'
            chapter = task.get('chapter', '未知章节')
            content = task.get('content', '')
            
            # 模拟写作过程
            self.current_task = f"正在撰写：{chapter}"
            
            for i in range(0, 101, 10):
                self.progress = i
                await asyncio.sleep(0.3)
            
            # 生成写作内容
            draft_content = f"""# {chapter}

{content}

## 主要内容

根据项目要求和相关资料，本章节主要包含以下内容：

1. 背景分析
2. 现状描述  
3. 问题识别
4. 改进建议

*本内容由写作专家 {self.name} 撰写*
*撰写时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            # 保存草稿
            draft_file = self.agent_workspace / f'{chapter.replace("、", "_")}.md'
            with open(draft_file, 'w', encoding='utf-8') as f:
                f.write(draft_content)
            
            result = {
                'agent_id': self.agent_id,
                'agent_name': self.name,
                'task': task,
                'status': 'completed',
                'result': f"已完成 {chapter} 的撰写",
                'files_created': [draft_file.name],
                'content': draft_content,
                'timestamp': datetime.now().isoformat()
            }
            
            self.status = 'completed'
            self.progress = 100
            await self._save_result(result)
            
            return result
            
        except Exception as e:
            print(f"❌ {self.name} 写作任务失败: {e}")
            self.status = 'error'
            return {
                'agent_id': self.agent_id,
                'agent_name': self.name,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


class DocumentAgent(BaseAgent):
    """文档专家Agent"""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行文档整理任务"""
        try:
            self.status = 'working'
            self.current_task = "整理项目文档和资料"
            
            # 模拟文档整理过程
            documents = [
                "项目基础资料.docx",
                "政策法规汇总.pdf", 
                "数据统计表.xlsx",
                "参考模板.docx"
            ]
            
            for i, doc in enumerate(documents):
                self.progress = int((i + 1) / len(documents) * 100)
                
                # 创建模拟文档
                doc_file = self.agent_workspace / doc
                with open(doc_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {doc}\n\n这是由文档专家 {self.name} 整理的 {doc}\n\n整理时间：{datetime.now()}")
                
                await asyncio.sleep(0.5)
            
            result = {
                'agent_id': self.agent_id,
                'agent_name': self.name,
                'task': task,
                'status': 'completed',
                'result': f"已整理 {len(documents)} 个项目文档",
                'files_created': documents,
                'timestamp': datetime.now().isoformat()
            }
            
            self.status = 'completed'
            await self._save_result(result)
            
            return result
            
        except Exception as e:
            print(f"❌ {self.name} 文档整理失败: {e}")
            self.status = 'error'
            return {
                'agent_id': self.agent_id,
                'agent_name': self.name,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


class CaseAgent(BaseAgent):
    """案例专家Agent"""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行案例搜索任务"""
        try:
            self.status = 'working'
            self.current_task = "搜索相关案例和最佳实践"
            
            # 模拟案例搜索
            cases = [
                "某市绩效评价成功案例",
                "政策实施效果评估案例",
                "行业最佳实践案例"
            ]
            
            for i, case in enumerate(cases):
                self.progress = int((i + 1) / len(cases) * 100)
                
                case_content = f"""# {case}

## 案例背景
{case} 的详细背景信息...

## 实施过程
具体的实施步骤和方法...

## 取得成效
实施后取得的具体成效...

## 经验启示
可借鉴的经验和做法...

*案例整理：{self.name}*
*整理时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
                
                case_file = self.agent_workspace / f'{case}.md'
                with open(case_file, 'w', encoding='utf-8') as f:
                    f.write(case_content)
                
                await asyncio.sleep(0.4)
            
            result = {
                'agent_id': self.agent_id,
                'agent_name': self.name,
                'task': task,
                'status': 'completed',
                'result': f"已搜索整理 {len(cases)} 个相关案例",
                'files_created': [f'{case}.md' for case in cases],
                'timestamp': datetime.now().isoformat()
            }
            
            self.status = 'completed'
            await self._save_result(result)
            
            return result
            
        except Exception as e:
            print(f"❌ {self.name} 案例搜索失败: {e}")
            self.status = 'error'
            return {
                'agent_id': self.agent_id,
                'agent_name': self.name,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Agent工厂函数
def create_agent(agent_id: str, session_id: str, workspace_path: str) -> BaseAgent:
    """根据Agent ID创建对应的Agent实例"""
    agent_type = AGENT_INFO.get(agent_id, {}).get('type', 'base')
    
    if agent_type == 'writer_expert':
        return WriterAgent(agent_id, session_id, workspace_path)
    elif agent_type == 'document_expert':
        return DocumentAgent(agent_id, session_id, workspace_path)
    elif agent_type == 'case_expert':
        return CaseAgent(agent_id, session_id, workspace_path)
    else:
        return BaseAgent(agent_id, session_id, workspace_path)