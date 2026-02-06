/**
 * WebSocket Manager
 * Manages WebSocket connections with automatic reconnection
 */

class WebSocketManager {
    constructor() {
        this.connections = new Map();
        this.reconnectAttempts = new Map();
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Max 30 seconds
        this.heartbeatInterval = 30000; // 30 seconds
        this.heartbeatTimers = new Map();
    }

    /**
     * Connect to a WebSocket endpoint
     * @param {string} endpoint - WebSocket endpoint (e.g., 'notifications', 'transactions')
     * @param {object} handlers - Event handlers {onMessage, onOpen, onClose, onError}
     * @returns {WebSocket} WebSocket instance
     */
    connect(endpoint, handlers = {}) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${endpoint}/`;
        
        console.log(`[WebSocket] Connecting to ${endpoint}...`);
        
        const ws = new WebSocket(wsUrl);
        this.connections.set(endpoint, ws);
        this.reconnectAttempts.set(endpoint, 0);

        ws.onopen = () => {
            console.log(`[WebSocket] Connected to ${endpoint}`);
            this.reconnectAttempts.set(endpoint, 0);
            
            // Start heartbeat for notification channel
            if (endpoint === 'notifications') {
                this.startHeartbeat(endpoint, ws);
            }
            
            if (handlers.onOpen) {
                handlers.onOpen();
            }
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log(`[WebSocket] Message from ${endpoint}:`, data);
                
                // Handle pong responses
                if (data.type === 'pong') {
                    console.log(`[WebSocket] Heartbeat pong received from ${endpoint}`);
                    return;
                }
                
                if (handlers.onMessage) {
                    handlers.onMessage(data);
                }
            } catch (error) {
                console.error(`[WebSocket] Error parsing message:`, error);
            }
        };

        ws.onclose = (event) => {
            console.log(`[WebSocket] Disconnected from ${endpoint}`, event);
            this.stopHeartbeat(endpoint);
            this.connections.delete(endpoint);
            
            if (handlers.onClose) {
                handlers.onClose(event);
            }

            // Attempt reconnection
            this.scheduleReconnect(endpoint, handlers);
        };

        ws.onerror = (error) => {
            console.error(`[WebSocket] Error on ${endpoint}:`, error);
            
            if (handlers.onError) {
                handlers.onError(error);
            }
        };

        return ws;
    }

    /**
     * Schedule reconnection with exponential backoff
     */
    scheduleReconnect(endpoint, handlers) {
        const attempts = this.reconnectAttempts.get(endpoint) || 0;
        
        if (attempts >= this.maxReconnectAttempts) {
            console.error(`[WebSocket] Max reconnection attempts reached for ${endpoint}`);
            return;
        }

        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, attempts),
            this.maxReconnectDelay
        );

        console.log(`[WebSocket] Reconnecting to ${endpoint} in ${delay}ms (attempt ${attempts + 1}/${this.maxReconnectAttempts})`);

        setTimeout(() => {
            this.reconnectAttempts.set(endpoint, attempts + 1);
            this.connect(endpoint, handlers);
        }, delay);
    }

    /**
     * Start heartbeat ping/pong
     */
    startHeartbeat(endpoint, ws) {
        this.stopHeartbeat(endpoint); // Clear any existing timer
        
        const timer = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                console.log(`[WebSocket] Sending heartbeat ping to ${endpoint}`);
                ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, this.heartbeatInterval);
        
        this.heartbeatTimers.set(endpoint, timer);
    }

    /**
     * Stop heartbeat
     */
    stopHeartbeat(endpoint) {
        const timer = this.heartbeatTimers.get(endpoint);
        if (timer) {
            clearInterval(timer);
            this.heartbeatTimers.delete(endpoint);
        }
    }

    /**
     * Disconnect from an endpoint
     */
    disconnect(endpoint) {
        const ws = this.connections.get(endpoint);
        if (ws) {
            console.log(`[WebSocket] Manually disconnecting from ${endpoint}`);
            this.stopHeartbeat(endpoint);
            ws.close();
            this.connections.delete(endpoint);
        }
    }

    /**
     * Disconnect all connections
     */
    disconnectAll() {
        console.log('[WebSocket] Disconnecting all connections');
        for (const endpoint of this.connections.keys()) {
            this.disconnect(endpoint);
        }
    }

    /**
     * Get connection status
     */
    isConnected(endpoint) {
        const ws = this.connections.get(endpoint);
        return ws && ws.readyState === WebSocket.OPEN;
    }

    /**
     * Send message to endpoint
     */
    send(endpoint, data) {
        const ws = this.connections.get(endpoint);
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(data));
            return true;
        }
        console.warn(`[WebSocket] Cannot send to ${endpoint}: not connected`);
        return false;
    }
}

// Create global instance
window.wsManager = new WebSocketManager();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    window.wsManager.disconnectAll();
});
