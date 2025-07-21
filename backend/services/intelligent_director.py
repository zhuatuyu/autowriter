"""
智能项目总监 - 真正的人机协同报告写作系统
实现动态模板生成、迭代式开发和智能决策
"""
import asyncio
import json
import yaml
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
from queue import Queue

from metagpt.roles import Role
from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.logs import logger

from backend.tools.alibaba_search import alibaba_search_tool

class ConversationPhase(Enum):
    """对话阶段"""
    GREETING = "greeting"                    # 问候阶段
    REQUIREMENT_COLLECTION = "requirement_collection"  # 需求收集
    TEMPLATE_PROPOSAL = "template_proposal"  # 模板提议
    TEMPLATE_CONFIRMATION = "template_confirmation"  # 模板确认
    CHAPTER_WRITING = "chapter_writing"      # 章节写作
    USER_FEEDBACK = "user_feedback"          # 用户反馈
    ITERATION = "iteration"                  # 迭代改进
    COMPLETION = "completion"                # 完成阶段

class ChapterState(Enum):
    """章节状态"""
    PLANNED = "planned"          # 已规划
    IN_PROGRESS = "in_progress"  # 进行中
    DRAFT_READY = "draft_ready"  # 草稿完成
    USER_REVIEWING = "user_reviewing"  # 用户评审中
    APPROVED = "approved"        # 已批准
    NEEDS_REVISION = "needs_revision"  # 需要修订

class ExpertType(Enum):
    """专家类型"""
    DATA_ANALYST = "data_analyst"        # 数据分析师
    POLICY_RESEARCHER = "policy_researcher"  # 政策研究员
    CASE_RESEARCHER = "case_researcher"   # 案例研究员
    INDICATOR_EXPERT = "indicator_expert" # 指标专家
    WRITER = "writer"                    # 写作专员
    REVIEWER = "reviewer"                # 质量评审员

@dataclass
class ChapterTask:
    """章节任务"""
    chapter_id: str
    title: str
    description: str
    assigned_experts: List[ExpertType]
    requirements: List[str]
    reference_materials: List[str]
    status: ChapterState = ChapterState.PLANNED
    draft_content: str = ""
    user_feedback: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.user_feedback is None:
            self.user_feedback = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass
class DynamicTemplate:
    """动态模板 - 支持迭代和实时调整"""
    report_title: str
    report_type: str
    chapters: List[ChapterTask]
    current_chapter_index: int = 0
    user_requirements: List[str] = None
    reference_files: List[str] = None
    iteration_count: int = 1
    mvp_scope: str = "minimal"  # minimal, extended, full
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.user_requirements is None:
            self.user_requirements = []
        if self.reference_files is None:
            self.reference_files = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_yaml(self) -> str:
        """转换为YAML格式"""
        chapters_data = []
        for chapter in self.chapters:
            chapter_dict = {
                'id': chapter.chapter_id,
                'title': chapter.title,
                'description': chapter.description,
                'assigned_experts': [expert.value for expert in chapter.assigned_experts],
                'requirements': chapter.requirements,
                'reference_materials': chapter.reference_materials,
                'status': chapter.status.value,
                'draft_content': chapter.draft_content,
                'user_feedback': chapter.user_feedback,
                'created_at': chapter.created_at.isoformat(),
                'updated_at': chapter.updated_at.isoformat()
            }
            chapters_data.append(chapter_dict)
        
        data = {
            'name': self.report_title,
            'type': self.report_type,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'iteration_count': self.iteration_count,
            'mvp_scope': self.mvp_scope,
            'user_requirements': self.user_requirements,
            'reference_files': self.reference_files,
            'current_chapter_index': self.current_chapter_index,
            'chapters': chapters_data
        }
        return yaml.dump(data, allow_unicode=True, default_flow_style=False)
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'DynamicTemplate':
        """从YAML创建模板"""
        data = yaml.safe_load(yaml_content)
        
        chapters = []
        for chapter_data in data.get('chapters', []):
            chapter = ChapterTask(
                chapter_id=chapter_data['id'],
                title=chapter_data['title'],
                description=chapter_data['description'],
                assigned_experts=[ExpertType(expert) for expert in chapter_data['assigned_experts']],
                requirements=chapter_data['requirements'],
                reference_materials=chapter_data['reference_materials'],
                status=ChapterState(chapter_data['status']),
                draft_content=chapter_data.get('draft_content', ''),
                user_feedback=chapter_data.get('user_feedback', []),
                created_at=datetime.fromisoformat(chapter_data['created_at']),
                updated_at=datetime.fromisoformat(chapter_data['updated_at'])
            )
            chapters.append(chapter)
        
        return cls(
            report_title=data['name'],
            report_type=data['type'],
            chapters=chapters,
            current_chapter_index=data.get('current_chapter_index', 0),
            iteration_count=data.get('iteration_count', 1),
            mvp_scope=data.get('mvp_scope', 'minimal'),
            user_requirements=data.get('user_requirements', []),
            reference_files=data.get('reference_files', []),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )
    
    def get_current_chapter(self) -> Optional[ChapterTask]:
        """获取当前章节"""
        if 0 <= self.current_chapter_index < len(self.chapters):
            return self.chapters[self.current_chapter_index]
        return None
    
    def add_chapter(self, title: str, description: str, experts: List[ExpertType]) -> ChapterTask:
        """添加新章节"""
        chapter = ChapterTask(
            chapter_id=f"chapter_{len(self.chapters) + 1}",
            title=title,
            description=description,
            assigned_experts=experts,
            requirements=[],
            reference_materials=[]
        )
        self.chapters.append(chapter)
        return chapter
    
    def expand_scope(self, new_requirements: List[str]):
        """扩展报告范围"""
        self.user_requirements.extend(new_requirements)
        if self.mvp_scope == "minimal":
            self.mvp_scope = "extended"
        elif self.mvp_scope == "extended":
            self.mvp_scope = "full"
        self.iteration_count += 1
        self.updated_at = datetime.now()

