/**
 * WebSocket Client Module
 * Manages real-time connection to the FastAPI backend.
 */

const WS_URL = 'ws://127.0.0.1:8765/ws';
const RECONNECT_INTERVAL = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

class WebSocketClient {
  constructor() {
    this.ws = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.listeners = new Map();
    this.reconnectTimer = null;
  }

  /**
   * Connect to the WebSocket server.
   */
  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    try {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => {
        console.log('[WS] Connected to backend');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.emit('connected');
      };

      this.ws.onclose = (event) => {
        console.log(`[WS] Disconnected (code: ${event.code})`);
        this.isConnected = false;
        this.emit('disconnected');
        this._scheduleReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('[WS] Error:', error);
        this.emit('error', error);
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this._handleMessage(message);
        } catch (e) {
          console.error('[WS] Failed to parse message:', e);
        }
      };
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      this._scheduleReconnect();
    }
  }

  /**
   * Send a message to the server.
   */
  send(data) {
    if (!this.isConnected || this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('[WS] Not connected, cannot send');
      return false;
    }

    this.ws.send(JSON.stringify(data));
    return true;
  }

  /**
   * Send a chat message.
   */
  sendChat(text) {
    return this.send({ type: 'chat', text });
  }

  /**
   * Send audio data for STT.
   */
  sendAudio(base64Data) {
    return this.send({ type: 'audio', data: base64Data });
  }

  /**
   * Reset conversation.
   */
  resetConversation() {
    return this.send({ type: 'reset' });
  }

  /**
   * Register an event listener.
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  /**
   * Remove an event listener.
   */
  off(event, callback) {
    const cbs = this.listeners.get(event);
    if (cbs) {
      this.listeners.set(event, cbs.filter(cb => cb !== callback));
    }
  }

  /**
   * Emit an event to all listeners.
   */
  emit(event, data) {
    const cbs = this.listeners.get(event) || [];
    cbs.forEach(cb => cb(data));
  }

  /**
   * Handle incoming WebSocket message by type.
   */
  _handleMessage(message) {
    const { type } = message;

    switch (type) {
      case 'token':
        this.emit('token', message);
        break;
      case 'sentence':
        this.emit('sentence', message);
        break;
      case 'response_complete':
        this.emit('response_complete', message);
        break;
      case 'audio_response':
        this.emit('audio_response', message);
        break;
      case 'stt_result':
        this.emit('stt_result', message);
        break;
      case 'status':
        this.emit('status', message);
        break;
      case 'error':
        this.emit('error', message);
        break;
      case 'pong':
        break;
      default:
        console.log('[WS] Unknown message type:', type, message);
    }
  }

  /**
   * Schedule a reconnection attempt.
   */
  _scheduleReconnect() {
    if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      console.error('[WS] Max reconnect attempts reached');
      this.emit('max_reconnect');
      return;
    }

    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      console.log(`[WS] Reconnecting... (attempt ${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
      this.emit('reconnecting', this.reconnectAttempts);
      this.connect();
    }, RECONNECT_INTERVAL);
  }

  /**
   * Disconnect cleanly.
   */
  disconnect() {
    clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }
}

export default WebSocketClient;
