import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import { useReportStore } from '../../stores/reportStore';

const ReportPreview: React.FC = () => {
  const { currentReport, reportContent } = useReportStore();
  
  // 调试信息
  console.log('ReportPreview - currentReport:', currentReport);
  console.log('ReportPreview - reportContent:', reportContent ? 'Content exists' : 'No content');

  if (!currentReport && !reportContent) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center">
          <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">报告预览</h3>
          <p className="text-gray-500">选择一个报告查看实时内容</p>
        </div>
      </div>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'analysis':
      case 'writing':
      case 'review':
        return <Clock className="w-4 h-4 text-blue-500 animate-pulse" />;
      case 'paused':
        return <AlertCircle className="w-4 h-4 text-orange-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusText = (status: string) => {
    const statusMap = {
      'analysis': '分析中',
      'writing': '写作中',
      'review': '评审中',
      'completed': '已完成',
      'paused': '已暂停'
    };
    return statusMap[status as keyof typeof statusMap] || '未知状态';
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* 头部 */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-gray-900">报告内容</h2>
          {currentReport && (
            <div className="flex items-center space-x-2">
              {getStatusIcon(currentReport.status)}
              <span className="text-sm text-gray-600">
                {getStatusText(currentReport.status)}
              </span>
            </div>
          )}
        </div>
        
        {currentReport && (
          <div className="text-sm text-gray-500 truncate">
            {currentReport.title}
          </div>
        )}
        
        {/* 进度条 */}
        {currentReport && currentReport.status !== 'completed' && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>完成进度</span>
              <span>{currentReport.progress}%</span>
            </div>
            <div className="bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${currentReport.progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* 报告内容 */}
      <div className="flex-1 overflow-y-auto">
        {reportContent ? (
          <div className="p-6">
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => (
                    <h1 className="text-2xl font-bold text-gray-900 mb-4 pb-2 border-b border-gray-200">
                      {children}
                    </h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-xl font-semibold text-gray-900 mb-3 mt-6">
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-lg font-medium text-gray-900 mb-2 mt-4">
                      {children}
                    </h3>
                  ),
                  h4: ({ children }) => (
                    <h4 className="text-base font-medium text-gray-900 mb-2 mt-3">
                      {children}
                    </h4>
                  ),
                  p: ({ children }) => (
                    <p className="text-gray-700 mb-3 leading-relaxed">
                      {children}
                    </p>
                  ),
                  ul: ({ children }) => (
                    <ul className="list-disc list-inside text-gray-700 mb-3 space-y-1">
                      {children}
                    </ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal list-inside text-gray-700 mb-3 space-y-1">
                      {children}
                    </ol>
                  ),
                  li: ({ children }) => (
                    <li className="text-sm leading-relaxed">{children}</li>
                  ),
                  strong: ({ children }) => (
                    <strong className="font-semibold text-gray-900">{children}</strong>
                  ),
                  em: ({ children }) => (
                    <em className="italic text-gray-600">{children}</em>
                  ),
                  code: ({ children }) => (
                    <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono">
                      {children}
                    </code>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-4 border-blue-200 pl-4 py-2 bg-blue-50 rounded-r">
                      {children}
                    </blockquote>
                  ),
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-6 shadow-sm rounded-lg border border-gray-200">
                      <table className="min-w-full divide-y divide-gray-200">
                        {children}
                      </table>
                    </div>
                  ),
                  thead: ({ children }) => (
                    <thead className="bg-gray-50">{children}</thead>
                  ),
                  tbody: ({ children }) => (
                    <tbody className="bg-white divide-y divide-gray-200">{children}</tbody>
                  ),
                  tr: ({ children }) => (
                    <tr className="hover:bg-gray-50">{children}</tr>
                  ),
                  th: ({ children }) => (
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {children}
                    </td>
                  ),
                  hr: () => (
                    <hr className="my-6 border-gray-200" />
                  ),
                }}
              >
                {reportContent}
              </ReactMarkdown>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-pulse">
                <div className="w-12 h-12 bg-gray-200 rounded-full mx-auto mb-4"></div>
                <div className="h-4 bg-gray-200 rounded w-32 mx-auto mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-24 mx-auto"></div>
              </div>
              <p className="text-gray-500 mt-4">等待 Agent 生成报告内容...</p>
            </div>
          </div>
        )}
      </div>

      {/* 底部操作 */}
      {reportContent && (
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <div className="flex space-x-2">
            <button className="flex-1 bg-white border border-gray-300 text-gray-700 px-3 py-2 rounded-lg hover:bg-gray-50 text-sm">
              导出 Word
            </button>
            <button className="flex-1 bg-white border border-gray-300 text-gray-700 px-3 py-2 rounded-lg hover:bg-gray-50 text-sm">
              导出 PDF
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportPreview;