import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Mic, CornerDownLeft } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket'; // 确认路径正确
import { useParams } from 'react-router-dom';

const ChatArea: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
    const { messages, sendMessage, isConnected } = useWebSocket(sessionId || 'default-session');
    const [input, setInput] = useState('');
    const endOfMessagesRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLInputElement>(null); // 新增：输入框引用

  useEffect(() => {
        endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

    const handleSend = () => {
        if (input.trim()) {
            // 先在本地显示用户消息
            const userMessage = {
                type: 'user_message',
                sender: 'user',
                content: input,
                timestamp: new Date().toISOString()
            };
            
            // 发送到后端
            sendMessage({
                type: 'user_message',
                content: input,
            });
            
            setInput('');
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            handleSend();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                sendMessage({
                    type: 'file_upload',
                    content: file,
                });
            }
    }
  };

    return (
        <div className="flex flex-col h-full bg-gray-800">
            {/* 顶部状态栏 */}
            <div className="flex items-center justify-between p-3 border-b border-gray-700">
                <h2 className="text-lg font-semibold text-white">Agent 协作对话</h2>
                <div className={`flex items-center text-sm ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
                    <span className={`w-2 h-2 rounded-full mr-2 ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></span>
                    {isConnected ? '已连接' : '未连接'}
        </div>
      </div>

            {/* 消息展示区域 */}
            <div className="flex-1 p-4 overflow-y-auto">
        {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <div className="text-center">
                            <CornerDownLeft size={48} className="mx-auto mb-4 opacity-50" />
                            <h3 className="text-xl font-medium text-gray-400">准备就绪</h3>
                            <p className="mt-1">从下方的输入框开始，向我提出您的报告撰写需求吧。</p>
            </div>
          </div>
        ) : (
                    <div className="space-y-6">
            {messages.map((msg, index) => (
                            <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`p-3 rounded-lg max-w-lg ${msg.sender === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-200'}`}>
                                    {msg.sender !== 'user' && <div className="font-bold text-sm mb-1 text-indigo-300">{msg.sender}</div>}
                                    <p className="text-sm" style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
                                </div>
                            </div>
            ))}
                    </div>
                )}
                <div ref={endOfMessagesRef} />
      </div>

            {/* 输入框区域 */}
            <div className="p-4 border-t border-gray-700">
                <div className="flex items-center bg-gray-900 rounded-lg p-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                        placeholder="请输入您的需求，或上传文件..."
                        className="flex-1 w-full bg-transparent text-white placeholder-gray-500 focus:outline-none px-2"
                        disabled={!isConnected}
              />
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        className="hidden"
                        multiple
                    />
                    <button onClick={() => fileInputRef.current?.click()} className="p-2 text-gray-400 hover:text-white">
                <Paperclip size={20} />
              </button>
                    <button className="p-2 text-gray-400 hover:text-white">
                        <Mic size={20} />
                    </button>
          <button
                        onClick={handleSend}
                        className="ml-2 bg-blue-600 text-white rounded-md p-2 hover:bg-blue-700 focus:outline-none disabled:bg-gray-600 disabled:cursor-not-allowed"
                        disabled={!input.trim() || !isConnected}
                    >
                        <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatArea;