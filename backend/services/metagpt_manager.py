"""
MetaGPT 管理器 - 基于MetaGPT框架的多Agent协作系统
采用SOP模式和工具集成的最佳实践
"""
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import uuid
import threading
from queue import Queue

# MetaGPT核心导入
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.team import Team
from metagpt.actions import Action
from metagpt.memory import Memory
from metagpt.config2 import config
from metagpt.logs import logger
from metagpt.environment import Environment

from backend.models.session import WorkflowPhase
from backend.tools.alibaba_search import alibaba_search_tool
from backend.tools.report_template_analyzer import report_template_analyzer, ChapterInfo

class TemplateAnalysisAction(Action):
    """模板分析动作 - 分析报告模板并制定写作计划"""
    
    async def run(self, project_info: Dict, template_analyzer) -> str:
        """分析模板并制定写作计划"""
        try:
            template_summary = template_analyzer.get_template_summary()
            
            prompt = f"""作为模板分析专家，请分析以下报告模板并制定详细的写作计划：

## 项目信息
- 项目名称：{project_info.get('name', '未知项目')}
- 项目类型：{project_info.get('type', '绩效评价')}
- 预算规模：{project_info.get('budget', '待确定')}万元
- 资金来源：{project_info.get('funding_source', '财政资金')}

## 模板信息
- 模板名称：{template_summary['name']}
- 模板描述：{template_summary['description']}
- 总章节数：{template_summary['total_chapters']}
- 写作序列长度：{template_summary['writing_sequence_length']}

## 任务要求
1. 分析模板结构的合理性
2. 根据项目特点调整写作重点
3. 制定专家分工计划
4. 确定写作顺序和依赖关系
5. 识别需要重点关注的章节

请提供详细的分析结果和写作蓝图。"""

            # 这里应该调用LLM，暂时返回分析结果
            return f"""# 模板分析结果

## 模板结构分析
{template_summary['name']} 是一个结构完整的绩效评价报告模板，包含 {template_summary['total_chapters']} 个章节，按照标准的绩效评价流程设计。

## 写作蓝图
基于项目特点，建议按照以下顺序进行写作：
1. 首先完成项目概述部分，建立基础信息框架
2. 然后进行指标分析，构建评价体系
3. 最后完成综合评价和建议部分

## 专家分工建议
- 数据分析师：负责指标体系构建和数据分析
- 政策研究员：负责政策背景和合规性分析
- 案例研究员：负责同类项目案例研究
- 指标专家：负责评价标准制定
- 写作专员：负责内容整合和报告撰写
- 质量评审员：负责最终质量把控

模板分析完成，可以开始按章节顺序写作。"""
            
        except Exception as e:
            logger.error(f"模板分析失败: {e}")
            return f"模板分析出现错误：{str(e)}"

class ChapterWritingAction(Action):
    """章节写作动作 - 基于模板进行章节写作"""
    
    def __init__(self, role_type: str, **kwargs):
        super().__init__(**kwargs)
        self.role_type = role_type
        
    async def run(self, chapter: ChapterInfo, project_info: Dict, role_llm=None, search_results: str = "") -> str:
        """执行章节写作"""
        try:
            # 构建写作提示
            prompt = report_template_analyzer.get_chapter_writing_prompt(chapter, project_info)
            
            # 如果有搜索结果，添加到提示中
            if search_results:
                prompt += f"\n## 搜索资料参考\n{search_results}\n\n"
            
            prompt += f"\n请作为{self.role_type}，严格按照上述要求完成章节写作："
            
            if role_llm:
                response = await role_llm.aask(prompt)
                return response
            else:
                return f"[{self.role_type}] 正在撰写章节：{chapter.title}\n\n{prompt[:200]}..."
                
        except Exception as e:
            logger.error(f"章节写作失败: {e}")
            return f"抱歉，{self.role_type}写作章节时出现错误：{str(e)}"

