type MessageHandler = (data: any) => void;
type ConnectionHandler = () => void;
type ErrorHandler = (error: any) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private isConnecting = false;
  private userId: string | null = null;
  private messageHandlers: MessageHandler[] = [];
  private openHandlers: ConnectionHandler[] = [];
  private closeHandlers: ConnectionHandler[] = [];
  private errorHandlers: ErrorHandler[] = [];
  private connectionTimeout: NodeJS.Timeout | null = null;

  connect(userId: string) {
    if (this.userId === userId && this.ws && 
        (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      console.log('WebSocket already connected or connecting for user:', userId);
      return;
    }

    if (this.isConnecting) {
      console.log('WebSocket connection already in progress');
      return;
    }

    this.userId = userId;
    this.isConnecting = true;

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NODE_ENV === 'production'
      ? window.location.host
      : '127.0.0.1:8000';
    const wsUrl = `${protocol}//${host}/api/v1/chat/ws?user_id=${userId}`;

    console.log('Creating singleton WebSocket connection:', wsUrl);
    this.ws = new WebSocket(wsUrl);

    this.connectionTimeout = setTimeout(() => {
      if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
        console.log('WebSocket connection timeout');
        this.ws.close();
        this.errorHandlers.forEach(handler => handler('Connection timeout'));
      }
    }, 10000);

    this.ws.onopen = () => {
      console.log('Singleton WebSocket connected');
      this.isConnecting = false;
      if (this.connectionTimeout) {
        clearTimeout(this.connectionTimeout);
        this.connectionTimeout = null;
      }
      this.openHandlers.forEach(handler => handler());
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Singleton WebSocket message received:', data.type, data.content ? data.content.substring(0, 20) + '...' : '');
      console.log('Broadcasting to', this.messageHandlers.length, 'handlers');
      this.messageHandlers.forEach((handler, index) => {
        console.log(`Calling handler ${index + 1} for message type:`, data.type);
        handler(data);
      });
    };

    this.ws.onerror = (error) => {
      console.error('Singleton WebSocket error:', error);
      this.isConnecting = false;
      this.errorHandlers.forEach(handler => handler(error));
    };

    this.ws.onclose = (event) => {
      console.log('Singleton WebSocket closed:', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
      });
      this.isConnecting = false;
      if (this.connectionTimeout) {
        clearTimeout(this.connectionTimeout);
        this.connectionTimeout = null;
      }
      this.closeHandlers.forEach(handler => handler());
    };
  }

  disconnect() {
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnecting = false;
    this.userId = null;
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
      return true;
    }
    console.error('WebSocket not connected');
    return false;
  }

  isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  onMessage(handler: MessageHandler) {
    console.log('Adding message handler. Total handlers:', this.messageHandlers.length + 1);
    this.messageHandlers.push(handler);
    return () => {
      console.log('Removing message handler. Total handlers will be:', this.messageHandlers.length - 1);
      this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
    };
  }

  onOpen(handler: ConnectionHandler) {
    this.openHandlers.push(handler);
    return () => {
      this.openHandlers = this.openHandlers.filter(h => h !== handler);
    };
  }

  onClose(handler: ConnectionHandler) {
    this.closeHandlers.push(handler);
    return () => {
      this.closeHandlers = this.closeHandlers.filter(h => h !== handler);
    };
  }

  onError(handler: ErrorHandler) {
    this.errorHandlers.push(handler);
    return () => {
      this.errorHandlers = this.errorHandlers.filter(h => h !== handler);
    };
  }
}

// Singleton instance
export const socketManager = new WebSocketManager();