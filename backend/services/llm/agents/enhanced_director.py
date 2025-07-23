"""
增强版智能项目总监Agent - 基于MetaGPT设计理念
具备深度客户沟通、智能任务规划和动态Agent编排能力
"""
from metagpt.roles import Role
from metagpt.schema import Message, Plan, Task
from metagpt.logs import logger
from metagpt.strategy.planner import Planner
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from backend.services.llm.agents.base import BaseAgent


class EnhancedDirectorAgent(BaseAgent):
    """
    🎯 增强版智能项目总监 - 虚拟办公室的核心管理者
    
    基于MetaGPT的TeamLeader和Planner模式设计，具备：
    1. 深度客户沟通能力 - 回答各种专业问题，不只是构建报告框架
    2. 智能任务规划 - 将复杂需求拆解为可执行任务
    3. 动态Agent编排 - 根据需求调用合适的Agent组合
    4. 上下文记忆 - 维护对话历史和项目状态
    5. 灵活工作流 - 简单问题直接回答，复杂任务启动多Agent协作
    """
    
    def __init__(self, session_id: str, workspace_path: str, memory_manager=None):
        super().__init__(
            agent_id="enhanced_director",
            session_id=session_id,
            workspace_path=workspace_path,
            memory_manager=memory_manager,
            profile="智能项目总监",
            goal="项目管理和客户沟通专家"
        )
        
        # 设置增强版Director的特有属性
        self.role = "项目管理和客户沟通专家"
        
        # 初始化增强版Director的特有属性
        self.conversation_context = []
        self.active_tasks = []
        self.current_report_structure = None
        
        # 初始化其他必要属性
        self._initialize_capabilities()
        self._initialize_knowledge_base()
    
    def _initialize_capabilities(self):
        """初始化Agent能力映射"""
        self.agent_capabilities = {
            "document_expert": {
                "name": "文档专家李心悦",
                "capabilities": ["文档上传处理", "格式转换", "内容摘要", "文档检索", "历史文档查找", "文档管理"],
                "suitable_for": ["文档相关问题", "历史资料查询", "文件处理需求", "文档格式转换"],
                "keywords": ["文档", "文件", "历史", "资料", "上传", "格式", "查找"]
            },
            "case_expert": {
                "name": "案例专家王磊", 
                "capabilities": ["案例搜索", "最佳实践分析", "行业对比", "参考资料收集", "网络搜索"],
                "suitable_for": ["案例查找", "行业经验", "参考资料需求", "对比分析", "最佳实践"],
                "keywords": ["案例", "参考", "搜索", "行业", "经验", "实践", "对比"]
            },
            "data_analyst": {
                "name": "数据分析师赵丽娅",
                "capabilities": ["数据提取", "统计分析", "图表生成", "指标计算", "数据可视化"],
                "suitable_for": ["数据分析", "统计需求", "指标相关", "量化分析", "图表制作"],
                "keywords": ["数据", "分析", "统计", "指标", "图表", "量化", "计算"]
            },
            "writer_expert": {
                "name": "写作专家张翰",
                "capabilities": ["内容撰写", "章节编写", "文本润色", "结构优化", "报告撰写"],
                "suitable_for": ["写作需求", "内容创作", "章节撰写", "文本优化", "报告编写"],
                "keywords": ["写作", "撰写", "内容", "章节", "编写", "创作", "文本"]
            },
            "chief_editor": {
                "name": "总编辑钱敏",
                "capabilities": ["内容审核", "质量把控", "格式规范", "最终润色", "整体把关"],
                "suitable_for": ["审核需求", "质量检查", "最终确认", "格式规范", "整体优化"],
                "keywords": ["审核", "检查", "质量", "格式", "规范", "润色", "把关"]
            }
        }
    
    def _initialize_knowledge_base(self):
        """初始化专业知识库"""
        self.knowledge_base = {
            "report_writing_tips": {
                "绩效报告写作技巧": [
                    "明确评价目标和范围",
                    "建立科学的指标体系", 
                    "收集充分的数据支撑",
                    "采用定量与定性相结合的方法",
                    "注重逻辑性和条理性",
                    "突出问题导向和结果导向"
                ]
            },
            "common_frameworks": {
                "常用报告框架": [
                    "背景与目标 → 实施过程 → 成效分析 → 问题与建议",
                    "项目概述 → 绩效指标 → 评价结果 → 改进措施",
                    "立项背景 → 执行情况 → 产出效果 → 影响评估"
                ]
            }
        }
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM的方法 - 使用MetaGPT的LLM接口"""
        try:
            # 创建消息
            message = Message(content=prompt, role="user")
            
            # 使用MetaGPT的think方法调用LLM
            response = await self._think()
            
            # 如果think方法不返回字符串，尝试直接使用LLM
            if not isinstance(response, str):
                from metagpt.llm import LLM
                llm = LLM()
                response = await llm.aask(prompt)
            
            return response
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return f"抱歉，我在处理您的请求时遇到了技术问题：{str(e)}"
        
        # 初始化规划器 - 借鉴MetaGPT的Planner模式
        self.planner = Planner(goal="协助用户完成专业报告相关的各种需求")
        
        # 报告模板配置
        self.report_template = self._load_report_template()
    
    def _load_report_template(self) -> dict:
        """加载报告模板配置"""
        try:
            template_path = os.path.join(os.path.dirname(__file__), "../../../..", "reportmodel.yaml")
            import yaml
            with open(template_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载报告模板失败: {e}")
            return {}
    
    async def process_request(self, user_message: str, context: dict = None) -> dict:
        """
        处理用户请求的主入口 - 借鉴MetaGPT的智能分发机制
        """
        try:
            # 更新对话上下文
            self.conversation_context.append({
                "role": "user",
                "content": user_message,
                "timestamp": self._get_timestamp()
            })
            
            # 补录用户消息到统一记忆
            if hasattr(self, '_memory_adapter') and self._memory_adapter:
                self._memory_adapter.add_simple_message(content=user_message, role="user", cause_by="user_input")

            # 智能意图识别和需求分析
            intent_analysis = await self._analyze_user_intent(user_message, context)
            
            # 根据意图选择处理策略
            response = await self._route_request(user_message, intent_analysis, context)
            
            # 记录响应到上下文
            self.conversation_context.append({
                "role": "assistant", 
                "content": response.get("message", ""),
                "timestamp": self._get_timestamp(),
                "intent": intent_analysis
            })
            
            # 补录Agent响应到统一记忆
            if hasattr(self, '_memory_adapter') and self._memory_adapter:
                self._memory_adapter.add_simple_message(
                    content=response.get("message", ""),
                    role=self.profile,
                    cause_by=f"enhanced_director_response:{intent_analysis.get('intent_type', 'unknown')}"
                )
            
            return response
                
        except Exception as e:
            logger.error(f"Enhanced Director处理请求失败: {e}")
            return {
                "success": False,
                "message": f"处理请求时出现错误: {str(e)}",
                "agent_id": self.agent_id,
                "error_type": "processing_error"
            }
    
    async def _analyze_user_intent(self, user_message: str, context: dict = None) -> dict:
        """
        智能意图识别 - 借鉴你原来planner.js的分析逻辑，但更加智能化
        """
        # 构建上下文信息
        context_info = self._build_context_summary()
        
        analysis_prompt = f"""
        作为经验丰富的项目总监，请深度分析用户的意图和需求。

        用户消息：{user_message}
        
        对话历史摘要：{context_info}
        
        当前项目状态：{json.dumps(context or {}, ensure_ascii=False, indent=2)}

        我的团队成员能力：
        {json.dumps(self.agent_capabilities, ensure_ascii=False, indent=2)}

        请分析并返回JSON格式的结果：
        {{
            "intent_type": "意图类型",  // direct_answer, simple_task, complex_workflow, consultation, report_structure
            "complexity": "复杂度",  // simple, medium, complex
            "required_agents": ["需要的Agent ID列表"],
            "workflow_type": "工作流类型",  // single_agent, sequential, parallel, iterative
            "priority": "优先级",  // high, medium, low
            "estimated_steps": "预估步骤数",
            "user_goal": "用户的核心目标",
            "context_dependencies": "是否依赖历史对话",
            "can_answer_directly": "我是否可以直接回答",
            "reasoning": "详细的分析推理过程"
        }}

        意图类型说明：
        - direct_answer: 我可以直接回答的问题（如技巧咨询、概念解释、经验分享）
        - simple_task: 单一Agent可以完成的简单任务（如查找文档、搜索案例）
        - complex_workflow: 需要多Agent协作的复杂工作流（如完整报告撰写）
        - consultation: 专业咨询和建议（需要我的专业判断）
        - report_structure: 报告框架和结构设计

        工作流类型说明：
        - single_agent: 单个Agent独立完成
        - sequential: 多Agent按顺序执行
        - parallel: 多Agent并行执行
        - iterative: 需要多轮迭代优化

        判断原则：
        1. 如果是询问技巧、经验、建议类问题，优先选择direct_answer
        2. 如果明确提到需要某个专家的服务，选择simple_task
        3. 如果是复杂的报告撰写需求，选择complex_workflow
        4. 如果需要专业判断和建议，选择consultation
        """
        
        response = await self._call_llm(analysis_prompt)
        
        try:
            return json.loads(response)
        except:
            return {
                "intent_type": "consultation",
                "complexity": "medium",
                "required_agents": [],
                "workflow_type": "single_agent",
                "priority": "medium",
                "estimated_steps": 1,
                "user_goal": "获得专业帮助",
                "context_dependencies": False,
                "can_answer_directly": True,
                "reasoning": "解析失败，使用默认咨询模式"
            }
    
    async def _route_request(self, user_message: str, intent_analysis: dict, context: dict = None) -> dict:
        """
        智能路由分发 - 根据意图选择最佳处理策略
        """
        intent_type = intent_analysis.get("intent_type", "consultation")
        
        if intent_type == "direct_answer":
            return await self._handle_direct_answer(user_message, intent_analysis)
        elif intent_type == "simple_task":
            return await self._handle_simple_task(user_message, intent_analysis)
        elif intent_type == "complex_workflow":
            return await self._handle_complex_workflow(user_message, intent_analysis)
        elif intent_type == "consultation":
            return await self._handle_consultation(user_message, intent_analysis)
        elif intent_type == "report_structure":
            return await self._handle_report_structure(user_message, intent_analysis)
        else:
            return await self._handle_general_communication(user_message, intent_analysis)
    
    async def _handle_direct_answer(self, user_message: str, intent_analysis: dict) -> dict:
        """
        直接回答模式 - 处理我可以立即回答的专业问题
        这是新增的核心能力，让Director能够直接回答专业问题
        """
        context_summary = self._build_context_summary()
        
        direct_answer_prompt = f"""
        作为经验丰富的项目总监和报告写作专家，请直接回答用户的问题。

        用户问题：{user_message}
        
        对话上下文：{context_summary}
        
        意图分析：{json.dumps(intent_analysis, ensure_ascii=False, indent=2)}

        我的专业知识库：
        {json.dumps(self.knowledge_base, ensure_ascii=False, indent=2)}

        请基于你在以下领域的丰富经验提供专业回答：
        1. 项目管理和协调
        2. 报告写作和结构设计  
        3. 绩效评价和指标设计
        4. 团队协作和工作流程
        5. 质量控制和标准规范

        回答要求：
        1. 专业准确，基于实际经验
        2. 结构清晰，重点突出  
        3. 实用性强，可操作
        4. 如需进一步协助，说明团队可提供的具体服务
        5. 保持友好专业的语调

        如果问题涉及具体的执行操作（如搜索案例、处理文档等），请说明可以安排相应的专家来协助。
        """
        
        response = await self._call_llm(direct_answer_prompt)
        
        return {
            "success": True,
            "message": response,
            "agent_id": self.agent_id,
            "response_type": "direct_answer",
            "next_actions": [],
            "workflow_plan": None,
            "follow_up_services": self._suggest_follow_up_services(intent_analysis)
        }
    
    async def _handle_simple_task(self, user_message: str, intent_analysis: dict) -> dict:
        """
        简单任务模式 - 单个Agent可以完成的任务
        """
        required_agents = intent_analysis.get("required_agents", [])
        if not required_agents:
            # 如果没有明确的Agent需求，尝试智能匹配
            required_agents = self._smart_agent_matching(user_message)
        
        if not required_agents:
            return await self._handle_direct_answer(user_message, intent_analysis)
        
        target_agent = required_agents[0]
        agent_info = self.agent_capabilities.get(target_agent, {})
        
        task_plan = {
            "plan_id": f"simple_task_{self._get_timestamp()}",
            "description": f"委托{agent_info.get('name', target_agent)}处理用户需求",
            "workflow_type": "single_agent",
            "steps": [
                {
                    "step_id": "step_1",
                    "agent_id": target_agent,
                    "action": "process_user_request",
                    "parameters": {
                        "user_message": user_message,
                        "context": self._build_context_summary(),
                        "director_guidance": self._generate_agent_guidance(target_agent, user_message)
                    },
                    "expected_output": "完成用户的具体需求",
                    "dependencies": []
                }
            ],
            "estimated_time": "2-5分钟",
            "success_criteria": "用户需求得到满足"
        }
        
        response_message = f"""我理解您的需求，这个任务最适合由我们的{agent_info.get('name', target_agent)}来处理。