class SearchEnhancedAction(Action):
    """搜索增强动作 - 集成阿里云搜索"""
    
    def __init__(self, role_type: str, **kwargs):
        super().__init__(**kwargs)
        self.role_type = role_type
        
    async def run(self, query: str, project_info: Dict, role_llm=None) -> str:
        """执行搜索增强分析"""
        try:
            # 使用阿里云搜索工具
            search_results = await alibaba_search_tool.run(query)
            
            # 构建分析提示
            prompt = f"""作为{self.role_type}，请基于以下搜索结果进行专业分析：

## 项目信息
- 项目名称：{project_info.get('name', '未知项目')}
- 项目类型：{project_info.get('type', '绩效评价')}
- 预算规模：{project_info.get('budget', '待确定')}万元

## 搜索查询
{query}

## 搜索结果
{search_results}

请结合搜索结果和项目特点，提供专业的分析意见："""

            if role_llm:
                response = await role_llm.aask(prompt)
                return response
            else:
                return f"[{self.role_type}] 基于搜索结果的分析：\n\n{search_results[:500]}..."
                
        except Exception as e:
            logger.error(f"搜索增强分析失败: {e}")
            return f"抱歉，{self.role_type}搜索分析时出现错误：{str(e)}"
    
    def _build_prompt(self, context: str, project_info: Dict) -> str:
        """构建分析提示"""
        base_prompt = f"""项目信息：
- 项目名称：{project_info.get('name', '未知项目')}
- 项目类型：{project_info.get('type', '绩效评价')}
- 预算规模：{project_info.get('budget', '待确定')}万元
- 资金来源：{project_info.get('funding_source', '财政资金')}

上下文：{context}

"""
        
        role_prompts = {
            "data_analyst": base_prompt + """请作为数据分析师，进行以下分析：
1. 构建科学的指标体系（投入、过程、产出、效果四个维度）
2. 评估数据完整性和质量
3. 提供量化分析建议
4. 识别数据缺口

请用中文回复，提供具体的分析结果。""",
            
            "policy_researcher": base_prompt + """请作为政策研究员，进行以下分析：
1. 研究相关政策背景和法规要求
2. 分析政策对项目的影响
3. 确保项目合规性
4. 提供政策建议

请用中文回复，引用具体的政策法规。""",
            
            "case_researcher": base_prompt + """请作为案例研究员，进行以下分析：
1. 搜索和分析类似项目案例
2. 进行对比分析
3. 识别最佳实践和经验教训
4. 提供借鉴建议

请用中文回复，提供具体的案例分析。""",
            
            "indicator_expert": base_prompt + """请作为指标专家，进行以下工作：
1. 设计科学的评价指标体系
2. 制定具体的评价规则和标准
3. 确定指标权重
4. 提供评价方法

请用中文回复，提供完整的指标体系设计。""",
            
            "writer": base_prompt + """请作为写作专员，进行以下工作：
1. 整合各专家的分析结果
2. 撰写报告章节内容
3. 确保内容逻辑清晰
4. 遵循报告格式要求

请用中文回复，生成高质量的报告内容。""",
            
            "reviewer": base_prompt + """请作为质量评审员，进行以下评审：
1. 评估内容的完整性和准确性
2. 检查数据引用的可靠性
3. 评价写作质量和专业水准
4. 提供具体的改进建议

请用中文回复，提供详细的质量评估。"""
        }
        
        return role_prompts.get(self.role_type, base_prompt + "请根据你的专业角色进行分析。")

class TemplateAnalyzerRole(Role):
    """模板分析师角色 - 负责分析报告模板并制定写作蓝图"""
    
    def __init__(self, project_info: Dict, message_queue: Queue, **kwargs):
        super().__init__(
            name="模板分析师",
            profile="Template Analyzer",
            goal="分析报告模板，制定写作蓝图和执行计划",
            constraints="必须严格按照模板结构制定写作计划",
            **kwargs
        )
        self.project_info = project_info
        self.message_queue = message_queue
        self.template_action = TemplateAnalysisAction()
        
    async def _act(self) -> Message:
        """执行模板分析"""
        try:
            # 发送思考状态
            if self.message_queue:
                self.message_queue.put({
                    "agent_type": "template_analyzer",
                    "agent_name": "模板分析师",
                    "content": "🔍 正在分析报告模板结构...",
                    "status": "thinking"
                })
            
            # 执行模板分析
            result = await self.template_action.run(self.project_info, report_template_analyzer)
            
            # 发送结果
            if self.message_queue:
                self.message_queue.put({
                    "agent_type": "template_analyzer",
                    "agent_name": "模板分析师",
                    "content": result,
                    "status": "completed"
                })
            
            return Message(content=result, role=self.profile)
            
        except Exception as e:
            error_msg = f"模板分析失败：{str(e)}"
            logger.error(error_msg)
            
            if self.message_queue:
                self.message_queue.put({
                    "agent_type": "template_analyzer",
                    "agent_name": "模板分析师",
                    "content": error_msg,
                    "status": "error"
                })
            
            return Message(content=error_msg, role=self.profile)

class ChapterWriterRole(Role):
    """章节写作角色 - 基于模板进行章节写作"""
    
    def __init__(self, role_type: str, project_info: Dict, message_queue: Queue, **kwargs):
        super().__init__(**kwargs)
        self.role_type = role_type
        self.project_info = project_info
        self.message_queue = message_queue
        self.chapter_action = ChapterWritingAction(role_type)
        self.search_action = SearchEnhancedAction(role_type)
        
    async def write_chapter(self, chapter: ChapterInfo) -> str:
        """写作指定章节"""
        try:
            # 发送开始写作状态
            if self.message_queue:
                self.message_queue.put({
                    "agent_type": self.role_type,
                    "agent_name": self.name,
                    "content": f"📝 开始写作章节：{chapter.title}",
                    "status": "writing"
                })
            
            # 如果需要搜索增强，先进行搜索
            search_results = ""
            if chapter.title and any(keyword in chapter.title for keyword in ["政策", "案例", "经验", "最佳实践"]):
                search_query = f"{self.project_info.get('name', '')} {chapter.title} 绩效评价"
                search_results = await self.search_action.run(search_query, self.project_info, self.llm)
            
            # 执行章节写作
            result = await self.chapter_action.run(chapter, self.project_info, self.llm, search_results)
            
            # 发送写作结果
            if self.message_queue:
                self.message_queue.put({
                    "agent_type": self.role_type,
                    "agent_name": self.name,
                    "content": result,
                    "status": "completed"
                })
                
                # 触发增量报告更新
                self.message_queue.put({
                    "agent_type": "report_update",
                    "agent_name": f"{self.name}({chapter.chapter_code})",
                    "content": result,
                    "chapter_code": chapter.chapter_code,
                    "is_incremental_update": True
                })
            
            return result
            
        except Exception as e:
            error_msg = f"{self.name}写作章节失败：{str(e)}"
            logger.error(error_msg)
            
            if self.message_queue:
                self.message_queue.put({
                    "agent_type": self.role_type,
                    "agent_name": self.name,
                    "content": error_msg,
                    "status": "error"
                })
            
            return error_msg

class ReportRole(Role):
    """报告角色基类 - 保持向后兼容"""
    
    def __init__(self, role_type: str, project_info: Dict, **kwargs):
        super().__init__(**kwargs)
        self.role_type = role_type
        self.project_info = project_info
        self.search_action = SearchEnhancedAction(role_type)
        # 为了向后兼容，保留analysis_action
        self.analysis_action = SearchEnhancedAction(role_type)
        # 不直接存储Queue对象，而是通过全局管理器获取
        
    async def _act(self) -> Message:
        """执行角色动作"""
        # 先发送思考状态
        if hasattr(self, '_message_queue') and self._message_queue:
            self._message_queue.put({
                "agent_type": self.role_type,
                "agent_name": self.name,
                "content": f"🤔 {self.name}正在分析项目信息...",
                "status": "thinking"
            })
        
        # 获取最新的消息作为上下文
        context = ""
        if hasattr(self, 'rc') and self.rc.memory:
            messages = self.rc.memory.get()
            if messages:
                latest_msg = messages[-1]
                context = latest_msg.content
            
        # 执行分析，传入self.llm以便调用LLM
        # 使用搜索增强的分析方法
        search_query = f"{self.project_info.get('name', '')} {self.role_type} 绩效评价"
        result = await self.analysis_action.run(search_query, self.project_info, self.llm)
        
        # 将结果放入消息队列，供WebSocket发送
        if hasattr(self, '_message_queue') and self._message_queue:
            self._message_queue.put({
                "agent_type": self.role_type,
                "agent_name": self.name,
                "content": result,
                "status": "completed"
            })
            
            # 同时触发增量报告更新
            self._message_queue.put({
                "agent_type": "report_update",
                "agent_name": self.name,
                "content": result,
                "is_incremental_update": True
            })
        
        # 返回消息
        return Message(content=result, role=self.profile)

class ChiefEditorRole(ReportRole):
    """总编角色 - 负责协调和决策"""
    
    def __init__(self, message_queue: Queue, project_info: Dict, **kwargs):
        super().__init__(
            role_type="chief_editor",
            project_info=project_info,
            name="总编",
            profile="Chief Editor",
            goal="协调团队工作，制定写作策略，响应用户需求",
            constraints="必须根据用户插话调整工作流程，确保报告质量",
            **kwargs
        )
        self.message_queue = message_queue  # 单独存储message_queue
        self.user_interventions = []
        
    def add_user_intervention(self, intervention: str):
        """添加用户插话"""
        self.user_interventions.append({
            "content": intervention,
            "timestamp": datetime.now()
        })
        logger.info(f"用户插话已记录: {intervention[:50]}...")
    
    async def _act(self) -> Message:
        """总编的特殊行为 - 考虑用户插话"""
        context = ""
        if hasattr(self, 'rc') and self.rc.memory:
            messages = self.rc.memory.get()
            if messages:
                latest_msg = messages[-1]
                context = latest_msg.content
            
        # 如果有用户插话，优先处理
        if self.user_interventions:
            latest_intervention = self.user_interventions[-1]
            context += f"\n\n用户最新要求：{latest_intervention['content']}"
            
        # 总编的特殊提示
        prompt = f"""作为总编，请根据以下信息制定工作计划：

项目信息：
- 项目名称：{self.project_info.get('name', '未知项目')}
- 项目类型：{self.project_info.get('type', '绩效评价')}
- 预算规模：{self.project_info.get('budget', '待确定')}万元

当前情况：{context}

请分析项目特点，决定需要哪些专家参与，制定详细的工作计划。
如果有用户插话，请重点考虑用户的要求。

格式：
PLAN:
1. [专家名称]: [具体任务]
2. [专家名称]: [具体任务]
...

用中文回复。"""
        
        try:
            # 使用正确的MetaGPT API调用LLM
            result = await self.llm.aask(prompt)
            
            # 将结果放入消息队列
            if self.message_queue:
                self.message_queue.put({
                    "agent_type": "chief_editor",
                    "agent_name": "总编",
                    "content": result,
                    "status": "completed"
                })
            
            return Message(content=result, role=self.profile)
            
        except Exception as e:
            error_msg = f"总编决策时出现错误：{str(e)}"
            logger.error(error_msg)
            
            if self.message_queue:
                self.message_queue.put({
                    "agent_type": "chief_editor", 
                    "agent_name": "总编",
                    "content": error_msg,
                    "status": "error"
                })
            
            return Message(content=error_msg, role=self.profile)

