import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Loader2 } from 'lucide-react';

interface AgentMessageProps {
  message: {
    type: string;
    agent_type?: string;
    agent_name?: string;
    content: string;
    status?: string;
    timestamp: string;
  };
}

const AgentMessage: React.FC<AgentMessageProps> = ({ message }) => {
  const getAgentConfig = (agentType: string) => {
    const configs = {
      'chief_editor': { name: '总编', color: 'bg-blue-500', icon: '👔' },
      'data_analyst': { name: '数据分析师', color: 'bg-green-500', icon: '📊' },
      'policy_researcher': { name: '政策研究员', color: 'bg-purple-500', icon: '📋' },
      'case_researcher': { name: '案例研究员', color: 'bg-orange-500', icon: '🔍' },
      'indicator_builder': { name: '指标专家', color: 'bg-red-500', icon: '📏' },
      'writer': { name: '写作专员', color: 'bg-indigo-500', icon: '✍️' },
      'reviewer': { name: '质量评审员', color: 'bg-gray-500', icon: '🔎' }
    };
    return configs[agentType as keyof typeof configs] || { name: '系统', color: 'bg-gray-400', icon: '🤖' };
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // 处理用户消息
  if (message.type === 'user_intervention') {
    return (
      <div className="flex items-start space-x-3">
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm">
          👤
        </div>
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-1">
            <span className="font-medium text-gray-900">您</span>
            <span className="text-xs text-gray-500">
              {formatTime(message.timestamp)}
            </span>
          </div>
          <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
            <p className="text-gray-900">{message.content}</p>
          </div>
        </div>
      </div>
    );
  }

  // 处理Agent消息
  if (message.type === 'agent_message' && message.agent_type) {
    const config = getAgentConfig(message.agent_type);
    const isThinking = message.status === 'thinking';

    return (
      <div className="flex items-start space-x-3">
        <div className={`w-8 h-8 rounded-full ${config.color} flex items-center justify-center text-white text-sm relative`}>
          {config.icon}
          {isThinking && (
            <div className="absolute -top-1 -right-1">
              <Loader2 size={12} className="animate-spin text-blue-500" />
            </div>
          )}
        </div>
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-1">
            <span className="font-medium text-gray-900">{config.name}</span>
            <span className="text-xs text-gray-500">
              {formatTime(message.timestamp)}
            </span>
            {isThinking && (
              <span className="text-xs text-blue-500 animate-pulse flex items-center space-x-1">
                <Loader2 size={12} className="animate-spin" />
                <span>正在思考...</span>
              </span>
            )}
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // 自定义渲染组件
                  h1: ({ children }) => <h1 className="text-lg font-bold text-gray-900 mb-2">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-base font-semibold text-gray-900 mb-2">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-medium text-gray-900 mb-1">{children}</h3>,
                  h4: ({ children }) => <h4 className="text-sm font-medium text-gray-800 mb-1">{children}</h4>,
                  p: ({ children }) => <p className="text-gray-700 mb-2 last:mb-0">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc list-inside text-gray-700 mb-2 space-y-1">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-inside text-gray-700 mb-2 space-y-1">{children}</ol>,
                  li: ({ children }) => <li className="text-sm">{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
                  em: ({ children }) => <em className="italic text-gray-600">{children}</em>,
                  code: ({ children }) => <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">{children}</code>,
                  blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-4 italic text-gray-600">{children}</blockquote>,
                  // 表格组件
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-4">
                      <table className="min-w-full divide-y divide-gray-200 border border-gray-300 rounded-lg">
                        {children}
                      </table>
                    </div>
                  ),
                  thead: ({ children }) => (
                    <thead className="bg-gray-50">
                      {children}
                    </thead>
                  ),
                  tbody: ({ children }) => (
                    <tbody className="bg-white divide-y divide-gray-200">
                      {children}
                    </tbody>
                  ),
                  tr: ({ children }) => (
                    <tr className="hover:bg-gray-50">
                      {children}
                    </tr>
                  ),
                  th: ({ children }) => (
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-200 last:border-r-0">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="px-4 py-3 text-sm text-gray-900 border-r border-gray-200 last:border-r-0">
                      {children}
                    </td>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 处理系统消息
  return (
    <div className="flex justify-center">
      <div className="bg-gray-100 text-gray-600 px-3 py-1 rounded-full text-sm">
        {message.content}
      </div>
    </div>
  );
};

export default AgentMessage;