class IntelligentTemplatePlanner:
    """智能模板规划器 - 使用LLM分析用户需求并生成动态、可迭代的报告结构"""
    
    def __init__(self, llm):
        self.llm = llm

    async def generate_template(self, user_input: str) -> DynamicTemplate:
        """使用LLM生成动态模板"""
        prompt = f"""
        作为一名顶级的项目总监，请仔细分析用户的需求，并为他们量身定制一份专业的报告写作方案。

        ## 用户原始需求
        "{user_input}"

        ## 你的任务
        1.  **理解意图**: 分析用户想要撰写什么类型的报告，主题是什么。
        2.  **规划结构**: 设计一个符合专业标准、逻辑清晰的 **最小可行（MVP）** 报告大纲。只需包含2-3个最重要的核心章节，确保能够快速启动项目。
        3.  **分配专家**: 为每个章节分配合适的专家团队。专家类型必须从以下列表中选择: {', '.join([e.value for e in ExpertType])}
        4.  **生成JSON**: 将你的规划方案严格按照以下JSON格式输出，不要添加任何额外的解释或说明。

        ## JSON输出格式
        {{
          "report_title": "一个高度概括、专业的报告标题",
          "report_type": "从'绩效评价', '调研报告', '政策分析'中选择最恰当的类型",
          "chapters": [
            {{
              "title": "第一章的标题",
              "description": "用一句话精准描述本章的核心写作任务和目标",
              "experts": ["expert_type_1", "expert_type_2"]
            }},
            {{
              "title": "第二章的标题",
              "description": "用一句话精准描述本章的核心写作任务和目标",
              "experts": ["expert_type_1", "expert_type_2"]
            }}
          ]
        }}
        """
        
        try:
            response_json_str = await self.llm.aask(prompt)
            # 清理可能的Markdown代码块标记
            cleaned_json_str = response_json_str.strip().replace('```json', '').replace('```', '').strip()
            response_data = json.loads(cleaned_json_str)

            chapters = []
            for i, ch_data in enumerate(response_data.get("chapters", [])):
                chapter = ChapterTask(
                    chapter_id=f"chapter_{i+1}",
                    title=ch_data["title"],
                    description=ch_data["description"],
                    assigned_experts=[ExpertType(expert) for expert in ch_data["experts"]],
                    requirements=[ch_data["description"]],  # 初始需求与描述一致
                    reference_materials=[]
                )
                chapters.append(chapter)
            
            return DynamicTemplate(
                report_title=response_data["report_title"],
                report_type=response_data["report_type"],
                chapters=chapters,
                user_requirements=[user_input]
            )

        except Exception as e:
            logger.error(f"❌ LLM生成模板失败: {e}. Raw response: {response_json_str}")
            # 创建一个安全的备用模板
            return DynamicTemplate(
                report_title="智能报告（备用方案）",
                report_type="综合报告",
                chapters=[ChapterTask(chapter_id="chapter_1", title="核心分析", description="根据用户需求进行核心内容分析", assigned_experts=[ExpertType.WRITER], requirements=[], reference_materials=[])],
                user_requirements=[user_input]
            )


class IntelligentProjectDirector(Role):
    """智能项目总监 - 真正的动态协作者"""
    
    def __init__(self, session_id: str, project_name: str, message_queue: Queue):
        super().__init__(
            name="智能项目总监",
            profile="Intelligent Project Director",
            goal="与用户深度协作，动态调整策略，打造完美报告",
            constraints="始终以用户需求为中心，保持智能决策和持续对话"
        )
        
        # 确保 Role 被正确初始化，拥有 self.llm
        # 如果 self.llm 没有被父类初始化，需要在这里手动处理
        if not hasattr(self, 'llm') or not self.llm:
            from metagpt.provider.llm import LLM
            self.llm = LLM()

        self.session_id = session_id
        self.project_name = project_name
        self.message_queue = message_queue
        self.workspace_path = Path(f"workspaces/{self.project_name}")
        self.draft_path = self.workspace_path / "draft"
        self.files_path = self.workspace_path / "files"
        
        # 创建项目目录结构
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.draft_path.mkdir(exist_ok=True)
        self.files_path.mkdir(exist_ok=True)
        
        # 初始化状态
        self.current_phase = ConversationPhase.GREETING
        self.dynamic_template: Optional[DynamicTemplate] = None
        self.conversation_history = []
        self.pending_user_input = False
        self.template_planner = IntelligentTemplatePlanner(self.llm)
        
        # 专家团队配置
        self.expert_descriptions = {
            ExpertType.DATA_ANALYST: "数据分析师 - 负责数据收集、统计分析和图表制作",
            ExpertType.POLICY_RESEARCHER: "政策研究员 - 负责政策背景研究和政策建议",
            ExpertType.CASE_RESEARCHER: "案例研究员 - 负责案例收集和分析",
            ExpertType.INDICATOR_EXPERT: "指标专家 - 负责评价指标体系设计",
            ExpertType.WRITER: "写作专员 - 负责文本写作和语言润色",
            ExpertType.REVIEWER: "质量评审员 - 负责内容审核和质量把控"
        }
        
        # 加载已有模板（如果存在）
        self._load_existing_template()

    async def _act(self) -> Message:
        """执行智能决策"""
        try:
            # 根据当前阶段执行相应的行为
            if self.current_phase == ConversationPhase.GREETING:
                return await self._handle_greeting()
            elif self.current_phase == ConversationPhase.REQUIREMENT_COLLECTION:
                return await self._handle_requirement_collection()
            elif self.current_phase == ConversationPhase.TEMPLATE_PROPOSAL:
                return await self._handle_template_proposal()
            elif self.current_phase == ConversationPhase.CHAPTER_WRITING:
                return await self._handle_chapter_writing()
            elif self.current_phase == ConversationPhase.USER_FEEDBACK:
                return await self._handle_user_feedback()
            elif self.current_phase == ConversationPhase.COMPLETION:
                return await self._handle_completion()
            else:
                return await self._handle_default()
                
        except Exception as e:
            error_msg = f"❌ 项目总监执行失败：{str(e)}"
            logger.error(error_msg, exc_info=True)
            self._send_message(error_msg, "error")
            return Message(content=error_msg, role=self.profile)

    async def _handle_greeting(self) -> Message:
        """处理问候阶段 - 更加人性化和智能"""
        greeting = """👋 您好！我是您的智能项目总监 🤖

我采用**真正的人机协同模式**，特点：

🎯 **动态适应**：根据您的需求实时调整策略
📋 **最小可行**：从简单结构开始，逐步完善  
🔄 **迭代开发**：像开发软件一样编写报告
👥 **专家团队**：6位专业AI专家为您服务
💬 **持续对话**：每个关键节点都会征求您的意见

---

请告诉我：
1. **报告主题**：您想写什么报告？
2. **基本需求**：有什么特殊要求？
3. **参考资料**：可以上传参考文件

💡 **不用担心描述不够详细**，我们会在过程中不断完善！"""
        
        self._send_message(greeting, "waiting_for_response")
        self.current_phase = ConversationPhase.REQUIREMENT_COLLECTION
        self._record_conversation("director", greeting)
        
        return Message(content=greeting, role=self.profile)

    async def _handle_requirement_collection(self) -> Message:
        """处理需求收集阶段 - 智能引导用户"""
        # 检查是否有足够的信息生成初始模板
        if self._has_sufficient_requirements():
            self.current_phase = ConversationPhase.TEMPLATE_PROPOSAL
            return await self._handle_template_proposal()
        else:
            # 智能生成引导问题
            question = self._generate_smart_question()
            self._send_message(question, "waiting_for_response")
            return Message(content=question, role=self.profile)

    async def _handle_template_proposal(self) -> Message:
        """处理模板提议阶段 - 生成最小可行模板"""
        # 生成动态模板
        user_inputs = [msg['content'] for msg in self.conversation_history if msg['role'] == 'user']
        combined_input = ' '.join(user_inputs)
        
        template = await self.template_planner.generate_template(combined_input)
        
        self.dynamic_template = template
        
        # 保存模板到工作空间
        self._save_template()
        
        # 使用LLM生成向用户展示模板的回复
        proposal_prompt = f"""
        你是一位非常专业且善于沟通的智能项目总监。你刚刚为用户精心策划了一份报告的初始写作方案。

        ## 你的任务
        向用户清晰、友好地展示这份方案，并引导他们进行下一步操作。

        ## 方案详情
        - **报告标题**: {template.report_title}
        - **报告类型**: {template.report_type}
        - **核心章节**:
        {self._format_chapter_list_with_experts(template.chapters)}

        ## 沟通要点
        1.  **开场**: 热情地告诉用户，你已经根据他们的需求制定了方案。
        2.  **展示方案**: 清晰地列出报告标题、类型和章节结构。
        3.  **强调MVP理念**: 解释这只是一个“最小可行”的初步框架，重点是快速启动并确保方向正确。告诉用户，后续可以随时调整、增加或修改。
        4.  **征求意见**: 礼貌地询问用户对这个方案的看法，例如：“您觉得这个初步的结构怎么样？”或“我们可以先从第一章开始吗？”
        5.  **明确下一步**: 给出清晰的指令，例如：“如果您同意，请回复‘开始’，我将立即组织专家团队投入工作！”

        请生成你的回复。
        """
        proposal = await self.llm.aask(proposal_prompt)
        
        self._send_message(proposal, "waiting_for_response")
        self.current_phase = ConversationPhase.TEMPLATE_CONFIRMATION
        self._record_conversation("director", proposal)
        
        return Message(content=proposal, role=self.profile)

    async def _handle_chapter_writing(self) -> Message:
        """处理章节写作阶段 - 协调专家团队"""
        if not self.dynamic_template:
            return Message(content="❌ 模板未初始化", role=self.profile)
        
        current_chapter = self.dynamic_template.get_current_chapter()
        if not current_chapter:
            # 所有章节完成
            self.current_phase = ConversationPhase.COMPLETION
            return await self._handle_completion()
        
        # 更新章节状态
        current_chapter.status = ChapterState.IN_PROGRESS
        current_chapter.updated_at = datetime.now()
        self._save_template()
        
        # 分配专家写作当前章节
        experts_info = [self.expert_descriptions[expert] for expert in current_chapter.assigned_experts]
        
        writing_msg = f"""🚀 **开始写作第{self.dynamic_template.current_chapter_index + 1}章**

**📖 章节信息**：
- **标题**：《{current_chapter.title}》
- **要求**：{current_chapter.description}

**👥 专家团队**：
{chr(10).join(f"• {expert}" for expert in experts_info)}

**🔄 工作流程**：
1. 📊 数据分析师收集相关数据和资料
2. 🔍 研究员进行深度分析  
3. ✍️ 写作专员完成初稿
4. 🔍 质量评审员进行审核

⏱️ **预计时间**：3-5分钟
📝 **完成后**：我会请您审阅并提供反馈

正在协调专家团队开始工作... 🎯"""
        
        self._send_message(writing_msg, "writing")
        
        # 模拟专家写作过程
        await self._simulate_expert_writing(current_chapter)
        
        # _simulate_expert_writing 是异步的，所以这里不立即返回
        # 而是等待模拟任务完成后，由其内部逻辑发送消息并更新状态
        return Message(content=writing_msg, role=self.profile)

    async def _simulate_expert_writing(self, chapter: ChapterTask):
        """模拟并执行专家写作过程，集成搜索和LLM"""
        try:
            # 步骤1: 资料收集（搜索）
            search_query = f"{self.dynamic_template.report_title} {chapter.title} 相关政策、数据和案例分析"
            self._send_message(f"🔍 案例研究员: 正在围绕 “{search_query}” 进行网络搜索...", "writing")
            await asyncio.sleep(1) # 模拟思考
            
            # 异步执行搜索
            search_results = await alibaba_search_tool.run(search_query)
            self._send_message(f"📝 写作专员: 已整合搜索到的 {len(search_results.splitlines())} 条相关资料，开始撰写初稿...", "writing")
            await asyncio.sleep(1) # 模拟整合
            
            # 步骤2: 调用LLM生成内容并保存
            generated_content = await self._generate_chapter_content_with_llm(chapter, search_results)
            
            # 将内容保存到文件，并用路径更新模板
            draft_file_path = self.draft_path / f"{chapter.chapter_id}.md"
            with open(draft_file_path, "w", encoding="utf-8") as f:
                f.write(generated_content)
            
            chapter.draft_content = f"draft/{chapter.chapter_id}.md" # 存入相对路径
            chapter.status = ChapterState.DRAFT_READY
            chapter.updated_at = datetime.now()
            self._save_template()
            
            # 步骤3: 发送完成消息
            await asyncio.sleep(1)
            
            completion_prompt = f"""
            你是一位智能项目总监。你的AI专家团队刚刚完成了报告的其中一章。

            ## 章节信息
            - **章节标题**: 《{chapter.title}》
            - **内容预览**: {generated_content[:200]}...

            ## 你的任务
            向用户报告这个好消息。你的回复应该包括：
            1.  清晰地告知哪个章节已完成。
            2.  附上内容预览，让用户对产出有初步了解。
            3.  主动、清晰地询问用户反馈，例如：“请您审阅一下，内容是否符合您的期望？”
            4.  提供明确的下一步操作选项，例如：回复“满意”继续下一章，或者直接提出修改意见。
            """
            completion_msg = await self.llm.aask(completion_prompt)

            self._send_message(completion_msg, "waiting_for_response")
            self.current_phase = ConversationPhase.USER_FEEDBACK
            
        except Exception as e:
            error_msg = f"❌ 专家写作过程出错：{str(e)}"
            logger.error(error_msg, exc_info=True)
            self._send_message(error_msg, "error")

    async def _generate_chapter_content_with_llm(self, chapter: ChapterTask, search_results: str) -> str:
        """使用LLM生成章节内容"""
        prompt = f"""
        你是一位顶级的行业分析师和报告撰写专家。你的任务是为一个关于 **"{self.dynamic_template.report_title}"** 的 **{self.dynamic_template.report_type}** 撰写关键章节。

        ## 报告的 overarching 目标与要求
        {', '.join(self.dynamic_template.user_requirements)}

        ## 当前章节的核心任务
        - **章节标题**: **{chapter.title}**
        - **必须达成的目标**: {chapter.description}
        - **需要包含的要点**: {', '.join(chapter.requirements)}

        ## 关键参考资料（源自网络搜索）
        ---
        {search_results[:3000]}
        ---

        ## 你的写作指令
        1.  **深度整合**: 请勿罗列搜索结果。你必须深度理解、分析并**融合**上述“关键参考资料”中的信息，以支撑你的观点和分析。
        2.  **聚焦任务**: 严格围绕“当前章节的核心任务”进行撰写，确保内容不偏离主题。
        3.  **展现专业性**: 使用专业、客观、精炼的语言。如果适用，可以提出数据、案例或政策作为论据。
        4.  **结构清晰**: 内容应有清晰的逻辑层次，可以使用小标题来组织文章结构。
        5.  **直接输出**: 请直接开始撰写章节的正文，不要包含任何如“好的，这是您要的内容”之类的开场白或总结。

        现在，请开始撰写 **{chapter.title}** 章节。
        """
        
        content = await self.llm.aask(prompt)
        return content

    async def _handle_user_feedback(self) -> Message:
        """处理用户反馈阶段"""
        if not self.dynamic_template:
            return Message(content="❌ 模板未初始化", role=self.profile)
        
        current_chapter = self.dynamic_template.get_current_chapter()
        if not current_chapter:
            return Message(content="❌ 当前章节不存在", role=self.profile)

        feedback_prompt = f"""
        你是一位智能项目总监。你正在等待用户对刚刚完成的章节《{current_chapter.title}》提供反馈。

        ## 你的任务
        撰写一条信息，友好地提示用户，并清晰地告知他们可以执行的操作。

        ## 沟通要点
        1.  **点明状态**: 温和地提醒用户，你正在等待他们对当前章节的反馈。
        2.  **提供选项**: 清晰地列出用户可以选择的操作，例如：
            -   如果满意，可以回复“满意”或“继续”，以进入下一章。
            -   如果不满意，可以直接输入具体的修改意见。
            -   还可以“调整结构”或“上传文件”来提供更多信息。
        3.  **鼓励合作**: 传递出一种乐于修改、持续协作的积极态度。
        """
        feedback_msg = await self.llm.aask(feedback_prompt)
        
        self._send_message(feedback_msg, "waiting_for_response")
        return Message(content=feedback_msg, role=self.profile)

    async def _handle_completion(self) -> Message:
        """处理完成阶段"""
        if not self.dynamic_template:
            return Message(content="❌ 模板未初始化", role=self.profile)

        completion_msg = f"""🎉 **恭喜！报告写作完成！**

**📊 项目统计**：
- **报告标题**：{self.dynamic_template.report_title}
- **报告类型**：{self.dynamic_template.report_type}
- **总章节数**：{len(self.dynamic_template.chapters)}
- **迭代次数**：{self.dynamic_template.iteration_count}
- **完成时间**：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}

**📋 章节概览**：
{self._format_completed_chapters()}

**📁 文件输出**：
- 报告已保存到：`workspaces/{self.project_name}/`
- 模板文件：`dynamic_template.yaml`
- 最终报告：`report.md`

**🌟 感谢您的配合！**
这种人机协同的方式让我们打造了一份真正符合您需求的报告。如果需要进一步调整，随时可以继续对话！"""
        
        self._send_message(completion_msg, "completed")
        
        # 拼接所有章节内容
        final_content = f"# {self.dynamic_template.report_title}\n\n"
        final_content += f"**报告类型**：{self.dynamic_template.report_type}\n"
        final_content += f"**生成时间**：{datetime.now().strftime('%Y年%m月%d日')}\n\n"
        
        for i, chapter in enumerate(self.dynamic_template.chapters):
            final_content += f"\n## {i+1}. {chapter.title}\n\n"
            # 读取草稿文件并添加到最终报告中
            draft_file_path = self.workspace_path / chapter.draft_content
            if draft_file_path.exists():
                with open(draft_file_path, 'r', encoding='utf-8') as f:
                    final_content += f.read() + "\n\n"
            else:
                final_content += "（草稿文件未找到）\n\n"
            
        # 保存最终报告
        report_path = self.workspace_path / "report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        
        return Message(content=completion_msg, role=self.profile)

    def handle_user_input(self, user_input: str, uploaded_files: List[str] = None):
        """处理用户输入 - 智能理解用户意图"""
        logger.info(f"💬 收到用户输入：{user_input[:50]}...")
        
        self._record_conversation("user", user_input)
        
        # 处理上传的文件
        if uploaded_files:
            self._process_uploaded_files(uploaded_files)
        
        # 根据当前阶段智能处理输入
        if self.current_phase == ConversationPhase.REQUIREMENT_COLLECTION:
            self._process_requirement_input(user_input)
        elif self.current_phase == ConversationPhase.TEMPLATE_CONFIRMATION:
            self._process_template_confirmation(user_input)
        elif self.current_phase == ConversationPhase.USER_FEEDBACK:
            self._process_user_feedback(user_input)
        
        self.pending_user_input = False

    def _process_requirement_input(self, user_input: str):
        """处理需求输入 - 智能收集信息"""
        # 提取关键信息
        if self.dynamic_template is None:
            # 首次输入，初始化需求列表
            if not hasattr(self, 'collected_requirements'):
                self.collected_requirements = []
            
            self.collected_requirements.append(user_input)
        
        logger.info(f"�� 需求收集：{user_input[:50]}...")

    def _process_template_confirmation(self, user_input: str):
        """处理模板确认"""
        input_lower = user_input.lower()
        
        if any(word in input_lower for word in ['开始', '确认', '同意', '可以', 'ok', '好的']):
            # 用户确认，开始写作
            self.current_phase = ConversationPhase.CHAPTER_WRITING
            self._send_message("✅ 收到确认！开始组织专家团队写作第一章...", "info")
            
        elif any(word in input_lower for word in ['修改', '调整', '不行', '不对', '改']):
            # 用户要求修改模板
            self._adjust_template_based_on_feedback(user_input)
            self._send_message("🔄 正在根据您的要求调整模板...", "info")
            
        else:
            # 不明确的回复，询问明确意图
            clarify_msg = """🤔 **请明确您的意图**：

- 回复"**开始**" - 确认当前结构，开始写作
- 回复"**修改**" - 调整报告结构  
- 具体说明需要怎样调整

我会根据您的回复进行相应处理。"""
            
            self._send_message(clarify_msg, "waiting_for_response")

    def _process_user_feedback(self, user_input: str):
        """处理用户反馈 - 智能分析反馈类型"""
        input_lower = user_input.lower()
        
        if any(word in input_lower for word in ['满意', '可以', '继续', '下一章', '好的', 'ok']):
            # 用户满意，继续下一章
            self._move_to_next_chapter()
            self.current_phase = ConversationPhase.CHAPTER_WRITING
            self._send_message("✅ 很好！继续下一章节...", "info")
            
        elif any(word in input_lower for word in ['修改', '调整', '不满意', '重写']):
            # 需要修改当前章节
            self._revise_current_chapter(user_input)
            
        elif any(word in input_lower for word in ['扩展', '增加', '更多']):
            # 用户希望扩展内容
            self._expand_current_chapter(user_input)
            
        else:
            # 当作具体的修改意见处理
            self._revise_current_chapter(user_input)

    def _move_to_next_chapter(self):
        """移动到下一章节"""
        if self.dynamic_template:
            current_chapter = self.dynamic_template.get_current_chapter()
            if current_chapter:
                current_chapter.status = ChapterState.APPROVED
                current_chapter.updated_at = datetime.now()
            
            self.dynamic_template.current_chapter_index += 1
            self._save_template()
            
            logger.info(f"📈 移动到第{self.dynamic_template.current_chapter_index + 1}章")

    def _adjust_template_based_on_feedback(self, feedback: str):
        """根据反馈调整模板"""
        # 这里应该用LLM分析反馈并智能调整模板
        # 临时实现：记录反馈并提示手动调整
        
        if self.dynamic_template:
            self.dynamic_template.user_requirements.append(f"模板调整：{feedback}")
            self.dynamic_template.updated_at = datetime.now()
            self._save_template()
        
        logger.info(f"🔄 模板调整请求：{feedback[:50]}...")

    def _revise_current_chapter(self, feedback: str):
        """修订当前章节"""
        if not self.dynamic_template:
            return
        
        current_chapter = self.dynamic_template.get_current_chapter()
        if current_chapter:
            # 记录用户反馈
            current_chapter.user_feedback.append(feedback)
            current_chapter.status = ChapterState.NEEDS_REVISION
            current_chapter.updated_at = datetime.now()
            self._save_template()
            
            # 发送修订中的消息
            revision_msg = f"""🔄 **开始修订第{self.dynamic_template.current_chapter_index + 1}章**

**反馈内容**：{feedback}

**修订计划**：
1. 分析您的具体要求
2. 调整章节内容和结构
3. 重新组织专家团队完善内容
4. 生成修订版本供您审阅

⏱️ 预计修订时间：2-3分钟
📝 修订完成后会再次请您确认..."""
            
            self._send_message(revision_msg, "revising")
            
            # 模拟修订过程
            asyncio.create_task(self._simulate_revision(current_chapter, feedback))

    async def _simulate_revision(self, chapter: ChapterTask, feedback: str):
        """模拟修订过程，集成LLM"""
        try:
            self._send_message(f"收到您的反馈，正在分析并组织专家团队进行修订...", "revising")
            await asyncio.sleep(1)  # 模拟思考时间
            
            # 读取原始草稿内容
            original_content = ""
            if chapter.draft_content and (self.workspace_path / chapter.draft_content).exists():
                with open(self.workspace_path / chapter.draft_content, "r", encoding="utf-8") as f:
                    original_content = f.read()
            else:
                logger.warning(f"无法找到草稿文件：{chapter.draft_content}，将基于空内容进行修订。")

            # 调用LLM修订内容
            revised_content = await self._revise_chapter_content_with_llm(chapter, original_content, feedback)
            
            # 将修订后的内容写回文件
            draft_file_path = self.workspace_path / chapter.draft_content
            with open(draft_file_path, "w", encoding="utf-8") as f:
                f.write(revised_content)
                
            chapter.status = ChapterState.DRAFT_READY
            chapter.updated_at = datetime.now()
            self._save_template()
            
            # 发送修订完成消息
            await asyncio.sleep(1)

            revision_complete_prompt = f"""
            你是一位智能项目总监。你的AI团队已根据用户的反馈，对章节《{chapter.title}》进行了修订。

            ## 修订后内容预览
            {revised_content[:200]}...

            ## 你的任务
            向用户报告修订已完成。你的信息应：
            1.  告知章节已根据他们的意见完成修订。
            2.  提供修订后的内容预览。
            3.  再次礼貌地征求用户的确认，询问新版本是否满足要求。
            4.  给出明确的下一步指令（例如：回复“满意”以继续）。
            """
            revision_complete_msg = await self.llm.aask(revision_complete_prompt)
            
            self._send_message(revision_complete_msg, "waiting_for_response")
            self.current_phase = ConversationPhase.USER_FEEDBACK
            
        except Exception as e:
            error_msg = f"❌ 修订过程出错：{str(e)}"
            logger.error(error_msg, exc_info=True)
            self._send_message(error_msg, "error")

    async def _revise_chapter_content_with_llm(self, chapter: ChapterTask, original_content: str, feedback: str) -> str:
        """使用LLM修订章节内容"""
        prompt = f"""
        你是一位顶级的报告修改专家。你需要根据用户的反馈，对一个报告章节进行彻底的重写和优化。

        ## 报告的整体目标
        {', '.join(self.dynamic_template.user_requirements)}

        ## 需要修订的章节
        - **章节标题**: **{chapter.title}**

        ## 章节的原始版本
        ---
        {original_content}
        ---

        ## 用户的修改意见
        ---
        "{feedback}"
        ---

        ## 你的修订指令
        1.  **深刻理解反馈**: 准确把握用户的核心修改意图。用户的意见是最高指令。
        2.  **彻底重写**: 不要只做小修小补。请基于原始版本和用户反馈，对整个章节进行**全面重写**，以达到用户期望。
        3.  **保持专业**: 即使重写，也要确保内容的专业性、逻辑性和流畅性。
        4.  **直接输出**: 请直接输出重写后的章节正文，不要有任何如“好的，这是修改后的版本”之类的开场白。
        """
        
        revised_content = await self.llm.aask(prompt)
        return revised_content

    def _expand_current_chapter(self, expansion_request: str):
        """扩展当前章节"""
        if not self.dynamic_template:
            return
        
        current_chapter = self.dynamic_template.get_current_chapter()
        if current_chapter:
            # 记录扩展请求
            current_chapter.user_feedback.append(f"扩展请求：{expansion_request}")
            current_chapter.requirements.append(expansion_request)
            current_chapter.updated_at = datetime.now()
            self._save_template()
            
            expand_msg = f"""📈 **扩展第{self.dynamic_template.current_chapter_index + 1}章内容**

**扩展要求**：{expansion_request}

正在为您：
- 补充更多相关内容
- 增加数据和案例支撑
- 丰富分析维度

⏱️ 预计时间：2-3分钟
📝 完成后请您审阅扩展效果..."""
            
            self._send_message(expand_msg, "expanding")
            
            # 模拟扩展过程
            asyncio.create_task(self._simulate_expansion(current_chapter, expansion_request))

    async def _simulate_expansion(self, chapter: ChapterTask, expansion_request: str):
        """模拟扩展过程"""
        try:
            await asyncio.sleep(3)  # 模拟扩展时间
            
            # 扩展章节内容
            expanded_content = self._expand_chapter_content(chapter, expansion_request)
            chapter.draft_content = expanded_content
            chapter.status = ChapterState.DRAFT_READY
            chapter.updated_at = datetime.now()
            self._save_template()
            
            expansion_complete_msg = f"""✅ **第{self.dynamic_template.current_chapter_index + 1}章扩展完成！**

**扩展内容**：
- 新增了相关分析内容
- 补充了数据和案例
- 丰富了内容层次

**📊 内容统计**：
- 扩展前：约{len(chapter.draft_content)//2}字
- 扩展后：约{len(chapter.draft_content)}字

**📝 请审阅扩展效果**：
新的内容是否符合您的期望？"""
            
            self._send_message(expansion_complete_msg, "waiting_for_response")
            self.current_phase = ConversationPhase.USER_FEEDBACK
            
        except Exception as e:
            error_msg = f"❌ 扩展过程出错：{str(e)}"
            logger.error(error_msg)
            self._send_message(error_msg, "error")

    def _expand_chapter_content(self, chapter: ChapterTask, expansion_request: str) -> str:
        """扩展章节内容"""
        # 基于原内容进行扩展
        original_content = chapter.draft_content
        
        expanded_content = original_content + f"""

## 补充分析（根据您的要求）

### 扩展内容
根据您的要求"{expansion_request}"，我们进一步分析了以下方面：

#### 深入分析
通过更深入的研究和数据收集，我们发现...

#### 相关案例
以下案例能够更好地说明问题：
1. 案例一：...
2. 案例二：...

#### 数据支撑
最新的数据显示...

#### 进一步建议
基于扩展分析，我们建议...

---
*本部分为根据用户需求扩展的内容*
"""
        
        return expanded_content

    def _process_uploaded_files(self, files: List[str]):
        """处理上传的文件"""
        if self.dynamic_template:
            self.dynamic_template.reference_files.extend(files)
            self.dynamic_template.updated_at = datetime.now()
            self._save_template()
        
        # 发送文件处理确认
        files_msg = f"""📁 **文件上传成功！**

**已接收文件**：
{chr(10).join(f"• {file}" for file in files)}

**处理状态**：
✅ 文件已加入参考资料库
✅ 后续写作将参考这些材料
✅ 专家团队会充分利用这些信息

**💡 提示**：
这些文件将在当前章节和后续章节中被充分利用，确保报告内容更加准确和丰富。"""
        
        self._send_message(files_msg, "info")
        logger.info(f"📁 处理上传文件：{files}")

    def _has_sufficient_requirements(self) -> bool:
        """检查是否有足够的需求信息"""
        if not hasattr(self, 'collected_requirements'):
            return False
        
        # 简单检查：至少有一条需求输入
        return len(self.collected_requirements) >= 1

    def _generate_smart_question(self) -> str:
        """生成智能引导问题"""
        questions = [
            "💡 **请详细描述一下**：您想写什么类型的报告？比如绩效评价、调研报告、政策分析等？",
            "📋 **关于报告主题**：具体是关于哪个项目或领域的？请简单介绍一下背景。",
            "🎯 **报告用途**：这份报告主要用于什么场合？内部汇报、外部提交还是其他用途？",
            "📊 **内容要求**：您希望报告重点关注哪些方面？比如数据分析、问题诊断、建议措施等？",
            "📄 **格式要求**：报告大概需要多少页？有特定的格式要求吗？",
            "📁 **参考资料**：您有相关的参考报告、数据资料或模板可以分享吗？"
        ]
        
        # 根据对话轮次选择问题
        user_inputs = [msg for msg in self.conversation_history if msg['role'] == 'user']
        question_index = len(user_inputs) - 1
        
        if question_index < len(questions):
            return questions[question_index]
        else:
            return "💬 **还有其他要求吗？** 比如特殊的内容要求、格式规范或时间安排等，尽管告诉我！"

    def _format_chapter_list_with_experts(self, chapters: List[ChapterTask]) -> str:
        """格式化章节列表，包含专家信息"""
        result = ""
        for i, chapter in enumerate(chapters):
            experts = [self.expert_descriptions[expert].split(' - ')[0] for expert in chapter.assigned_experts]
            result += f"""
**第{i+1}章：{chapter.title}**
- 📝 内容：{chapter.description}
- 👥 负责专家：{', '.join(experts)}
- 🎯 要求：{', '.join(chapter.requirements[:2])}{'...' if len(chapter.requirements) > 2 else ''}
"""
        return result

    def _format_completed_chapters(self) -> str:
        """格式化已完成章节"""
        if not self.dynamic_template:
            return "无章节信息"
        
        result = ""
        for i, chapter in enumerate(self.dynamic_template.chapters):
            status_emoji = {
                ChapterState.APPROVED: "✅",
                ChapterState.DRAFT_READY: "📝", 
                ChapterState.IN_PROGRESS: "🔄",
                ChapterState.NEEDS_REVISION: "🔧",
                ChapterState.PLANNED: "📋"
            }.get(chapter.status, "❓")
            
            result += f"{status_emoji} 第{i+1}章：{chapter.title}\n"
        
        return result

    def _save_template(self):
        """保存模板到工作空间"""
        try:
            if self.dynamic_template:
                template_file = self.workspace_path / "dynamic_template.yaml"
                with open(template_file, 'w', encoding='utf-8') as f:
                    f.write(self.dynamic_template.to_yaml())
                logger.info(f"💾 模板已保存：{template_file}")
        except Exception as e:
            logger.error(f"❌ 保存模板失败：{e}")

    def _load_existing_template(self):
        """加载已有模板"""
        try:
            template_file = self.workspace_path / "dynamic_template.yaml"
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.dynamic_template = DynamicTemplate.from_yaml(content)
                logger.info(f"📂 已加载模板：{template_file}")
        except Exception as e:
            logger.error(f"❌ 加载模板失败：{e}")

    def _record_conversation(self, role: str, content: str):
        """记录对话历史"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })

    def _send_message(self, content: str, status: str):
        """发送消息"""
        if self.message_queue:
            self.message_queue.put({
                "agent_type": "project_director",
                "agent_name": "智能项目总监",
                "content": content,
                "status": status,
                "requires_user_input": status == "waiting_for_response",
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_default(self) -> Message:
        """默认处理"""
        return Message(content="🤖 智能项目总监待命中...", role=self.profile)

    def get_workspace_status(self) -> Dict:
        """获取工作空间状态"""
        template_file = self.workspace_path / "dynamic_template.yaml"
        
        status = {
            "session_id": self.session_id,
            "project_name": self.project_name,
            "current_phase": self.current_phase.value,
            "workspace_path": str(self.workspace_path),
            "template_exists": template_file.exists(),
            "conversation_count": len(self.conversation_history),
            "last_activity": datetime.now().isoformat()
        }
        
        if self.dynamic_template:
            approved_count = len([c for c in self.dynamic_template.chapters if c.status == ChapterState.APPROVED])
            status.update({
                "report_title": self.dynamic_template.report_title,
                "report_type": self.dynamic_template.report_type,
                "total_chapters": len(self.dynamic_template.chapters),
                "current_chapter_index": self.dynamic_template.current_chapter_index,
                "completed_chapters": approved_count,
                "progress_percentage": int((approved_count / len(self.dynamic_template.chapters)) * 100) if self.dynamic_template.chapters else 0,
                "iteration_count": self.dynamic_template.iteration_count,
                "mvp_scope": self.dynamic_template.mvp_scope
            })
        
        return status

# 全局实例管理
intelligent_directors: Dict[str, IntelligentProjectDirector] = {}