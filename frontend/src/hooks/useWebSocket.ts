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

    const connect = useCallback(() => {
        if (!sessionId) return;

        try {
            const wsUrl = `ws://${window.location.host}/ws/${sessionId}`;
            socket.current = new WebSocket(wsUrl);

            socket.current.onopen = () => {
                console.log(`WebSocket connected for session ${sessionId}`);
                setIsConnected(true);
                reconnectAttemptsRef.current = 0; // 重置重连计数
            };

            socket.current.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    setMessages((prevMessages) => [...prevMessages, message]);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            socket.current.onclose = (event) => {
                console.log(`WebSocket disconnected for session ${sessionId}`, event.code, event.reason);
                setIsConnected(false);

                // 如果不是手动关闭，尝试重连
                if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
                    const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
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
            };
        } catch (error) {
            console.error('Error creating WebSocket connection:', error);
            setIsConnected(false);
        }
    }, [sessionId]);

    useEffect(() => {
        connect();

        return () => {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (socket.current) {
                socket.current.close(1000, 'Component unmounting');
            }
        };
    }, [connect]);

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
                    // 文件上传成功后，可以发送一个通知消息
                    const notification = {
                        type: 'system_notification',
                        sender: 'System',
                        content: `文件上传成功: ${message.content.name}`
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
                    content: `文件上传失败: ${message.content.name}`
                };
                setMessages((prev) => [...prev, errorNotification]);
            }
        } else if (socket.current?.readyState === WebSocket.OPEN) {
            // 发送普通JSON消息
            socket.current.send(JSON.stringify(message));
        }
    };

    return { messages, sendMessage, isConnected };
};