{agent_info.get('name', target_agent)}的专长包括：{', '.join(agent_info.get('capabilities', []))}

我现在就安排{agent_info.get('name', target_agent)}为您处理这个需求，我会全程跟进确保质量。"""
        
        return {
            "success": True,
            "message": response_message,
            "agent_id": self.agent_id,
            "response_type": "simple_task",
            "task_plan": task_plan,
            "next_actions": [target_agent]
        }
    
    def _smart_agent_matching(self, user_message: str) -> List[str]:
        """
        智能Agent匹配 - 根据用户消息内容匹配最合适的Agent
        """
        message_lower = user_message.lower()
        matched_agents = []
        
        for agent_id, agent_info in self.agent_capabilities.items():
            keywords = agent_info.get("keywords", [])
            if any(keyword in message_lower for keyword in keywords):
                matched_agents.append(agent_id)
        
        return matched_agents[:2]  # 最多返回2个匹配的Agent
    
    def _generate_agent_guidance(self, agent_id: str, user_message: str) -> str:
        """
        为特定Agent生成指导信息
        """
        agent_info = self.agent_capabilities.get(agent_id, {})
        return f"""
        作为项目总监，我为您提供以下指导：
        
        用户需求：{user_message}
        
        您的专长：{', '.join(agent_info.get('capabilities', []))}
        
        请充分发挥您的专业能力，为用户提供高质量的服务。
        如遇到超出您专业范围的问题，请及时反馈给我进行协调。
        """
    
    async def _handle_complex_workflow(self, user_message: str, intent_analysis: dict) -> dict:
        """
        复杂工作流模式 - 需要多Agent协作的任务
        """
        # 使用规划器生成详细的执行计划
        workflow_plan = await self._generate_workflow_plan(user_message, intent_analysis)
        
        required_agents = intent_analysis.get("required_agents", [])
        agent_names = [self.agent_capabilities.get(agent_id, {}).get('name', agent_id) for agent_id in required_agents]
        
        response_message = f"""我理解您的需求，这是一个需要团队协作的复杂任务。

