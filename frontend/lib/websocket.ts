import { WSMessage } from "./types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export type WSStatus = "connecting" | "connected" | "disconnected" | "error";
export type MessageHandler = (msg: WSMessage) => void;

export class ImaginaSocket {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private handlers: MessageHandler[] = [];
  private statusHandlers: ((s: WSStatus) => void)[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _status: WSStatus = "disconnected";
  private shouldReconnect = true;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  get status() {
    return this._status;
  }

  onMessage(handler: MessageHandler) {
    this.handlers.push(handler);
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler);
    };
  }

  onStatus(handler: (s: WSStatus) => void) {
    this.statusHandlers.push(handler);
    return () => {
      this.statusHandlers = this.statusHandlers.filter((h) => h !== handler);
    };
  }

  connect() {
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) return;
    this.shouldReconnect = true;
    this.setStatus("connecting");
    const url = `${WS_URL}/ws/sessions/${this.sessionId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => this.setStatus("connected");

    this.ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as WSMessage;
        this.handlers.forEach((h) => h(msg));
      } catch {
        /* ignore malformed */
      }
    };

    this.ws.onclose = () => {
      this.setStatus("disconnected");
      if (this.shouldReconnect) this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.setStatus("error");
    };
  }

  send(type: string, payload: Record<string, unknown> = {}) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...payload }));
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
    this.setStatus("disconnected");
  }

  private setStatus(s: WSStatus) {
    this._status = s;
    this.statusHandlers.forEach((h) => h(s));
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => this.connect(), 3000);
  }
}
