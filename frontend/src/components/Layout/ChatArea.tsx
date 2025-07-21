import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Loader2 } from 'lucide-react';
import AgentMessage from '../Chat/AgentMessage';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useParams } from 'react-router-dom';
import { useReportStore } from '../../stores/reportStore';

const ChatArea: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [message, setMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const { messages, sendMessage, isConnected } = useWebSocket(sessionId || '');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = () => {
    if (message.trim() && sessionId) {
      sendMessage({
        type: 'user_message',
        content: message.trim()
      });
      setMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFileUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      // TODO: 实现文件上传逻辑
      console.log('Files selected:', files);
    }
  };

  if (!sessionId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">欢迎使用 AutoWriter Enhanced</h2>
          <p className="text-gray-600">请从左侧选择一个报告或创建新报告开始</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* 连接状态指示器 */}
      <div className="px-4 py-2 bg-white border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Agent 协作对话</h2>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600">
              {isConnected ? '已连接' : '连接中...'}
            </span>
          </div>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="text-gray-400 mb-4">
                <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-3.582 8-8 8a8.955 8.955 0 01-2.347-.306c-.584.296-1.925.864-3.653 1.027-.066-.005-.133-.01-.2-.015v-.025c.05-.094.093-.19.132-.288.815-.197 1.538-.516 2.068-.896A8 8 0 1121 12z" />
                </svg>
              </div>
              <p className="text-gray-600 mb-4">Agent 团队准备就绪</p>
              <div className="space-y-2">
                <button 
                  onClick={() => sendMessage({ type: 'start_analysis', project_info: { name: '测试项目' } })}
                  className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 block w-full"
                >
                  开始分析
                </button>
                <button 
                  onClick={() => {
                    // 测试报告更新
                    console.log('Testing report update...');
                    const { setReportContent } = useReportStore.getState();
                    const testContent = '# 测试报告\n\n这是一个测试报告内容，用于验证右侧预览功能是否正常工作。\n\n## 测试章节\n\n- 测试项目1\n- 测试项目2\n- 测试项目3\n\n**测试完成！**';
                    setReportContent(testContent);
                    console.log('Report content set:', testContent.substring(0, 50) + '...');
                  }}
                  className="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 block w-full text-sm"
                >
                  测试报告更新
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, index) => (
              <AgentMessage key={index} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* 输入区域 */}
      <div className="border-t bg-white p-4">
        <div className="flex items-end space-x-3">
          <div className="flex-1">
            <div className="relative">
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="随时插话补充信息或提出问题..."
                className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={1}
                style={{ minHeight: '44px', maxHeight: '120px' }}
              />
              <button
                onClick={handleFileUpload}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <Paperclip size={20} />
              </button>
            </div>
          </div>
          
          <button
            onClick={handleSendMessage}
            disabled={!message.trim() || !isConnected}
            className="bg-blue-500 text-white p-3 rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isTyping ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
          </button>
        </div>
        
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileChange}
          className="hidden"
        />
      </div>
    </div>
  );
};

export default ChatArea;