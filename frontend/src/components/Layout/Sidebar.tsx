import React, { useState } from 'react';
import { Plus, Upload, Play, Pause, FileText, Clock, CheckCircle } from 'lucide-react';
import { useReportStore } from '../../stores/reportStore';
import { useNavigate, useParams } from 'react-router-dom';

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const { reports, currentSession, createNewReport } = useReportStore();
  const [isCreating, setIsCreating] = useState(false);

  const handleCreateReport = async () => {
    setIsCreating(true);
    try {
      const newSessionId = await createNewReport({
        name: '新建绩效评价报告',
        type: '绩效评价',
        objective: '评估项目绩效',
        budget: '100',
        funding_source: '财政资金',
        evaluator: '专业评价机构'
      });
      navigate(`/session/${newSessionId}`);
    } catch (error) {
      console.error('创建报告失败:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const getStatusConfig = (status: string) => {
    const configs = {
      'analysis': { 
        color: 'bg-yellow-100 text-yellow-800', 
        text: '分析中', 
        icon: Clock 
      },
      'writing': { 
        color: 'bg-blue-100 text-blue-800', 
        text: '写作中', 
        icon: FileText 
      },
      'review': { 
        color: 'bg-purple-100 text-purple-800', 
        text: '评审中', 
        icon: Clock 
      },
      'completed': { 
        color: 'bg-green-100 text-green-800', 
        text: '已完成', 
        icon: CheckCircle 
      },
      'paused': { 
        color: 'bg-gray-100 text-gray-800', 
        text: '已暂停', 
        icon: Pause 
      }
    };
    return configs[status as keyof typeof configs] || configs['analysis'];
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="h-full flex flex-col">
      {/* 头部 */}
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-lg font-semibold text-gray-900 mb-4">AutoWriter Enhanced</h1>
        <button 
          onClick={handleCreateReport}
          disabled={isCreating}
          className="w-full bg-blue-500 text-white rounded-lg px-4 py-2 hover:bg-blue-600 disabled:opacity-50 flex items-center justify-center space-x-2"
        >
          <Plus size={16} />
          <span>{isCreating ? '创建中...' : '新建报告'}</span>
        </button>
      </div>

      {/* 报告列表 */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          {/* 进行中的报告 */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-500 mb-3">进行中</h3>
            {reports.filter(r => r.status !== 'completed').map(report => {
              const statusConfig = getStatusConfig(report.status);
              const StatusIcon = statusConfig.icon;
              const isActive = report.id === sessionId;
              
              return (
                <div 
                  key={report.id}
                  onClick={() => navigate(`/session/${report.id}`)}
                  className={`p-3 rounded-lg mb-3 cursor-pointer transition-all ${
                    isActive 
                      ? 'bg-blue-50 border border-blue-200 shadow-sm' 
                      : 'hover:bg-gray-50 border border-transparent'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="text-sm font-medium text-gray-900 truncate flex-1 mr-2">
                      {report.title}
                    </h4>
                    <span className={`px-2 py-1 text-xs rounded-full flex items-center space-x-1 ${statusConfig.color}`}>
                      <StatusIcon size={12} />
                      <span>{statusConfig.text}</span>
                    </span>
                  </div>
                  
                  <p className="text-xs text-gray-500 mb-2">{report.projectType}</p>
                  
                  <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
                    <span>{formatDate(report.updatedAt)}</span>
                    <span>{report.progress}%</span>
                  </div>
                  
                  {report.status !== 'completed' && report.status !== 'paused' && (
                    <div className="bg-gray-200 rounded-full h-1.5">
                      <div 
                        className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${report.progress}%` }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* 已完成的报告 */}
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-3">已完成</h3>
            {reports.filter(r => r.status === 'completed').map(report => {
              const statusConfig = getStatusConfig(report.status);
              const StatusIcon = statusConfig.icon;
              
              return (
                <div 
                  key={report.id}
                  onClick={() => navigate(`/session/${report.id}`)}
                  className="p-3 rounded-lg mb-3 cursor-pointer hover:bg-gray-50 border border-transparent"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="text-sm font-medium text-gray-900 truncate flex-1 mr-2">
                      {report.title}
                    </h4>
                    <span className={`px-2 py-1 text-xs rounded-full flex items-center space-x-1 ${statusConfig.color}`}>
                      <StatusIcon size={12} />
                      <span>{statusConfig.text}</span>
                    </span>
                  </div>
                  
                  <p className="text-xs text-gray-500 mb-2">{report.projectType}</p>
                  <div className="text-xs text-gray-400">
                    {formatDate(report.updatedAt)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>



      {/* 底部操作区 */}
      {currentSession && (
        <div className="p-4 border-t border-gray-200 space-y-2">
          <button className="w-full bg-gray-100 text-gray-700 rounded-lg px-4 py-2 hover:bg-gray-200 flex items-center justify-center space-x-2">
            <Upload size={16} />
            <span>上传资料</span>
          </button>
          
          <div className="flex space-x-2">
            <button className="flex-1 bg-orange-100 text-orange-700 rounded-lg px-3 py-2 hover:bg-orange-200 flex items-center justify-center space-x-1 text-sm">
              <Pause size={14} />
              <span>暂停</span>
            </button>
            
            <button className="flex-1 bg-gray-100 text-gray-700 rounded-lg px-3 py-2 hover:bg-gray-200 flex items-center justify-center space-x-1 text-sm">
              <FileText size={14} />
              <span>导出</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Sidebar;