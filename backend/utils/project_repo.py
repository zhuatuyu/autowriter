from pathlib import Path

class ProjectRepo:
    def __init__(self, session_id: str):
        """
        初始化项目仓库
        
        Args:
            session_id: 会话ID，用于创建唯一的项目工作区
        """
        self.session_id = session_id
        # 创建项目根目录：workspaces/project_{session_id}/
        self.root = Path("workspaces") / f"{session_id}"
        
        # 定义标准目录结构
        self.uploads = self.root / 'uploads'
        self.research = self.root / 'research'
        self.web_research = self.research / 'web'
        self.case_research = self.research / 'cases'
        self.analysis = self.root / 'analysis'
        self.design = self.root / 'design'
        self.drafts = self.root / 'drafts'
        self.reports = self.root / 'reports'
        self.outputs = self.root / 'outputs'

        self._create_dirs()

    def _create_dirs(self):
        """创建所有必要的目录"""
        self.root.mkdir(parents=True, exist_ok=True)
        self.uploads.mkdir(exist_ok=True)
        self.research.mkdir(exist_ok=True)
        self.web_research.mkdir(exist_ok=True)
        self.case_research.mkdir(exist_ok=True)
        self.analysis.mkdir(exist_ok=True)
        self.design.mkdir(exist_ok=True)
        self.drafts.mkdir(exist_ok=True)
        self.reports.mkdir(exist_ok=True)
        self.outputs.mkdir(exist_ok=True)

    def get_path(self, dir_type: str = '', filename: str = '') -> Path:
        """
        获取指定目录或文件的路径
        
        Args:
            dir_type: 目录类型，支持嵌套路径如 'research/cases'
            filename: 可选的文件名
            
        Returns:
            Path: 完整的文件或目录路径
        """
        if not dir_type:
            return self.root / filename if filename else self.root
            
        # 支持嵌套路径
        if '/' in dir_type:
            parts = dir_type.split('/')
            if parts[0] == 'research':
                if len(parts) > 1 and parts[1] == 'web':
                    base_path = self.web_research
                elif len(parts) > 1 and parts[1] == 'cases':
                    base_path = self.case_research
                else:
                    base_path = self.research
            else:
                # 对于其他嵌套路径，从根目录开始构建
                base_path = self.root
                for part in parts:
                    base_path = base_path / part
        else:
            # 单级目录映射
            dir_map = {
                'uploads': self.uploads,
                'research': self.research,
                'web': self.web_research,
                'cases': self.case_research,
                'analysis': self.analysis,
                'design': self.design,
                'drafts': self.drafts,
                'reports': self.reports,
                'outputs': self.outputs,
                'root': self.root
            }
            if dir_type not in dir_map:
                raise ValueError(f"Unknown directory type: {dir_type}")
            base_path = dir_map[dir_type]
        
        return base_path / filename if filename else base_path

    def save_file(self, filename: str, content: str, dir_type: str = 'outputs') -> Path:
        """
        保存文件到指定目录
        
        Args:
            filename: 文件名
            content: 文件内容
            dir_type: 目录类型
            
        Returns:
            Path: 保存的文件路径
        """
        file_path = self.get_path(dir_type, filename)
        
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return file_path