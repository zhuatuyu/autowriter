import React from 'react';
import Sidebar from './Sidebar';
import ChatArea from './ChatArea';
import ReportPreview from './ReportPreview';

interface LayoutProps {
  children?: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="flex h-screen bg-gray-100">
      {/* 左侧栏 - 报告列表 */}
      <div className="w-80 bg-white border-r border-gray-200 flex-shrink-0">
        <Sidebar />
      </div>
      
      {/* 中间区域 - Agent对话 */}
      <div className="flex-1 flex flex-col min-w-0">
        <ChatArea />
      </div>
      
      {/* 右侧栏 - 报告预览 */}
      <div className="w-96 bg-white border-l border-gray-200 flex-shrink-0">
        <ReportPreview />
      </div>
    </div>
  );
};

export default Layout;