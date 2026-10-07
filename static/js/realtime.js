/**
 * Realtime Client with WebSocket connection and 30s polling fallback.
 * ProjectHub AI - Academic Project Management System
 */

(function () {
    let socket = null;
    let pollInterval = null;
    const POLL_INTERVAL_MS = 30000;

    function updateNotificationBadge(unreadCount) {
        const badgeElem = document.getElementById('notification-badge');
        if (badgeElem) {
            if (unreadCount > 0) {
                badgeElem.textContent = unreadCount > 99 ? '99+' : unreadCount;
                badgeElem.classList.remove('hidden');
            } else {
                badgeElem.classList.add('hidden');
            }
        }
    }

    function startPollingFallback() {
        if (pollInterval) return;
        console.log('[Realtime] Starting 30s HTTP polling fallback...');
        
        function poll() {
            fetch('/notifications/unread-count/', {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => res.ok ? res.json() : null)
            .then(data => {
                if (data && typeof data.unread_count === 'number') {
                    updateNotificationBadge(data.unread_count);
                }
            })
            .catch(err => console.warn('[Realtime] Polling error:', err));
        }

        poll();
        pollInterval = setInterval(poll, POLL_INTERVAL_MS);
    }

    function initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;

        try {
            socket = new WebSocket(wsUrl);

            socket.onopen = function () {
                console.log('[Realtime] WebSocket connected successfully.');
                if (pollInterval) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                }
            };

            socket.onmessage = function (event) {
                try {
                    const data = JSON.parse(event.data);
                    if (data.unread_count !== undefined) {
                        updateNotificationBadge(data.unread_count);
                    }
                } catch (e) {
                    console.warn('[Realtime] Error parsing WS message:', e);
                }
            };

            socket.onerror = function (err) {
                console.warn('[Realtime] WebSocket error, switching to polling fallback:', err);
                startPollingFallback();
            };

            socket.onclose = function () {
                console.log('[Realtime] WebSocket connection closed, switching to polling fallback.');
                startPollingFallback();
            };
        } catch (e) {
            console.warn('[Realtime] WebSocket initialization failed:', e);
            startPollingFallback();
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        initWebSocket();
    });
})();