class ReportTeam(Team):
    """报告团队"""
    
    def __init__(self, session_id: str, project_info: Dict, message_queue: Queue):
        super().__init__()
        self._session_id = session_id
        self._project_info = project_info
        self._message_queue = message_queue
        
        # 创建工作空间
        workspace_path = Path(f"workspaces/{session_id}")
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化角色
        self._init_roles()
        
    def _init_roles(self):
        """初始化角色"""
        # 创建总编（特殊角色）
        chief_editor = ChiefEditorRole(
            message_queue=self._message_queue,
            project_info=self._project_info
        )
        
        # 创建其他专家角色
        roles = [chief_editor]
        
        role_configs = [
            {
                "role_type": "data_analyst",
                "name": "数据分析师",
                "profile": "Data Analyst",
                "goal": "分析项目数据，构建指标体系，提供量化分析",
                "constraints": "必须基于真实数据进行分析，确保指标科学合理"
            },
            {
                "role_type": "policy_researcher",
                "name": "政策研究员",
                "profile": "Policy Researcher",
                "goal": "研究政策背景，确保合规性，提供法规依据",
                "constraints": "必须引用准确的政策法规，确保合规性"
            },
            {
                "role_type": "case_researcher",
                "name": "案例研究员",
                "profile": "Case Researcher",
                "goal": "搜索类似案例，进行对比分析，提供最佳实践",
                "constraints": "必须提供真实可靠的案例，附带参考链接"
            },
            {
                "role_type": "indicator_expert",
                "name": "指标专家",
                "profile": "Indicator Expert",
                "goal": "设计科学的评价指标体系，制定评价标准和权重",
                "constraints": "必须确保指标体系科学合理，权重分配公正"
            },
            {
                "role_type": "writer",
                "name": "写作专员",
                "profile": "Report Writer",
                "goal": "整合各专家分析结果，撰写高质量报告",
                "constraints": "必须确保报告逻辑清晰，内容完整，格式规范"
            },
            {
                "role_type": "reviewer",
                "name": "质量评审员",
                "profile": "Quality Reviewer",
                "goal": "评审报告质量，提供改进建议",
                "constraints": "必须客观公正地评价报告质量，提出具体改进意见"
            }
        ]
        
        for config in role_configs:
            role = ReportRole(
                role_type=config["role_type"],
                project_info=self._project_info,
                name=config["name"],
                profile=config["profile"],
                goal=config["goal"],
                constraints=config["constraints"]
            )
            # Store message queue reference for later use
            role._message_queue = self._message_queue
            roles.append(role)
        
        # 设置团队角色
        self.hire(roles)
        print(f"✅ 成功初始化 {len(roles)} 个角色: {', '.join([role.name for role in roles])}")
        
    def get_chief_editor(self) -> ChiefEditorRole:
        """获取总编角色"""
        if hasattr(self, 'env') and hasattr(self.env, 'get_role'):
            # 通过角色名称获取总编
            chief_editor = self.env.get_role("总编")
            if chief_editor and isinstance(chief_editor, ChiefEditorRole):
                return chief_editor
        return None
    
    async def run_project(self, initial_requirement: str) -> str:
        """运行项目"""
        try:
            # 创建初始消息
            initial_message = Message(content=initial_requirement, role="user")
            
            # 发送给总编开始工作
            chief_editor = self.get_chief_editor()
            if chief_editor:
                # 手动触发总编的行动
                response = await chief_editor._act()
                
                # 让其他角色依次工作
                if hasattr(self, 'env') and hasattr(self.env, 'get_roles'):
                    all_roles = self.env.get_roles()  # 获取所有角色对象的字典
                    for role_name, role_obj in all_roles.items():
                        if role_name != "总编":  # 跳过总编，因为已经执行过了
                            try:
                                await role_obj._act()
                            except Exception as e:
                                logger.error(f"Role {role_name} failed: {e}")
                
                return response.content if response else "项目执行完成"
            else:
                return "未找到总编角色"
                
        except Exception as e:
            error_msg = f"项目执行出错: {str(e)}"
            logger.error(error_msg)
            return error_msg

class TemplateBasedReportTeam:
    """基于模板的报告团队 - 采用SOP模式"""
    
    def __init__(self, session_id: str, project_info: Dict, message_queue: Queue):
        self.session_id = session_id
        self.project_info = project_info
        self.message_queue = message_queue
        self.template_analyzer = report_template_analyzer
        
        # 创建工作空间
        workspace_path = Path(f"workspaces/{session_id}")
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 加载写作进度
        self.template_analyzer.load_progress(session_id)
        
        # 初始化专家角色
        self.experts = self._init_experts()
        
    def _init_experts(self) -> Dict[str, ChapterWriterRole]:
        """初始化专家角色"""
        experts = {}
        
        expert_configs = [
            {
                "role_type": "template_analyzer",
                "name": "模板分析师",
                "profile": "Template Analyzer",
                "goal": "分析报告模板，制定写作蓝图",
                "constraints": "必须严格按照模板结构分析"
            },
            {
                "role_type": "data_analyst", 
                "name": "数据分析师",
                "profile": "Data Analyst",
                "goal": "构建指标体系，进行数据分析",
                "constraints": "必须基于真实数据，确保指标科学"
            },
            {
                "role_type": "policy_researcher",
                "name": "政策研究员", 
                "profile": "Policy Researcher",
                "goal": "研究政策背景，确保合规性",
                "constraints": "必须引用准确政策法规"
            },
            {
                "role_type": "case_researcher",
                "name": "案例研究员",
                "profile": "Case Researcher", 
                "goal": "搜索案例，进行对比分析",
                "constraints": "必须提供真实可靠案例"
            },
            {
                "role_type": "indicator_expert",
                "name": "指标专家",
                "profile": "Indicator Expert",
                "goal": "设计评价指标体系",
                "constraints": "必须确保指标科学合理"
            },
            {
                "role_type": "writer",
                "name": "写作专员", 
                "profile": "Report Writer",
                "goal": "整合分析结果，撰写报告",
                "constraints": "必须确保逻辑清晰，格式规范"
            },
            {
                "role_type": "reviewer",
                "name": "质量评审员",
                "profile": "Quality Reviewer", 
                "goal": "评审报告质量，提供改进建议",
                "constraints": "必须客观公正评价质量"
            }
        ]
        
        for config in expert_configs:
            if config["role_type"] == "template_analyzer":
                expert = TemplateAnalyzerRole(
                    project_info=self.project_info,
                    message_queue=self.message_queue
                )
            else:
                expert = ChapterWriterRole(
                    role_type=config["role_type"],
                    project_info=self.project_info,
                    message_queue=self.message_queue,
                    name=config["name"],
                    profile=config["profile"],
                    goal=config["goal"],
                    constraints=config["constraints"]
                )
            
            experts[config["role_type"]] = expert
        
        logger.info(f"✅ 初始化 {len(experts)} 个专家角色")
        return experts
    
    async def run_template_based_workflow(self) -> str:
        """运行基于模板的工作流程"""
        try:
            # 1. 首先进行模板分析
            template_analyzer_role = self.experts["template_analyzer"]
            template_analysis = await template_analyzer_role._act()
            
            # 2. 按章节顺序进行写作
            completed_chapters = []
            
            while True:
                # 获取下一个需要写作的章节
                next_chapter = self.template_analyzer.get_next_chapter_to_write()
                
                if not next_chapter:
                    logger.info("所有章节写作完成")
                    break
                
                logger.info(f"开始写作章节: {next_chapter.title} ({next_chapter.chapter_code})")
                
                # 选择合适的专家写作该章节
                expert = self._select_expert_for_chapter(next_chapter)
                
                if expert:
                    # 执行章节写作
                    chapter_content = await expert.write_chapter(next_chapter)
                    completed_chapters.append({
                        "chapter": next_chapter,
                        "content": chapter_content,
                        "expert": expert.name
                    })
                    
                    # 标记章节为已完成
                    self.template_analyzer.mark_chapter_completed(next_chapter.chapter_code)
                    
                    # 保存进度
                    self.template_analyzer.save_progress(self.session_id)
                    
                    logger.info(f"章节 {next_chapter.chapter_code} 写作完成")
                else:
                    logger.warning(f"未找到合适的专家写作章节: {next_chapter.title}")
                    break
            
            # 3. 生成最终报告
            final_report = self._generate_structured_report(completed_chapters)
            
            return final_report
            
        except Exception as e:
            error_msg = f"模板化工作流程执行失败: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _select_expert_for_chapter(self, chapter: ChapterInfo) -> Optional[ChapterWriterRole]:
        """根据章节特点选择合适的专家"""
        chapter_title = chapter.title.lower()
        chapter_code = chapter.chapter_code
        
        # 根据章节内容选择专家
        if any(keyword in chapter_title for keyword in ["指标", "评价", "分析", "数据"]):
            return self.experts.get("data_analyst") or self.experts.get("indicator_expert")
        elif any(keyword in chapter_title for keyword in ["政策", "法规", "合规", "背景"]):
            return self.experts.get("policy_researcher")
        elif any(keyword in chapter_title for keyword in ["案例", "经验", "实践", "对比"]):
            return self.experts.get("case_researcher")
        elif chapter.is_indicator_driven or "7.2" in chapter_code:  # 指标分析章节
            return self.experts.get("indicator_expert")
        elif any(keyword in chapter_title for keyword in ["问题", "建议", "改进", "结论"]):
            return self.experts.get("writer")
        else:
            # 默认使用写作专员
            return self.experts.get("writer")
    
    def _generate_structured_report(self, completed_chapters: List[Dict]) -> str:
        """生成结构化的最终报告"""
        template_info = self.template_analyzer.get_template_summary()
        
        report_content = f"""# {self.project_info.get('name', '项目')}绩效评价报告

*基于模板: {template_info['name']}*
*生成时间: {datetime.now().strftime('%Y年%m月%d日')}*
*生成方式: MetaGPT多Agent协作 + 模板驱动*

---

"""
        
        # 按章节顺序组织内容
        for chapter_info in completed_chapters:
            chapter = chapter_info["chapter"]
            content = chapter_info["content"]
            expert = chapter_info["expert"]
            
            report_content += f"""
## {chapter.title}

*章节代码: {chapter.chapter_code}*
*负责专家: {expert}*

{content}

---
"""
        
        # 添加生成统计
        report_content += f"""

## 报告生成统计

- 模板名称: {template_info['name']}
- 总章节数: {template_info['total_chapters']}
- 已完成章节: {template_info['completed_chapters']}
- 参与专家: {len(self.experts)} 位
- 生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

---
*本报告由AutoWriter Enhanced系统基于MetaGPT框架自动生成*
"""
        
        return report_content