参与的团队成员：{', '.join(agent_names)}

执行计划：
{workflow_plan.get('description', '制定详细的执行方案')}

预估完成时间：{workflow_plan.get('estimated_time', '10-30分钟')}

我将作为项目总监全程协调这个复杂工作流，确保各个环节的质量和进度。现在开始执行计划。"""
        
        return {
            "success": True,
            "message": response_message,
            "agent_id": self.agent_id,
            "response_type": "complex_workflow",
            "task_plan": workflow_plan,
            "next_actions": required_agents
        }
    
    async def _handle_consultation(self, user_message: str, intent_analysis: dict) -> dict:
        """
        专业咨询模式 - 提供专业建议和指导
        """
        context_summary = self._build_context_summary()
        
        consultation_prompt = f"""
        作为资深的项目管理专家和报告写作顾问，请为用户提供专业的咨询建议。

        用户咨询：{user_message}
        
        对话背景：{context_summary}
        
        意图分析：{json.dumps(intent_analysis, ensure_ascii=False, indent=2)}

        请基于以下专业领域提供建议：
        1. 项目管理和协调
        2. 报告写作和结构设计
        3. 绩效评价和指标设计
        4. 团队协作和工作流程
        5. 质量控制和标准规范

        咨询回答要求：
        1. 提供多个可行的解决方案
        2. 分析每个方案的优缺点
        3. 给出具体的实施建议
        4. 说明可能遇到的问题和应对策略
        5. 如需进一步协助，说明团队可提供的具体服务

        请以专业顾问的身份，提供有价值的指导意见。
        """
        
        response = await self._call_llm(consultation_prompt)
        
        return {
            "success": True,
            "message": response,
            "agent_id": self.agent_id,
            "response_type": "consultation",
            "next_actions": [],
            "follow_up_services": self._suggest_follow_up_services(intent_analysis)
        }
    
    async def _generate_workflow_plan(self, user_message: str, intent_analysis: dict) -> dict:
        """
        生成详细的工作流执行计划 - 借鉴MetaGPT的规划机制
        """
        context_summary = self._build_context_summary()
        required_agents = intent_analysis.get("required_agents", [])
        
        planning_prompt = f"""
        作为项目总监，请为以下用户需求制定详细的多Agent协作执行计划。

        用户需求：{user_message}
        
        对话背景：{context_summary}
        
        意图分析：{json.dumps(intent_analysis, ensure_ascii=False, indent=2)}

        可用团队成员及其能力：
        {json.dumps(self.agent_capabilities, ensure_ascii=False, indent=2)}

        请返回JSON格式的详细执行计划：
        {{
            "plan_id": "计划唯一ID",
            "description": "计划总体描述",
            "workflow_type": "工作流类型",  // sequential, parallel, iterative
            "steps": [
                {{
                    "step_id": "步骤唯一ID",
                    "agent_id": "负责的Agent ID",
                    "action": "具体执行动作",
                    "parameters": {{
                        "user_message": "传递给Agent的消息",
                        "context": "上下文信息",
                        "specific_requirements": "特定要求",
                        "director_guidance": "总监指导"
                    }},
                    "expected_output": "预期输出描述",
                    "dependencies": ["依赖的前置步骤ID"],
                    "parallel_group": "并行组ID（如果适用）",
                    "timeout": "超时时间（分钟）"
                }}
            ],
            "estimated_time": "总预估时间",
            "success_criteria": "成功完成的标准",
            "quality_checkpoints": ["质量检查点"],
            "fallback_plan": "备用方案"
        }}

        规划原则：
        1. 充分利用每个Agent的专业能力
        2. 合理安排任务依赖关系
        3. 考虑并行执行的可能性
        4. 设置质量检查点
        5. 预留容错和调整空间
        6. 确保最终输出符合用户期望
        """
        
        response = await self._call_llm(planning_prompt)
        
        try:
            plan = json.loads(response)
            # 为计划添加时间戳和会话信息
            plan["created_at"] = self._get_timestamp()
            plan["session_id"] = self.session_id
            plan["director_id"] = self.agent_id
            return plan
        except:
            # 生成失败时的备用计划
            return self._generate_fallback_plan(user_message, required_agents, context_summary)
    
    def _generate_fallback_plan(self, user_message: str, required_agents: List[str], context_summary: str) -> dict:
        """生成备用执行计划"""
        return {
            "plan_id": f"fallback_plan_{self._get_timestamp()}",
            "description": "生成详细计划失败，使用顺序执行模式",
            "workflow_type": "sequential",
            "steps": [
                {
                    "step_id": f"step_{i+1}",
                    "agent_id": agent_id,
                    "action": "process_user_request",
                    "parameters": {
                        "user_message": user_message,
                        "context": context_summary,
                        "director_guidance": self._generate_agent_guidance(agent_id, user_message)
                    },
                    "expected_output": f"{self.agent_capabilities.get(agent_id, {}).get('name', agent_id)}的处理结果",
                    "dependencies": [f"step_{i}"] if i > 0 else [],
                    "timeout": 10
                }
                for i, agent_id in enumerate(required_agents)
            ],
            "estimated_time": f"{len(required_agents) * 5}分钟",
            "success_criteria": "完成用户需求",
            "quality_checkpoints": ["每步完成后检查"],
            "fallback_plan": "如遇问题，转为人工协助",
            "created_at": self._get_timestamp(),
            "session_id": self.session_id,
            "director_id": self.agent_id
        }
    
    def _build_context_summary(self) -> str:
        """构建对话上下文摘要"""
        if not self.conversation_context:
            return "这是我们对话的开始"
        
        # 获取最近的几轮对话
        recent_context = self.conversation_context[-6:]  # 最近3轮对话
        
        summary_parts = []
        for ctx in recent_context:
            role = "用户" if ctx["role"] == "user" else "我"
            content = ctx["content"][:200] + "..." if len(ctx["content"]) > 200 else ctx["content"]
            summary_parts.append(f"[{role}]: {content}")
        
        return "\n".join(summary_parts)
    
    def _suggest_follow_up_services(self, intent_analysis: dict) -> List[str]:
        """根据意图分析建议后续服务"""
        services = []
        user_goal = intent_analysis.get("user_goal", "").lower()
        
        if "案例" in user_goal or "参考" in user_goal:
            services.append("案例专家可以为您搜索更多相关案例和最佳实践")
        
        if "数据" in user_goal or "分析" in user_goal or "指标" in user_goal:
            services.append("数据分析师可以为您进行深度数据分析和指标设计")
        
        if "写作" in user_goal or "撰写" in user_goal or "内容" in user_goal:
            services.append("写作专家可以协助您完成具体的写作和内容创作任务")
        
        if "文档" in user_goal or "文件" in user_goal:
            services.append("文档专家可以帮您处理和管理相关文档资料")
        
        if "审核" in user_goal or "检查" in user_goal or "质量" in user_goal:
            services.append("总编辑可以为您进行专业的内容审核和质量把控")
        
        return services
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async def _handle_report_structure(self, user_message: str, intent_analysis: dict) -> dict:
        """
        处理报告结构相关的请求
        """
        context_summary = self._build_context_summary()
        
        structure_prompt = f"""
        作为项目总监和报告结构设计专家，请处理关于报告结构的需求。

        用户需求：{user_message}
        
        对话背景：{context_summary}
        
        意图分析：{json.dumps(intent_analysis, ensure_ascii=False, indent=2)}
        
        当前报告模板：{json.dumps(self.report_template, ensure_ascii=False, indent=2)}

        请基于以下方面提供专业的报告结构建议：
        1. 报告整体框架设计
        2. 章节逻辑关系
        3. 内容层次结构
        4. 指标体系设计
        5. 格式规范要求

        如果需要具体的结构设计或模板制定，我可以协调写作专家和总编辑来完成详细的设计工作。
        """
        
        response = await self._call_llm(structure_prompt)
        
        return {
            "success": True,
            "message": response,
            "agent_id": self.agent_id,
            "response_type": "structure_guidance",
            "next_actions": [],
            "suggested_agents": ["writer_expert", "chief_editor"]
        }
    
    async def _handle_general_communication(self, user_message: str, intent_analysis: dict) -> dict:
        """
        处理一般性沟通
        """
        context_summary = self._build_context_summary()
        
        communication_prompt = f"""
        作为友好专业的项目总监，请与用户进行自然的沟通交流。

        用户消息：{user_message}
        
        对话背景：{context_summary}
        
        意图分析：{json.dumps(intent_analysis, ensure_ascii=False, indent=2)}

        请保持以下沟通风格：
        1. 专业而友好的态度
        2. 主动了解用户需求
        3. 提供有价值的建议
        4. 引导用户明确具体需求
        5. 介绍团队能提供的服务

        如果用户需求不够明确，请友好地询问更多细节，以便为其提供更好的服务。
        """
        
        response = await self._call_llm(communication_prompt)
        
        return {
            "success": True,
            "message": response,
            "agent_id": self.agent_id,
            "response_type": "communication",
            "next_actions": []
        }
    
    def get_work_context(self) -> dict:
        """获取工作上下文"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "current_report_structure": self.current_report_structure,
            "active_tasks": self.active_tasks,
            "report_template": self.report_template,
            "conversation_context": self.conversation_context[-10:],  # 最近10轮对话
            "agent_capabilities": self.agent_capabilities,
            "planner_status": {
                "current_goal": self.planner.plan.goal if self.planner.plan else None,
                "active_tasks": len(self.active_tasks)
            },
            "knowledge_base": self.knowledge_base
        }
    
    async def update_plan(self, new_goal: str) -> dict:
        """
        更新规划目标 - 借鉴MetaGPT的动态规划能力
        """
        try:
            await self.planner.update_plan(goal=new_goal)
            return {
                "success": True,
                "message": f"规划目标已更新为: {new_goal}",
                "new_goal": new_goal,
                "tasks": [task.dict() for task in self.planner.plan.tasks]
            }
        except Exception as e:
            logger.error(f"更新规划失败: {e}")
            return {
                "success": False,
                "message": f"更新规划失败: {str(e)}"
            }
    
    def get_current_plan_status(self) -> dict:
        """获取当前规划状态"""
        if not self.planner.plan:
            return {"status": "no_plan", "message": "当前没有活跃的规划"}
        
        return {
            "goal": self.planner.plan.goal,
            "current_task": self.planner.current_task.dict() if self.planner.current_task else None,
            "total_tasks": len(self.planner.plan.tasks),
            "completed_tasks": len([t for t in self.planner.plan.tasks if t.is_finished]),
            "progress": f"{len([t for t in self.planner.plan.tasks if t.is_finished])}/{len(self.planner.plan.tasks)}"
        }