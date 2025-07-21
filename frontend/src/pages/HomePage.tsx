import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, FileText, TrendingUp, Users } from 'lucide-react';
import { useReportStore } from '../stores/reportStore';

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { reports, createNewReport } = useReportStore();
  const [isCreating, setIsCreating] = React.useState(false);

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

  const recentReports = reports.slice(0, 3);
  const completedCount = reports.filter(r => r.status === 'completed').length;
  const inProgressCount = reports.filter(r => r.status !== 'completed').length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-12">
        {/* 头部 */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            AutoWriter Enhanced
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            智能多Agent协作报告生成系统
          </p>
          <button
            onClick={handleCreateReport}
            disabled={isCreating}
            className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2 mx-auto"
          >
            <Plus size={20} />
            <span>{isCreating ? '创建中...' : '创建新报告'}</span>
          </button>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center">
              <div className="p-3 bg-blue-100 rounded-lg">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-semibold text-gray-900">总报告数</h3>
                <p className="text-2xl font-bold text-blue-600">{reports.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center">
              <div className="p-3 bg-green-100 rounded-lg">
                <TrendingUp className="w-6 h-6 text-green-600" />
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-semibold text-gray-900">已完成</h3>
                <p className="text-2xl font-bold text-green-600">{completedCount}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center">
              <div className="p-3 bg-orange-100 rounded-lg">
                <Users className="w-6 h-6 text-orange-600" />
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-semibold text-gray-900">进行中</h3>
                <p className="text-2xl font-bold text-orange-600">{inProgressCount}</p>
              </div>
            </div>
          </div>
        </div>

        {/* 最近的报告 */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">最近的报告</h2>
          
          {recentReports.length > 0 ? (
            <div className="space-y-4">
              {recentReports.map((report) => (
                <div
                  key={report.id}
                  onClick={() => navigate(`/session/${report.id}`)}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900">{report.title}</h3>
                    <p className="text-sm text-gray-500">{report.projectType}</p>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        report.status === 'completed' 
                          ? 'bg-green-100 text-green-800'
                          : report.status === 'paused'
                          ? 'bg-gray-100 text-gray-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {report.status === 'completed' ? '已完成' : 
                         report.status === 'paused' ? '已暂停' : '进行中'}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(report.updatedAt).toLocaleDateString('zh-CN')}
                      </p>
                    </div>
                    
                    {report.status !== 'completed' && (
                      <div className="w-16">
                        <div className="bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${report.progress}%` }}
                          />
                        </div>
                        <p className="text-xs text-gray-500 text-center mt-1">
                          {report.progress}%
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">还没有报告，创建第一个报告开始吧！</p>
            </div>
          )}
        </div>

        {/* 功能特性 */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          <div className="text-center">
            <div className="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
              <Users className="w-8 h-8 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">多Agent协作</h3>
            <p className="text-gray-600">7个专业Agent协同工作，分工明确，高效协作</p>
          </div>

          <div className="text-center">
            <div className="bg-green-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
              <TrendingUp className="w-8 h-8 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">实时监控</h3>
            <p className="text-gray-600">实时观察Agent对话过程，随时插话补充信息</p>
          </div>

          <div className="text-center">
            <div className="bg-purple-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
              <FileText className="w-8 h-8 text-purple-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">智能生成</h3>
            <p className="text-gray-600">基于知识库和案例分析，生成高质量专业报告</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;