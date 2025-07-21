import React from 'react';
import ChatArea from './ChatArea';
import AgentTeamPanel from './AgentTeamPanel';

interface LayoutProps {
  children?: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="flex h-screen bg-gray-900 text-white">
      {/* 主对话区域 - 占30% */}
      <div className="w-[35%] flex flex-col min-w-0 bg-gray-800">
        <ChatArea />
      </div>
      
      {/* 右侧Agent团队工作面板 - 占70% */}
      <div className="w-[65%] bg-gray-900 border-l border-gray-700 flex-shrink-0 shadow-lg">
        <AgentTeamPanel />
      </div>
    </div>
  );
};

export default Layout;