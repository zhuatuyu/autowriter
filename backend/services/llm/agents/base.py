"""
基于MetaGPT Role的Agent基类
使用我们自定义的记忆和消息系统，避免原生依赖问题
"""
import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.actions import Action
from metagpt.logs import logger

# 统一记忆系统导入将在_setup_memory_system中动态处理


# Agent信息配置
AGENT_INFO = {
    'director': {
        'name': '智能项目总监',
        'type': 'director',
        'avatar': '🎯',
        'description': '负责项目协调和客户沟通'
    },
    'document_expert': {
        'name': '文档专家（李心悦）',
        'type': 'document_expert', 
        'avatar': '📄',
        'description': '负责文档管理和格式化'
    },
    'case_expert': {
        'name': '案例专家（王磊）',
        'type': 'case_expert',
        'avatar': '🔍', 
        'description': '负责案例搜索和分析'
    },
    'data_analyst': {
        'name': '数据分析师（赵丽娅）',
        'type': 'data_analyst',
        'avatar': '📊',
        'description': '负责统计分析和可视化'
    },
    'writer_expert': {
        'name': '写作专家（张翰）',
        'type': 'writer_expert',
        'avatar': '✍️',
        'description': '负责报告撰写'
    },
    'chief_editor': {
        'name': '总编辑（钱敏）',
        'type': 'chief_editor',
        'avatar': '👔',
        'description': '负责最终审核和润色'
    }
}


