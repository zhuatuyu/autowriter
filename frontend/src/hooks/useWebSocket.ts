import { useState, useEffect, useRef, useCallback } from 'react';

interface WebSocketMessage {
    type: string;
    sender?: string;
    content: any;
    timestamp?: string;
}

export const useWebSocket = (sessionId: string) => {
    const [messages, setMessages] = useState<WebSocketMessage[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const socket = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const maxReconnectAttempts = 5;
    const isConnectingRef = useRef(false);
    const connectionStableRef = useRef(false);

    const connect = useCallback(() => {
        if (!sessionId || isConnectingRef.current) {
            console.log(`Skipping connection: sessionId=${sessionId}, isConnecting=${isConnectingRef.current}`);
            return;
        }

        // 如果已经有稳定连接，不要重复连接
        if (socket.current && socket.current.readyState === WebSocket.OPEN && connectionStableRef.current) {
            console.log(`WebSocket already connected and stable for session ${sessionId}`);
            return;
        }

        // 清理现有连接
        if (socket.current) {
            console.log(`Closing existing connection for session ${sessionId}`);
            socket.current.close();
            socket.current = null;
        }

        isConnectingRef.current = true;
        connectionStableRef.current = false;

        try {
            const wsUrl = `ws://${window.location.host}/ws/${sessionId}`;
            console.log(`Connecting to WebSocket: ${wsUrl}`);
            socket.current = new WebSocket(wsUrl);

            socket.current.onopen = () => {
                console.log(`WebSocket connected for session ${sessionId}`);
                setIsConnected(true);
                reconnectAttemptsRef.current = 0;
                isConnectingRef.current = false;
                
                // 设置连接稳定标志，延迟3秒确保连接真正稳定
                setTimeout(() => {
                    if (socket.current && socket.current.readyState === WebSocket.OPEN) {
                        connectionStableRef.current = true;
                        console.log(`WebSocket connection stable for session ${sessionId}`);
                    }
                }, 3000);
            };

            socket.current.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    console.log('Received WebSocket message:', message);
                    
                    // 过滤重复的连接确认消息
                    if (message.type === 'connection_established') {
                        return;
                    }
                    
                    setMessages((prevMessages) => [...prevMessages, message]);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            socket.current.onclose = (event) => {
                console.log(`WebSocket disconnected for session ${sessionId}`, event.code, event.reason);
                setIsConnected(false);
                isConnectingRef.current = false;
                connectionStableRef.current = false;

                // 只有在非正常关闭且连接曾经稳定时才重连
                if (event.code !== 1000 && event.code !== 1001 && reconnectAttemptsRef.current < maxReconnectAttempts) {
                    const delay = Math.min(3000 * Math.pow(1.5, reconnectAttemptsRef.current), 20000);
                    console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);

                    reconnectTimeoutRef.current = setTimeout(() => {
                        reconnectAttemptsRef.current++;
                        connect();
                    }, delay);
                }
            };

            socket.current.onerror = (error) => {
                console.error('WebSocket error:', error);
                setIsConnected(false);
                isConnectingRef.current = false;
                connectionStableRef.current = false;
            };
        } catch (error) {
            console.error('Error creating WebSocket connection:', error);
            setIsConnected(false);
            isConnectingRef.current = false;
            connectionStableRef.current = false;
        }
    }, [sessionId]);

    useEffect(() => {
        if (sessionId) {
            console.log(`Setting up WebSocket for session: ${sessionId}`);
            connect();
        }

        return () => {
            console.log(`Cleaning up WebSocket for session: ${sessionId}`);
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (socket.current) {
                connectionStableRef.current = false;
                socket.current.close(1000, 'Component unmounting');
                socket.current = null;
            }
            isConnectingRef.current = false;
        };
    }, [sessionId]);

    const sendMessage = async (message: WebSocketMessage) => {
        if (message.type === 'file_upload' && message.content instanceof File) {
            // 处理文件上传
            const formData = new FormData();
            formData.append('file', message.content);

            try {
                const response = await fetch(`/api/upload/${sessionId}`, {
                    method: 'POST',
                    body: formData,
                });
                const result = await response.json();
                if (response.ok) {
                    const notification = {
                        type: 'system_notification',
                        sender: 'System',
                        content: `文件上传成功: ${message.content.name}`,
                        timestamp: new Date().toISOString()
                    };
                    setMessages((prev) => [...prev, notification]);
                } else {
                    throw new Error(result.error || 'File upload failed');
                }
            } catch (error) {
                console.error('File upload error:', error);
                const errorNotification = {
                    type: 'system_error',
                    sender: 'System',
                    content: `文件上传失败: ${message.content.name}`,
                    timestamp: new Date().toISOString()
                };
                setMessages((prev) => [...prev, errorNotification]);
            }
        } else if (socket.current?.readyState === WebSocket.OPEN && connectionStableRef.current) {
            // 发送普通JSON消息
            console.log('Sending WebSocket message:', message);
            socket.current.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not ready for sending message:', {
                readyState: socket.current?.readyState,
                stable: connectionStableRef.current
            });
        }
    };

    return { messages, sendMessage, isConnected };
};