class MetaGPTManager:
    """MetaGPT管理器 - 支持传统模式和模板驱动模式"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict] = {}
        self.message_queues: Dict[str, Queue] = {}
        self.message_tasks: Dict[str, asyncio.Task] = {}
        self.teams: Dict[str, ReportTeam] = {}
        self.template_teams: Dict[str, TemplateBasedReportTeam] = {}
        
        # 配置MetaGPT
        self._configure_metagpt()
        
    def _configure_metagpt(self):
        """配置MetaGPT - 使用MetaGPT标准配置方式"""
        try:
            # MetaGPT会自动读取 MetaGPT/config/config2.yaml 配置文件
            # 我们只需要验证配置是否正确加载
            from metagpt.config2 import config
            
            if hasattr(config, 'llm') and config.llm:
                print(f"✅ MetaGPT配置成功: {config.llm.model}")
                print(f"   API类型: {config.llm.api_type}")
                print(f"   API地址: {config.llm.base_url}")
            else:
                raise Exception("MetaGPT配置未正确加载")
                
        except Exception as e:
            print(f"❌ MetaGPT配置失败: {e}")
            print("请检查 MetaGPT/config/config2.yaml 配置文件")
            raise
    
    async def start_analysis_workflow(self, session_id: str, project_info: Dict, websocket_manager):
        """启动分析工作流 - 传统模式"""
        print(f"Starting MetaGPT workflow for session {session_id}")
        
        if session_id in self.active_sessions:
            print(f"Session {session_id} already exists")
            return
        
        # 初始化会话
        self.active_sessions[session_id] = {
            "phase": WorkflowPhase.ANALYSIS,
            "project_info": project_info,
            "websocket_manager": websocket_manager,
            "is_running": True,
            "workflow_started": True,
            "mode": "traditional"
        }
        
        # 创建消息队列
        self.message_queues[session_id] = Queue()
        
        # 启动消息发送任务
        self.message_tasks[session_id] = asyncio.create_task(
            self._message_sender(session_id)
        )
        
        # 创建MetaGPT团队
        team = ReportTeam(
            session_id=session_id,
            project_info=project_info,
            message_queue=self.message_queues[session_id]
        )
        self.teams[session_id] = team
        
        # 在后台线程运行MetaGPT
        thread = threading.Thread(
            target=self._run_metagpt_in_thread,
            args=(session_id, project_info)
        )
        thread.daemon = True
        thread.start()
    
    async def start_template_based_workflow(self, session_id: str, project_info: Dict, websocket_manager):
        """启动基于模板的工作流程 - 新的SOP模式"""
        print(f"Starting Template-based MetaGPT workflow for session {session_id}")
        
        if session_id in self.active_sessions:
            print(f"Session {session_id} already exists")
            return
        
        # 初始化会话
        self.active_sessions[session_id] = {
            "phase": WorkflowPhase.ANALYSIS,
            "project_info": project_info,
            "websocket_manager": websocket_manager,
            "is_running": True,
            "workflow_started": True,
            "mode": "template_based"
        }
        
        # 创建消息队列
        self.message_queues[session_id] = Queue()
        
        # 启动消息发送任务
        self.message_tasks[session_id] = asyncio.create_task(
            self._message_sender(session_id)
        )
        
        # 创建基于模板的团队
        template_team = TemplateBasedReportTeam(
            session_id=session_id,
            project_info=project_info,
            message_queue=self.message_queues[session_id]
        )
        self.template_teams[session_id] = template_team
        
        # 在后台线程运行模板化工作流程
        thread = threading.Thread(
            target=self._run_template_workflow_in_thread,
            args=(session_id, project_info)
        )
        thread.daemon = True
        thread.start()
    
    def _run_template_workflow_in_thread(self, session_id: str, project_info: Dict):
        """在线程中运行模板化工作流程"""
        try:
            print("Starting Template-based MetaGPT workflow...")
            
            # 发送开始消息
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "系统",
                "content": "🚀 基于模板的MetaGPT团队正在启动...",
                "status": "running"
            })
            
            # 获取模板团队
            template_team = self.template_teams[session_id]
            
            # 运行模板化工作流程（需要在新的事件循环中）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(template_team.run_template_based_workflow())
                print(f"Template-based workflow completed: {result[:100]}...")
                
                # 发送最终报告
                self.message_queues[session_id].put({
                    "agent_type": "report",
                    "agent_name": "最终报告",
                    "content": result,
                    "is_report": True
                })
                
            finally:
                loop.close()
            
        except Exception as e:
            print(f"Error in template workflow thread: {e}")
            import traceback
            traceback.print_exc()
            
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "系统",
                "content": f"❌ 模板化工作流程执行出错: {str(e)}",
                "status": "error"
            })
        finally:
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["is_running"] = False
    
    def _run_template_workflow_in_thread(self, session_id: str, project_info: Dict):
        """在线程中运行模板化工作流程"""
        try:
            print("Starting Template-based MetaGPT workflow...")
            
            # 发送开始消息
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "系统",
                "content": "🚀 基于模板的MetaGPT团队正在启动...",
                "status": "running"
            })
            
            # 获取模板团队
            template_team = self.template_teams[session_id]
            
            # 运行模板化工作流程（需要在新的事件循环中）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(template_team.run_template_based_workflow())
                print(f"Template-based workflow completed: {result[:100]}...")
                
                # 发送最终报告
                self.message_queues[session_id].put({
                    "agent_type": "report",
                    "agent_name": "最终报告",
                    "content": result,
                    "is_report": True
                })
                
            finally:
                loop.close()
            
        except Exception as e:
            print(f"Error in template workflow thread: {e}")
            import traceback
            traceback.print_exc()
            
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "系统",
                "content": f"❌ 模板化工作流程执行出错: {str(e)}",
                "status": "error"
            })
        finally:
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["is_running"] = False
    
    async def _message_sender(self, session_id: str):
        """异步消息发送器"""
        websocket_manager = self.active_sessions[session_id]["websocket_manager"]
        queue = self.message_queues[session_id]
        
        while self.active_sessions.get(session_id, {}).get("is_running", False):
            try:
                if not queue.empty():
                    msg = queue.get_nowait()
                    
                    if msg.get("is_incremental_update"):
                        # 处理增量报告更新
                        self._update_incremental_report(session_id, msg["agent_name"], msg["content"])
                        print(f"📄 增量更新报告: {msg['agent_name']}")
                    elif msg.get("is_report"):
                        await websocket_manager.broadcast_report_update(
                            session_id=session_id,
                            chapter="full_report",
                            content=msg["content"],
                            version=1
                        )
                        print(f"📄 报告已发送")
                    else:
                        await websocket_manager.broadcast_agent_message(
                            session_id=session_id,
                            agent_type=msg["agent_type"],
                            agent_name=msg["agent_name"],
                            content=msg["content"],
                            status=msg.get("status", "completed")
                        )
                        print(f"📨 消息已发送: {msg['agent_name']}")
                    
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error in message sender: {e}")
                await asyncio.sleep(1)
        
        await websocket_manager.broadcast_workflow_status(session_id, "completed", 100)
        print(f"Message sender stopped for session {session_id}")
    
    def _run_metagpt_in_thread(self, session_id: str, project_info: Dict):
        """在线程中运行MetaGPT"""
        try:
            print("Starting MetaGPT team...")
            
            # 发送开始消息
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "系统",
                "content": "🚀 MetaGPT团队正在启动...",
                "status": "running"
            })
            
            # 获取团队
            team = self.teams[session_id]
            
            # 构建初始需求
            initial_requirement = f"""请为项目"{project_info.get('name', '未知项目')}"生成绩效评价报告。