class BaseAgentAction(Action):
    """基础Agent动作"""
    
    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务的基础方法，子类需要重写"""
        return {
            'status': 'completed',
            'result': '任务完成',
            'agent_id': self.name
        }


class BaseAgent(Role):
    """基于MetaGPT Role的Agent基类"""
    
    def __init__(self, agent_id: str, session_id: str, workspace_path: str, memory_manager=None, **kwargs):
        # 提取MetaGPT Role需要的参数
        profile = kwargs.pop('profile', 'Agent')
        goal = kwargs.pop('goal', '协助完成报告写作任务')
        constraints = kwargs.pop('constraints', '遵循专业标准，确保质量')
        
        # 使用MetaGPT的Role初始化
        super().__init__(
            name=agent_id,
            profile=profile,
            goal=goal,
            constraints=constraints,
            **kwargs  # 传递剩余的参数
        )
        
        self.agent_id = agent_id
        self.session_id = session_id
        self.agent_workspace = Path(workspace_path)
        
        # 统一记忆系统
        self._unified_memory_manager = memory_manager
        
        # Agent状态
        self.status = 'idle'  # idle, working, completed, error
        self.current_task = None
        self.progress = 0
        self.workspace_files = []
        
        # 创建工作目录
        self.agent_workspace.mkdir(parents=True, exist_ok=True)
        
        # 使用统一记忆系统（如果可用）
        self._setup_memory_system()
        
        # 恢复记忆，传递工作空间路径
        self._recover_memory()
        
        # 设置基础动作
        self.set_actions([BaseAgentAction])
    
    def _setup_memory_system(self):
        """设置记忆系统 - 优先使用统一记忆，回退到自定义记忆"""
        try:
            # 检查是否有统一记忆管理器传入
            if self._unified_memory_manager:
                # 获取适配器
                self._memory_adapter = self._unified_memory_manager.get_adapter(self.agent_id)
                
                # 注册Agent信息
                agent_info = AGENT_INFO.get(self.agent_id, {})
                agent_info.update({
                    'profile': self.profile,
                    'goal': self.goal,
                    'constraints': self.constraints,
                    'session_id': self.session_id
                })
                self._memory_adapter.register_agent(agent_info)
                
                # 使用统一记忆系统，创建一个简单的兼容记忆对象
                from metagpt.memory import Memory
                self.rc.memory = Memory()
                self._use_unified_memory = True
                
                logger.info(f"✅ {self.name} 已启用统一记忆系统")
            else:
                raise ImportError("未提供统一记忆管理器，无法初始化记忆系统。")
            
        except Exception as e:
            # 回退到原有的自定义记忆系统
            logger.warning(f"⚠️ {self.name} 统一记忆系统初始化失败，将使用无记忆模式: {e}")
            # 确保即使失败也有一个memory对象
            from metagpt.memory import Memory
            self.rc.memory = Memory()
            self._use_unified_memory = False
            self._memory_adapter = None
    
    def _recover_memory(self):
        """恢复Agent的历史记忆"""
        try:
            # 使用MetaGPT的记忆恢复机制，传递工作空间路径
            if hasattr(self.rc.memory, 'recover_memory'):
                self.rc.memory.recover_memory(self.agent_id, self.rc, self.agent_workspace)
                logger.info(f"🧠 {self.name} 记忆恢复完成")
            
            # 从工作空间加载历史状态
            self._load_workspace_state()
            
        except Exception as e:
            logger.error(f"❌ {self.name} 记忆恢复失败: {e}")
    
    def _load_workspace_state(self):
        """从工作空间加载历史状态"""
        try:
            state_file = self.agent_workspace / "agent_state.json"
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    self.status = state_data.get('status', 'idle')
                    self.progress = state_data.get('progress', 0)
                    logger.info(f"📋 {self.name} 恢复工作状态: {self.status}")
        except Exception as e:
            logger.warning(f"⚠️ {self.name} 加载工作状态失败: {e}")
    
    def _save_workspace_state(self):
        """保存工作状态到工作空间"""
        try:
            state_file = self.agent_workspace / "agent_state.json"
            state_data = {
                'agent_id': self.agent_id,
                'status': self.status,
                'progress': self.progress,
                'current_task': self.current_task,
                'last_updated': datetime.now().isoformat()
            }
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ {self.name} 保存工作状态失败: {e}")
    
    def record_work_memory(self, task_description: str, result: str, importance: str = "normal"):
        """记录工作记忆到记忆系统"""
        try:
            # 如果使用统一记忆系统
            if self._use_unified_memory and self._memory_adapter:
                self._memory_adapter.add_simple_message(
                    content=f"任务: {task_description}\n结果: {result}",
                    role=f"{self.name}({self.profile})",
                    cause_by=f"{self.agent_id}_work_memory"
                )
            else:
                # 使用原有的记忆系统
                work_msg = Message(
                    content=f"任务: {task_description}\n结果: {result}",
                    role=self.profile,
                    cause_by=BaseAgentAction,
                    sent_from=self.name
                )
                
                # 添加到记忆中
                self.rc.memory.add(work_msg)
                
                # 如果有长期记忆，持久化
                if hasattr(self.rc.memory, 'persist'):
                    self.rc.memory.persist()
                
            logger.info(f"💾 {self.name} 记录工作记忆: {task_description[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ {self.name} 记录工作记忆失败: {e}")
    
    def get_relevant_memories(self, keyword: str) -> List[Message]:
        """获取相关记忆"""
        try:
            return self.rc.memory.try_remember(keyword)
        except Exception as e:
            logger.error(f"❌ {self.name} 获取相关记忆失败: {e}")
            return []
    
    def get_work_context(self) -> str:
        """获取工作上下文"""
        try:
            # 如果使用统一记忆系统
            if self._use_unified_memory and self._memory_adapter:
                recent_memories = self._memory_adapter.get_recent_memory(5)
                
                if not recent_memories:
                    return f"{self.name} 暂无历史工作记录"
                
                context = f"=== {self.name} 的工作记忆 ===\n"
                for memory in recent_memories:
                    content = memory.get('content', '')
                    context += f"• {content[:100]}...\n"
                
                # 添加共享上下文信息
                shared_context = self._memory_adapter.get_shared_context()
                if shared_context:
                    context += f"\n=== 团队共享信息 ===\n"
                    for key, value in shared_context.items():
                        if key.startswith(self.agent_id):
                            context += f"• {key}: {str(value)[:50]}...\n"
                
                return context
            else:
                # 使用原有的记忆系统
                recent_memories = self.rc.memory.get(k=5)
                
                if not recent_memories:
                    return f"{self.name} 暂无历史工作记录"
                
                context = f"=== {self.name} 的工作记忆 ===\n"
                for memory in recent_memories:
                    context += f"• {memory.content[:100]}...\n"
                
                return context
            
        except Exception as e:
            logger.error(f"❌ {self.name} 获取工作上下文失败: {e}")
            return f"{self.name} 工作上下文获取失败"
    
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
        """执行任务的通用方法"""
        try:
            self.status = 'working'
            self.current_task = task.get('description', '执行任务')
            self.progress = 0
            
            # 保存状态
            self._save_workspace_state()
            
            # 获取历史上下文
            context = self.get_work_context()
            
            # 执行具体任务（子类重写）
            result = await self._execute_specific_task(task, context)
            
            # 记录工作记忆
            self.record_work_memory(
                task.get('description', '未知任务'),
                result.get('result', '任务完成')
            )
            
            # 更新状态
            self.status = 'completed'
            self.progress = 100
            self._save_workspace_state()
            
            return result
            
        except Exception as e:
            self.status = 'error'
            self._save_workspace_state()
            logger.error(f"❌ {self.name} 执行任务失败: {e}")
            return {
                'agent_id': self.agent_id,
                'status': 'error',
                'result': f'任务执行失败: {str(e)}',
                'error': str(e)
            }
    
    async def _execute_specific_task(self, task: Dict[str, Any], context: str) -> Dict[str, Any]:
        """执行具体任务，子类需要重写此方法"""
        return {
            'agent_id': self.agent_id,
            'status': 'completed',
            'result': f'{self.name} 已完成任务: {task.get("description", "未知任务")}',
        }
    
    def get_team_context(self) -> Dict[str, Any]:
        """获取团队上下文信息（仅在统一记忆系统中可用）"""
        try:
            if self._use_unified_memory and self._memory_adapter:
                return self._memory_adapter.get_team_summary()
            else:
                return {"message": "团队上下文仅在统一记忆系统中可用"}
        except Exception as e:
            logger.error(f"❌ {self.name} 获取团队上下文失败: {e}")
            return {"error": str(e)}
    
    def send_message_to_agent(self, target_agent_id: str, message: str):
        """发送消息给其他Agent（仅在统一记忆系统中可用）"""
        try:
            if self._use_unified_memory and self._memory_adapter:
                self._memory_adapter.send_message_to_agent(
                    target_agent_id, 
                    message, 
                    cause_by=f"{self.agent_id}_to_{target_agent_id}"
                )
                logger.info(f"📤 {self.name} 发送消息给 {target_agent_id}")
            else:
                logger.warning(f"⚠️ {self.name} 无法发送消息：需要统一记忆系统")
        except Exception as e:
            logger.error(f"❌ {self.name} 发送消息失败: {e}")
    
    def get_messages_from_agent(self, source_agent_id: str) -> List[Dict[str, Any]]:
        """获取来自特定Agent的消息（仅在统一记忆系统中可用）"""
        try:
            if self._use_unified_memory and self._memory_adapter:
                return self._memory_adapter.get_messages_from_agent(source_agent_id)
            else:
                logger.warning(f"⚠️ {self.name} 无法获取消息：需要统一记忆系统")
                return []
        except Exception as e:
            logger.error(f"❌ {self.name} 获取消息失败: {e}")
            return []
    
    async def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        # 更新工作文件列表
        await self._update_workspace_files()
        
        # 获取Agent信息
        agent_info = AGENT_INFO.get(self.agent_id, {})
        
        # 获取记忆数量
        memory_count = 0
        if self._use_unified_memory and self._memory_adapter:
            memory_count = len(self._memory_adapter.get_memory())
        elif hasattr(self.rc.memory, 'count'):
            memory_count = self.rc.memory.count()
        
        return {
            'agent_id': self.agent_id,
            'name': agent_info.get('name', self.name),
            'role': self.profile,
            'avatar': agent_info.get('avatar', '🤖'),
            'status': self.status,
            'current_task': self.current_task,
            'progress': self.progress,
            'workspace_files': self.workspace_files,
            'memory_count': memory_count,
            'memory_system': 'unified' if self._use_unified_memory else 'custom',
            'work_context': self.get_work_context()[:200] + "..." if len(self.get_work_context()) > 200 else self.get_work_context()
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


# Agent工厂函数
def create_agent(agent_id: str, session_id: str, workspace_path: str) -> BaseAgent:
    """根据Agent ID创建对应的Agent实例"""
    from .document_expert import DocumentExpertAgent
    from .case_expert import CaseExpertAgent
    from .director import IntelligentDirectorAgent
    from .writer_expert import WriterExpertAgent
    from .data_analyst import DataAnalystAgent
    from .chief_editor import ChiefEditorAgent
    
    agent_type = AGENT_INFO.get(agent_id, {}).get('type', 'base')
    
    if agent_type == 'document_expert':
        return DocumentExpertAgent(agent_id, session_id, workspace_path)
    elif agent_type == 'case_expert':
        return CaseExpertAgent(agent_id, session_id, workspace_path)
    elif agent_type == 'director':
        return IntelligentDirectorAgent(session_id, workspace_path)
    elif agent_type == 'writer_expert':
        return WriterExpertAgent(agent_id, session_id, workspace_path)
    elif agent_type == 'data_analyst':
        return DataAnalystAgent(agent_id, session_id, workspace_path)
    elif agent_type == 'chief_editor':
        return ChiefEditorAgent(agent_id, session_id, workspace_path)
    else:
        return BaseAgent(agent_id, session_id, workspace_path)