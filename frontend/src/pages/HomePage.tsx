import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Folder, Clock, CheckCircle, PlayCircle, PlusCircle } from 'lucide-react';

interface Project {
    id: string;
    name: string;
    status: 'draft' | 'active' | 'completed';
    lastModified: string;
    progress: number;
}

const statusConfig = {
    draft: { icon: <Folder size={16} />, color: 'text-gray-500', label: '草稿' },
    active: { icon: <PlayCircle size={16} />, color: 'text-blue-500', label: '进行中' },
    completed: { icon: <CheckCircle size={16} />, color: 'text-green-500', label: '已完成' },
};

const HomePage: React.FC = () => {
    const navigate = useNavigate();
    const [projects, setProjects] = useState<Project[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchProjects = async () => {
            try {
                setIsLoading(true);
                const response = await fetch('/api/projects');
                const data = await response.json();
                if (response.ok) {
                    setProjects(data.projects || []);
                } else {
                    throw new Error(data.error || '获取项目列表失败');
                }
            } catch (err: any) {
                setError(err.message);
    } finally {
                setIsLoading(false);
    }
  };

        fetchProjects();
    }, []);

    const createNewProject = () => {
        navigate('/create');
    };

  return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
            <div className="max-w-7xl mx-auto">
                <header className="flex justify-between items-center mb-8">
                    <h1 className="text-4xl font-bold">项目工作台</h1>
          <button
                        onClick={createNewProject}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          >
                        <PlusCircle size={20} />
                        创建新项目
          </button>
                </header>

                {isLoading && (
                    <div className="text-center py-16">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400 mx-auto"></div>
                        <p className="mt-4 text-gray-400">正在加载项目列表...</p>
                  </div>
                )}

                {error && (
                    <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg text-center">
                        <p><strong>加载失败：</strong> {error}</p>
                    </div>
                )}

                {!isLoading && !error && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                        {projects.map((project) => (
                            <Link to={`/session/${project.id}`} key={project.id} className="block bg-gray-800 p-6 rounded-lg border border-gray-700 hover:border-blue-500 hover:bg-gray-700/50 transition-all transform hover:-translate-y-1">
                                <div className="flex justify-between items-start">
                                    <Folder className="text-blue-400 w-10 h-10" />
                                    <div className={`flex items-center gap-2 text-xs px-2 py-1 rounded-full ${statusConfig[project.status].color} bg-opacity-10`}>
                                        {statusConfig[project.status].icon}
                                        <span>{statusConfig[project.status].label}</span>
                                    </div>
                                </div>
                                <h2 className="text-xl font-semibold mt-4 truncate">{project.name}</h2>
                                <p className="text-sm text-gray-400 flex items-center gap-2 mt-2">
                                    <Clock size={14} />
                                    最后修改: {project.lastModified}
                                </p>
                                <div className="mt-4">
                                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                                        <span>完成度</span>
                                        <span>{project.progress}%</span>
                                    </div>
                                    <div className="w-full bg-gray-700 rounded-full h-2">
                          <div 
                            className="bg-blue-500 h-2 rounded-full"
                                            style={{ width: `${project.progress}%` }}
                          />
                        </div>
                      </div>
                            </Link>
              ))}
            </div>
                )}
      </div>
    </div>
  );
};

export default HomePage;