项目信息：
- 项目名称：{project_info.get('name', '未知项目')}
- 项目类型：{project_info.get('type', '绩效评价')}
- 预算规模：{project_info.get('budget', '待确定')}万元
- 资金来源：{project_info.get('funding_source', '财政资金')}
- 项目目标：{project_info.get('objective', '待确定')}

请各专家协作完成分析和报告撰写。"""
            
            # 运行项目（需要在新的事件循环中）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(team.run_project(initial_requirement))
                print(f"MetaGPT项目完成: {result[:100]}...")
                
                # 生成最终报告
                self._generate_final_report(session_id, project_info, result)
                
            finally:
                loop.close()
            
        except Exception as e:
            print(f"Error in MetaGPT thread: {e}")
            import traceback
            traceback.print_exc()
            
            self.message_queues[session_id].put({
                "agent_type": "system",
                "agent_name": "系统",
                "content": f"❌ MetaGPT执行出错: {str(e)}",
                "status": "error"
            })
        finally:
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["is_running"] = False
    
    def _generate_final_report(self, session_id: str, project_info: Dict, analysis_result: str):
        """生成最终报告"""
        report_content = f"""# {project_info.get('name', '项目')}绩效评价报告

## 报告摘要

本报告基于MetaGPT多Agent协作分析，对{project_info.get('name', '该项目')}进行了全面的绩效评价。

