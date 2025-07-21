import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useReportStore } from '../stores/reportStore';

const SessionPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { setCurrentSession } = useReportStore();

  useEffect(() => {
    if (sessionId) {
      setCurrentSession(sessionId);
    }
    
    return () => {
      setCurrentSession(null);
    };
  }, [sessionId, setCurrentSession]);

  // Layout组件会处理实际的渲染
  return null;
};

export default SessionPage;