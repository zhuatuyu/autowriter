import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import HomePage from './pages/HomePage'; // 确保路径正确
import './index.css'; // 重新引入全局样式

function App() {
  return (
      <Router>
          <Routes>
            <Route path="/" element={<HomePage />} />
        <Route path="/session/:sessionId" element={<Layout />} />
        {/* 如果需要，可以添加一个重定向，当sessionId不存在时回到主页 */}
        <Route path="/session" element={<Navigate to="/" />} /> 
          </Routes>
      </Router>
  );
}

export default App;