## 专家团队分析结果

{analysis_result}

## 综合结论

基于MetaGPT团队的协作分析，项目整体表现良好，建议继续推进并关注专家提出的改进建议。

---
*报告生成时间：{datetime.now().strftime('%Y年%m月%d日')}*
*生成方式：MetaGPT多Agent协作*
"""
        
        # 保存报告到workspace目录
        self._save_report_to_workspace(session_id, report_content)
        
        # 发送报告
        self.message_queues[session_id].put({
            "agent_type": "report",
            "agent_name": "报告",
            "content": report_content,
            "is_report": True
        })
    
    def _save_report_to_workspace(self, session_id: str, content: str):
        """保存报告到workspace目录"""
        try:
            workspace_path = Path(f"workspaces/{session_id}")
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            report_file = workspace_path / "report.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"📄 报告已保存到: {report_file}")
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")
    
    def _update_incremental_report(self, session_id: str, agent_name: str, agent_content: str):
        """增量更新报告"""
        try:
            workspace_path = Path(f"workspaces/{session_id}")
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            # 读取现有报告
            report_file = workspace_path / "report.md"
            if report_file.exists():
                with open(report_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            else:
                # 创建初始报告结构
                project_info = self.active_sessions[session_id]["project_info"]
                existing_content = f"""# {project_info.get('name', '项目')}绩效评价报告

## 报告摘要

本报告基于MetaGPT多Agent协作分析，正在实时生成中...

## 专家团队分析结果

## 综合结论

基于MetaGPT团队的协作分析，正在生成综合结论...

---
*报告生成时间：{datetime.now().strftime('%Y年%m月%d日')}*
*生成方式：MetaGPT多Agent协作*
"""
            
            # 添加新的专家分析
            new_section = f"""
### {agent_name}分析

{agent_content}

---
"""
            
            # 在"## 综合结论"之前插入新内容
            if "## 综合结论" in existing_content:
                parts = existing_content.split("## 综合结论")
                updated_content = parts[0] + new_section + "\n## 综合结论" + parts[1]
            else:
                # 如果没有综合结论部分，直接添加到末尾
                updated_content = existing_content + new_section
            
            # 保存更新后的报告
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            # 发送更新后的报告到前端
            self.message_queues[session_id].put({
                "agent_type": "report",
                "agent_name": "报告更新",
                "content": updated_content,
                "is_report": True
            })
            
            print(f"📄 报告已增量更新: {agent_name}")
            
        except Exception as e:
            print(f"❌ 增量更新报告失败: {e}")
            import traceback
            traceback.print_exc()
    
    async def handle_user_intervention(self, session_id: str, message: str):
        """处理用户插话"""
        if session_id in self.teams:
            team = self.teams[session_id]
            chief_editor = team.get_chief_editor()
            
            if chief_editor:
                # 添加用户插话到总编
                chief_editor.add_user_intervention(message)
                
                # 立即响应用户
                self.message_queues[session_id].put({
                    "agent_type": "chief_editor",
                    "agent_name": "总编",
                    "content": f"收到您的重要指示：「{message}」\n\n我正在调整团队工作计划，会重点关注您提到的内容。",
                    "status": "completed"
                })
                
                print(f"🗣️ 用户插话已传达给总编: {message[:50]}...")
    
    def get_session_status(self, session_id: str):
        """获取会话状态"""
        return self.active_sessions.get(session_id)
    
    async def pause_workflow(self, session_id: str):
        """暂停工作流"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["is_running"] = False
    
    async def resume_workflow(self, session_id: str):
        """恢复工作流"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["is_running"] = True