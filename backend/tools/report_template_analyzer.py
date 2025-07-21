"""
报告模板分析器
基于reportmodel.yaml构建写作蓝图和执行计划
"""
import yaml
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from metagpt.logs import logger

@dataclass
class ChapterInfo:
    """章节信息"""
    title: str
    chapter_code: str
    default_prompt_text: str
    writing_sequence_order: int
    is_indicator_driven: bool
    fixed_qa_ids: List[str]
    depends_on_chapter_codes: List[str]
    fixed_table_schema: Dict
    sub_chapters: List['ChapterInfo'] = None
    is_completed: bool = False
    
    def __post_init__(self):
        if self.sub_chapters is None:
            self.sub_chapters = []

class ReportTemplateAnalyzer:
    """报告模板分析器"""
    
    def __init__(self, template_path: str = "reportmodel.yaml"):
        self.template_path = template_path
        self.template_data = None
        self.chapters = {}
        self.writing_sequence = []
        self.load_template()
    
    def load_template(self):
        """加载模板文件"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                self.template_data = yaml.safe_load(f)
            
            self._parse_chapters()
            self._build_writing_sequence()
            logger.info(f"成功加载报告模板: {self.template_data.get('name', '未知模板')}")
            
        except Exception as e:
            logger.error(f"加载模板失败: {e}")
            raise
    
    def _parse_chapters(self):
        """解析章节结构"""
        if not self.template_data or 'chapters' not in self.template_data:
            return
        
        for chapter_data in self.template_data['chapters']:
            chapter = self._create_chapter_info(chapter_data)
            self.chapters[chapter.chapter_code] = chapter
    
    def _create_chapter_info(self, chapter_data: Dict) -> ChapterInfo:
        """创建章节信息对象"""
        # 解析固定问题列表
        fixed_qa_ids = []
        if chapter_data.get('fixed_qa_ids_json'):
            try:
                fixed_qa_ids = json.loads(chapter_data['fixed_qa_ids_json'])
            except:
                fixed_qa_ids = []
        
        # 解析依赖章节
        depends_on = []
        if chapter_data.get('depends_on_chapter_codes'):
            try:
                depends_on = json.loads(chapter_data['depends_on_chapter_codes'])
            except:
                depends_on = []
        
        # 解析表格结构
        table_schema = {}
        if chapter_data.get('fixed_table_schema_json'):
            try:
                table_schema = json.loads(chapter_data['fixed_table_schema_json'])
            except:
                table_schema = {}
        
        chapter = ChapterInfo(
            title=chapter_data.get('title', ''),
            chapter_code=chapter_data.get('chapter_code', ''),
            default_prompt_text=chapter_data.get('default_prompt_text', ''),
            writing_sequence_order=chapter_data.get('writing_sequence_order', 999),
            is_indicator_driven=chapter_data.get('is_indicator_driven', False),
            fixed_qa_ids=fixed_qa_ids,
            depends_on_chapter_codes=depends_on,
            fixed_table_schema=table_schema
        )
        
        # 处理子章节
        if 'sub_chapters' in chapter_data:
            for sub_chapter_data in chapter_data['sub_chapters']:
                sub_chapter = self._create_chapter_info(sub_chapter_data)
                chapter.sub_chapters.append(sub_chapter)
                # 同时将子章节添加到全局章节字典中
                self.chapters[sub_chapter.chapter_code] = sub_chapter
        
        return chapter
    
    def _build_writing_sequence(self):
        """构建写作顺序"""
        # 获取所有章节并按writing_sequence_order排序
        all_chapters = []
        
        def collect_chapters(chapter: ChapterInfo):
            all_chapters.append(chapter)
            for sub_chapter in chapter.sub_chapters:
                collect_chapters(sub_chapter)
        
        for chapter in self.chapters.values():
            if '.' not in chapter.chapter_code:  # 只处理顶级章节
                collect_chapters(chapter)
        
        # 按写作顺序排序
        self.writing_sequence = sorted(all_chapters, key=lambda x: x.writing_sequence_order)
        
        logger.info(f"构建写作顺序完成，共 {len(self.writing_sequence)} 个章节")
    
    def get_next_chapter_to_write(self) -> Optional[ChapterInfo]:
        """获取下一个需要写作的章节"""
        for chapter in self.writing_sequence:
            if not chapter.is_completed and self._check_dependencies_completed(chapter):
                return chapter
        return None
    
    def _check_dependencies_completed(self, chapter: ChapterInfo) -> bool:
        """检查章节依赖是否已完成"""
        for dep_code in chapter.depends_on_chapter_codes:
            if dep_code in self.chapters:
                if not self.chapters[dep_code].is_completed:
                    return False
        return True
    
    def mark_chapter_completed(self, chapter_code: str):
        """标记章节为已完成"""
        if chapter_code in self.chapters:
            self.chapters[chapter_code].is_completed = True
            logger.info(f"章节 {chapter_code} 标记为已完成")
    
    def get_chapter_writing_prompt(self, chapter: ChapterInfo, project_info: Dict) -> str:
        """生成章节写作提示"""
        prompt = f"""# 章节写作任务

## 章节信息
- 标题: {chapter.title}
- 章节代码: {chapter.chapter_code}
- 写作顺序: {chapter.writing_sequence_order}

## 项目信息
- 项目名称: {project_info.get('name', '未知项目')}
- 项目类型: {project_info.get('type', '绩效评价')}
- 预算规模: {project_info.get('budget', '待确定')}万元
- 资金来源: {project_info.get('funding_source', '财政资金')}

## 写作要求
{chapter.default_prompt_text}

"""
        
        # 添加必答问题
        if chapter.fixed_qa_ids:
            prompt += "## 必须回答的问题\n"
            for i, question in enumerate(chapter.fixed_qa_ids, 1):
                prompt += f"{i}. {question}\n"
            prompt += "\n"
        
        # 添加表格要求
        if chapter.fixed_table_schema:
            prompt += "## 表格格式要求\n"
            prompt += f"请按照以下表格结构组织数据：\n"
            if isinstance(chapter.fixed_table_schema, dict) and 'columns' in chapter.fixed_table_schema:
                columns = chapter.fixed_table_schema['columns']
                prompt += f"表格列: {', '.join(columns)}\n"
            else:
                for key, value in chapter.fixed_table_schema.items():
                    prompt += f"- {key}: {value}\n"
            prompt += "\n"
        
        # 添加依赖信息
        if chapter.depends_on_chapter_codes:
            prompt += "## 依赖章节\n"
            prompt += "本章节的写作需要参考以下已完成章节的内容：\n"
            for dep_code in chapter.depends_on_chapter_codes:
                if dep_code in self.chapters:
                    dep_chapter = self.chapters[dep_code]
                    prompt += f"- {dep_code}: {dep_chapter.title}\n"
            prompt += "\n"
        
        prompt += """## 输出要求
1. 严格按照章节要求进行写作
2. 确保内容完整、逻辑清晰
3. 如需表格，请使用Markdown表格格式
4. 内容要专业、准确、符合绩效评价报告标准
5. 字数要充足，确保内容详实

请开始写作："""
        
        return prompt
    
    def get_template_summary(self) -> Dict:
        """获取模板摘要信息"""
        return {
            "name": self.template_data.get('name', ''),
            "description": self.template_data.get('description', ''),
            "version": self.template_data.get('version', ''),
            "total_chapters": len(self.chapters),
            "writing_sequence_length": len(self.writing_sequence),
            "completed_chapters": sum(1 for c in self.chapters.values() if c.is_completed),
            "next_chapter": self.get_next_chapter_to_write()
        }
    
    def save_progress(self, session_id: str):
        """保存写作进度"""
        progress_file = Path(f"workspaces/{session_id}/writing_progress.json")
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        progress_data = {
            "template_name": self.template_data.get('name', ''),
            "completed_chapters": [
                code for code, chapter in self.chapters.items() 
                if chapter.is_completed
            ],
            "total_chapters": len(self.chapters)
        }
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    def load_progress(self, session_id: str):
        """加载写作进度"""
        progress_file = Path(f"workspaces/{session_id}/writing_progress.json")
        
        if progress_file.exists():
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                
                # 恢复完成状态
                for chapter_code in progress_data.get('completed_chapters', []):
                    if chapter_code in self.chapters:
                        self.chapters[chapter_code].is_completed = True
                
                logger.info(f"加载写作进度: {len(progress_data.get('completed_chapters', []))} 个章节已完成")
                
            except Exception as e:
                logger.error(f"加载写作进度失败: {e}")

# 全局模板分析器实例
report_template_analyzer = ReportTemplateAnalyzer()