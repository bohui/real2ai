import { useCallback, useEffect, useRef, useState } from "react";

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: number;
}

export interface UseWebSocketOptions {
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
}

export interface UseWebSocketReturn {
  ws: WebSocket | null;
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  send: (message: any) => void;
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
}

export const useWebSocket = (
  url: string | null,
  options: UseWebSocketOptions = {},
): UseWebSocketReturn => {
  const {
    onOpen,
    onClose,
    onError,
    onMessage,
    reconnectAttempts = 3,
    reconnectInterval = 5000,
    heartbeatInterval = 30000,
  } = options;

  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reconnectAttemptsRef = useRef(0);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const clearHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const startHeartbeat = useCallback(() => {
    clearHeartbeat();

    if (heartbeatInterval > 0) {
      heartbeatIntervalRef.current = setInterval(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({ type: "ping", timestamp: Date.now() }),
          );
        }
      }, heartbeatInterval);
    }
  }, [heartbeatInterval, clearHeartbeat]);

  const connect = useCallback(() => {
    if (!url || isConnecting || (ws && ws.readyState === WebSocket.OPEN)) {
      return;
    }

    setIsConnecting(true);
    setError(null);
    clearReconnectTimeout();

    try {
      const websocket = new WebSocket(url);
      wsRef.current = websocket;
      setWs(websocket);

      websocket.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
        reconnectAttemptsRef.current = 0;
        startHeartbeat();
        onOpen?.();
      };

      websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          // Handle pong response
          if (message.type === "pong") {
            return;
          }

          onMessage?.(message);
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err);
        }
      };

      websocket.onerror = (event) => {
        setError("WebSocket connection error");
        setIsConnecting(false);
        onError?.(event);
      };

      websocket.onclose = (event) => {
        setIsConnected(false);
        setIsConnecting(false);
        wsRef.current = null;
        setWs(null);
        clearHeartbeat();

        onClose?.();

        // Attempt reconnection if not manually closed
        if (
          event.code !== 1000 &&
          reconnectAttemptsRef.current < reconnectAttempts
        ) {
          reconnectAttemptsRef.current++;
          setError(
            `Connection lost. Retrying... (${reconnectAttemptsRef.current}/${reconnectAttempts})`,
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        } else if (reconnectAttemptsRef.current >= reconnectAttempts) {
          setError("Failed to reconnect after multiple attempts");
        }
      };
    } catch (err) {
      setError("Failed to create WebSocket connection");
      setIsConnecting(false);
    }
  }, [url, isConnecting, reconnectAttempts, reconnectInterval]); // Simplified dependencies

  const disconnect = useCallback(() => {
    clearHeartbeat();
    clearReconnectTimeout();

    if (wsRef.current) {
      wsRef.current.close(1000, "Manual disconnect");
      wsRef.current = null;
    }

    setWs(null);
    setIsConnected(false);
    setIsConnecting(false);
    setError(null);
    reconnectAttemptsRef.current = 0;
  }, [clearHeartbeat, clearReconnectTimeout]);

  const reconnect = useCallback(() => {
    disconnect();
    setTimeout(() => connect(), 100);
  }, [disconnect, connect]);

  const send = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        const payload = typeof message === "string"
          ? message
          : JSON.stringify(message);
        wsRef.current.send(payload);
      } catch (err) {
        console.error("Failed to send WebSocket message:", err);
        setError("Failed to send message");
      }
    } else {
      console.warn("WebSocket is not connected");
      setError("WebSocket is not connected");
    }
  }, []);

  // Connect on mount if URL is provided
  useEffect(() => {
    if (url) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [url]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearHeartbeat();
      clearReconnectTimeout();
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [clearHeartbeat, clearReconnectTimeout]);

  return {
    ws,
    isConnected,
    isConnecting,
    error,
    send,
    connect,
    disconnect,
    reconnect,
  };
};
