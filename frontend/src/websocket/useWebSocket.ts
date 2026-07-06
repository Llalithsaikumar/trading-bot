/**
 * Generic WebSocket hook with auto-reconnect and heartbeat.
 */
import { useEffect, useRef, useCallback } from "react";
import type { WSMessage } from "@/types";

type MessageHandler<T = unknown> = (msg: WSMessage<T>) => void;

interface UseWebSocketOptions<T = unknown> {
  url: string;
  onMessage: MessageHandler<T>;
  onOpen?: () => void;
  onClose?: () => void;
  enabled?: boolean;
  reconnectDelay?: number;
}

export function useWebSocket<T = unknown>({
  url,
  onMessage,
  onOpen,
  onClose,
  enabled = true,
  reconnectDelay = 3000,
}: UseWebSocketOptions<T>) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMounted = useRef(true);

  const connect = useCallback(() => {
    if (!enabled || !isMounted.current) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      onOpen?.();
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage<T> = JSON.parse(event.data as string);
        onMessage(msg);
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => {
      onClose?.();
      if (isMounted.current) {
        reconnectTimer.current = setTimeout(connect, reconnectDelay);
      }
    };

    ws.onerror = () => ws.close();
  }, [url, enabled, onMessage, onOpen, onClose, reconnectDelay]);

  useEffect(() => {
    isMounted.current = true;
    connect();
    return () => {
      isMounted.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { send };
}
