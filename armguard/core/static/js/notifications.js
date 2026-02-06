/**
 * Notifications UI System
 * Toast notifications with queue management
 */

class NotificationSystem {
    constructor() {
        this.container = null;
        this.queue = [];
        this.activeNotifications = new Set();
        this.maxActive = 3;
        this.defaultDuration = 5000;
        this.init();
    }

    /**
     * Initialize notification container
     */
    init() {
        // Create container if it doesn't exist
        if (!document.getElementById('notification-container')) {
            this.container = document.createElement('div');
            this.container.id = 'notification-container';
            this.container.className = 'notification-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('notification-container');
        }
    }

    /**
     * Show notification
     * @param {string} title - Notification title
     * @param {string} message - Notification message
     * @param {string} level - Notification level: 'info', 'success', 'warning', 'error'
     * @param {number} duration - Auto-dismiss duration in ms (0 = no auto-dismiss)
     */
    show(title, message, level = 'info', duration = null) {
        const notification = {
            id: Date.now() + Math.random(),
            title,
            message,
            level,
            duration: duration !== null ? duration : this.defaultDuration
        };

        // Add to queue
        this.queue.push(notification);
        this.processQueue();
    }

    /**
     * Process notification queue
     */
    processQueue() {
        while (this.queue.length > 0 && this.activeNotifications.size < this.maxActive) {
            const notification = this.queue.shift();
            this.display(notification);
        }
    }

    /**
     * Display notification
     */
    display(notification) {
        const element = this.createNotificationElement(notification);
        this.container.appendChild(element);
        this.activeNotifications.add(notification.id);

        // Animate in
        setTimeout(() => {
            element.classList.add('show');
        }, 10);

        // Auto-dismiss
        if (notification.duration > 0) {
            setTimeout(() => {
                this.dismiss(notification.id, element);
            }, notification.duration);
        }

        // Manual dismiss on click
        const closeBtn = element.querySelector('.notification-close');
        if (closeBtn) {
            closeBtn.onclick = () => this.dismiss(notification.id, element);
        }
    }

    /**
     * Create notification DOM element
     */
    createNotificationElement(notification) {
        const element = document.createElement('div');
        element.className = `notification notification-${notification.level}`;
        element.setAttribute('data-id', notification.id);

        const icon = this.getIcon(notification.level);
        
        element.innerHTML = `
            <div class="notification-icon">${icon}</div>
            <div class="notification-content">
                <div class="notification-title">${this.escapeHtml(notification.title)}</div>
                <div class="notification-message">${this.escapeHtml(notification.message)}</div>
            </div>
            <button class="notification-close" aria-label="Close">&times;</button>
        `;

        return element;
    }

    /**
     * Get icon for notification level
     */
    getIcon(level) {
        const icons = {
            info: '&#9432;',      // ℹ
            success: '&#10004;',   // ✓
            warning: '&#9888;',    // ⚠
            error: '&#10006;'      // ✖
        };
        return icons[level] || icons.info;
    }

    /**
     * Dismiss notification
     */
    dismiss(id, element) {
        element.classList.remove('show');
        element.classList.add('hide');

        setTimeout(() => {
            element.remove();
            this.activeNotifications.delete(id);
            this.processQueue(); // Process next in queue
        }, 300);
    }

    /**
     * Clear all notifications
     */
    clearAll() {
        const notifications = this.container.querySelectorAll('.notification');
        notifications.forEach(element => {
            const id = element.getAttribute('data-id');
            this.dismiss(parseInt(id), element);
        });
        this.queue = [];
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
     * Shorthand methods
     */
    info(title, message, duration) {
        this.show(title, message, 'info', duration);
    }

    success(title, message, duration) {
        this.show(title, message, 'success', duration);
    }

    warning(title, message, duration) {
        this.show(title, message, 'warning', duration);
    }

    error(title, message, duration) {
        this.show(title, message, 'error', duration);
    }
}

// Create global instance
window.notifications = new NotificationSystem();

// Initialize WebSocket notification listener
document.addEventListener('DOMContentLoaded', function() {
    if (window.wsManager && typeof userAuthenticated !== 'undefined' && userAuthenticated) {
        // Connect to notification channel
        window.wsManager.connect('notifications', {
            onMessage: (data) => {
                if (data.type === 'notification') {
                    window.notifications.show(
                        data.title,
                        data.message,
                        data.level || 'info'
                    );
                }
            },
            onOpen: () => {
                console.log('[Notifications] Connected to notification channel');
            },
            onClose: () => {
                console.log('[Notifications] Disconnected from notification channel');
            }
        });
    }
});
