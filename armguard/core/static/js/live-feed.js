/**
 * Live Transaction Feed
 * Real-time transaction updates
 */

class LiveTransactionFeed {
    constructor(containerId = 'live-transaction-feed') {
        this.container = document.getElementById(containerId);
        this.maxItems = 10;
        this.transactions = [];
        this.connected = false;
        
        if (this.container) {
            this.init();
        }
    }

    /**
     * Initialize live feed
     */
    init() {
        // Connect to transaction WebSocket
        if (window.wsManager) {
            window.wsManager.connect('transactions', {
                onMessage: (data) => this.handleMessage(data),
                onOpen: () => {
                    this.connected = true;
                    this.updateConnectionStatus(true);
                    console.log('[LiveFeed] Connected to transaction feed');
                },
                onClose: () => {
                    this.connected = false;
                    this.updateConnectionStatus(false);
                    console.log('[LiveFeed] Disconnected from transaction feed');
                }
            });
        }

        // Show initial loading state
        this.showLoading();
    }

    /**
     * Handle WebSocket message
     */
    handleMessage(data) {
        if (data.type === 'transaction_created') {
            this.addTransaction(data.transaction, 'created');
        } else if (data.type === 'transaction_returned') {
            this.addTransaction(data.transaction, 'returned');
        }
    }

    /**
     * Add transaction to feed
     */
    addTransaction(transaction, type) {
        // Add to beginning of array
        this.transactions.unshift({
            ...transaction,
            feedType: type,
            timestamp: new Date(transaction.timestamp || Date.now())
        });

        // Trim to max items
        if (this.transactions.length > this.maxItems) {
            this.transactions = this.transactions.slice(0, this.maxItems);
        }

        this.render();
    }

    /**
     * Render feed
     */
    render() {
        if (!this.container) return;

        if (this.transactions.length === 0) {
            this.container.innerHTML = `
                <div class="feed-empty">
                    <p>No recent transactions</p>
                    <small>New transactions will appear here in real-time</small>
                </div>
            `;
            return;
        }

        const html = this.transactions.map(tx => this.renderTransaction(tx)).join('');
        this.container.innerHTML = html;

        // Animate new items
        const items = this.container.querySelectorAll('.feed-item');
        if (items.length > 0) {
            items[0].classList.add('feed-item-new');
            setTimeout(() => {
                items[0].classList.remove('feed-item-new');
            }, 2000);
        }
    }

    /**
     * Render single transaction
     */
    renderTransaction(tx) {
        const actionClass = tx.action === 'Take' ? 'action-take' : 'action-return';
        const actionIcon = tx.action === 'Take' ? '📤' : '📥';
        const timeAgo = this.getTimeAgo(tx.timestamp);
        
        return `
            <div class="feed-item ${actionClass}" data-id="${tx.id}">
                <div class="feed-icon">${actionIcon}</div>
                <div class="feed-content">
                    <div class="feed-header">
                        <strong>${this.escapeHtml(tx.personnel)}</strong>
                        <span class="feed-action">${tx.action}</span>
                        <span class="feed-item-name">${this.escapeHtml(tx.item)}</span>
                    </div>
                    <div class="feed-meta">
                        <span class="feed-user">by ${this.escapeHtml(tx.issued_by)}</span>
                        <span class="feed-time">${timeAgo}</span>
                    </div>
                    ${tx.duty_type ? `<div class="feed-duty"><small>Duty: ${this.escapeHtml(tx.duty_type)}</small></div>` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Show loading state
     */
    showLoading() {
        if (this.container) {
            this.container.innerHTML = `
                <div class="feed-loading">
                    <div class="spinner"></div>
                    <p>Connecting to live feed...</p>
                </div>
            `;
        }
    }

    /**
     * Update connection status indicator
     */
    updateConnectionStatus(connected) {
        const indicator = document.getElementById('feed-status-indicator');
        if (indicator) {
            indicator.className = connected ? 'status-connected' : 'status-disconnected';
            indicator.textContent = connected ? 'Live' : 'Disconnected';
        }
    }

    /**
     * Get human-readable time ago
     */
    getTimeAgo(timestamp) {
        const now = new Date();
        const then = new Date(timestamp);
        const seconds = Math.floor((now - then) / 1000);

        if (seconds < 60) return 'just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Destroy feed and disconnect
     */
    destroy() {
        if (window.wsManager) {
            window.wsManager.disconnect('transactions');
        }
    }
}

// Auto-initialize if container exists
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('live-transaction-feed')) {
        window.liveFeed = new LiveTransactionFeed();
    }
});
