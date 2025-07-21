import { useState, useEffect, useRef, useCallback } from 'react';
import { useReportStore } from '../stores/reportStore';

interface WebSocketMessage {
  type: string;
  agent_type?: string;
  agent_name?: string;
  content: string;
  status?: string;
  timestamp: string;
  [key: string]: any;
}

interface UseWebSocketReturn {
  messages: WebSocketMessage[];
  sendMessage: (message: any) => void;
  isConnected: boolean;
  connectionError: string | null;
}

export const useWebSocket = (sessionId: string): UseWebSocketReturn => {
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const messageIdsRef = useRef<Set<string>>(new Set()); // 用于去重

  const {
    updateReportProgress,
    updateReportStatus,
    setReportContent
  } = useReportStore();

  const connect = useCallback(() => {
    if (!sessionId) return;

    try {
      const wsUrl = `ws://localhost:8000/ws/${sessionId}`;
      const socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      socket.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        socketRef.current = null;

        // 自动重连
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.pow(2, reconnectAttempts.current) * 1000; // 指数退避
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            console.log(`Attempting to reconnect (${reconnectAttempts.current}/${maxReconnectAttempts})`);
            connect();
          }, delay);
        } else {
          setConnectionError('连接失败，请刷新页面重试');
        }
      };

      socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionError('连接出现错误');
      };

      socketRef.current = socket;
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionError('无法建立连接');
    }
  }, [sessionId]);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    console.log('Received message:', message);
    console.log('Message type:', message.type);
    console.log('Message agent_type:', message.agent_type);
    console.log('Message content preview:', message.content?.substring(0, 100));

    // 添加时间戳（如果没有的话）
    if (!message.timestamp) {
      message.timestamp = new Date().toISOString();
    }

    // 处理不同类型的消息
    switch (message.type) {
      case 'agent_message':
      case 'user_intervention':
        console.log('Adding message to chat history');
        setMessages(prev => {
          console.log('Previous messages count:', prev.length);
          const newMessages = [...prev, message];
          console.log('New messages count:', newMessages.length);
          return newMessages;
        });
        break;

      case 'report_update':
        // 更新报告内容
        console.log('Received report_update:', message);
        if (message.content) {
          console.log('Setting report content:', message.content.substring(0, 100) + '...');
          setReportContent(message.content);
        }
        break;

      case 'workflow_status':
        // 更新工作流状态
        if (message.phase) {
          updateReportStatus(sessionId, message.phase);
        }
        if (message.progress !== undefined) {
          updateReportProgress(sessionId, message.progress);
        }
        break;

      case 'connection_established':
        console.log('Connection established:', message.message);
        break;

      default:
        console.log('Unknown message type, adding to messages anyway');
        // 其他类型的消息也添加到消息列表
        setMessages(prev => [...prev, message]);
    }
  }, [sessionId, updateReportProgress, updateReportStatus, setReportContent]);

  const sendMessage = useCallback((message: any) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      try {
        socketRef.current.send(JSON.stringify(message));
        // 不在这里添加用户消息，让后端处理后再通过WebSocket返回
      } catch (error) {
        console.error('Error sending message:', error);
        setConnectionError('发送消息失败');
      }
    } else {
      console.warn('WebSocket is not connected');
      setConnectionError('连接已断开，正在重连...');
    }
  }, []);

  // 建立连接
  useEffect(() => {
    if (sessionId) {
      // 先清理现有连接
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      connect();
    }

    // 清理函数
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [sessionId]);

  // 页面可见性变化时重连
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !isConnected && sessionId) {
        connect();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isConnected, sessionId, connect]);

  return {
    messages,
    sendMessage,
    isConnected,
    connectionError
  };
};