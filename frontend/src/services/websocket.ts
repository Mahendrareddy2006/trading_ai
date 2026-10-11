type MessageHandler = (data: any) => void;

export const getLiveWebSocketUrl = (): string => {
  const envWs = (import.meta as any).env?.VITE_WS_URL;
  if (envWs) return envWs;

  const envApi = (import.meta as any).env?.VITE_API_BASE_URL;
  if (envApi) {
    const wsBase = envApi.replace(/^http/, 'ws').replace(/\/api\/?$/, '');
    return `${wsBase}/ws/live`;
  }

  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    if (window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1')) {
      return 'ws://127.0.0.1:8000/ws/live';
    }
    return `${proto}//${window.location.host}/ws/live`;
  }

  return 'ws://127.0.0.1:8000/ws/live';
};

class LiveWebSocketClient {
  private url: string;
  private ws: WebSocket | null = null;
  private listeners: Set<MessageHandler> = new Set();
  private reconnectTimer: any = null;
  private isConnected = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 20;

  constructor(url?: string) {
    this.url = url || getLiveWebSocketUrl();
  }

  public connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.reconnectAttempts = 0;
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.listeners.forEach((handler) => handler(payload));
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.isConnected = false;
        this.ws?.close();
      };
    } catch (e) {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    if (!this.reconnectTimer) {
      // Exponential backoff with jitter
      this.reconnectAttempts++;
      const baseDelay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 15000);
      const jitter = Math.random() * 1000;
      const delay = baseDelay + jitter;

      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this.connect();
      }, delay);
    }
  }

  public subscribe(handler: MessageHandler) {
    this.listeners.add(handler);
    return () => this.listeners.delete(handler);
  }

  public getStatus(): boolean {
    return this.isConnected;
  }
}

export const liveWs = new LiveWebSocketClient();
