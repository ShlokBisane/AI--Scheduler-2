/**
 * History Module — Shows completed, expired, and deleted schedule entries.
 * Provides a record of all past study sessions.
 */

const History = (() => {
    let isExpanded = false;

    function init() {
        const toggle = document.getElementById('history-toggle');
        const list = document.getElementById('history-list');

        if (toggle) {
            toggle.addEventListener('click', () => {
                isExpanded = !isExpanded;
                list.classList.toggle('collapsed', !isExpanded);
                toggle.classList.toggle('collapsed', !isExpanded);
                if (isExpanded) {
                    refresh();
                }
            });
        }

        // Start collapsed
        if (list) list.classList.add('collapsed');
        refresh();
    }

    async function refresh() {
        const list = document.getElementById('history-list');
        const countBadge = document.getElementById('history-count');

        try {
            const data = await Api.getHistory();
            const history = data.history || [];
            const stats = data.stats || {};

            // Update count badge
            const total = stats.total || 0;
            if (countBadge) {
                countBadge.textContent = total;
                countBadge.className = 'badge' + (total > 0 ? ' has-items' : '');
            }

            if (history.length === 0) {
                list.innerHTML = '<div class="history-empty">No history yet</div>';
                return;
            }

            // Group by date
            const grouped = {};
            history.forEach(h => {
                const dateKey = h.date || 'Unknown';
                if (!grouped[dateKey]) grouped[dateKey] = [];
                grouped[dateKey].push(h);
            });

            let html = '';

            // Stats summary
            html += `
                <div class="history-stats">
                    <span class="history-stat completed">✅ ${stats.completed || 0}</span>
                    <span class="history-stat expired">⏰ ${stats.expired || 0}</span>
                    <span class="history-stat deleted">🗑️ ${stats.deleted || 0}</span>
                </div>
            `;

            // Render by date (most recent first)
            const sortedDates = Object.keys(grouped).sort().reverse();
            const showDates = sortedDates.slice(0, 10); // Show last 10 dates

            showDates.forEach(dateStr => {
                const items = grouped[dateStr];
                const dateLabel = formatHistoryDate(dateStr);
                
                html += `<div class="history-date-label">${dateLabel}</div>`;
                
                items.forEach(item => {
                    if (item.session_type === 'break') return; // Skip breaks
                    
                    const reasonIcon = {
                        'completed': '✅',
                        'expired': '⏰',
                        'deleted': '🗑️'
                    }[item.reason] || '📋';

                    html += `
                        <div class="history-item ${item.reason}">
                            <span class="history-icon">${reasonIcon}</span>
                            <div class="history-info">
                                <div class="history-subject">
                                    <span class="history-color-dot" style="background:${item.color}"></span>
                                    ${item.subject}
                                </div>
                                <div class="history-topic">${item.topic || item.session_type}</div>
                            </div>
                            <span class="history-time">${item.start_time}–${item.end_time}</span>
                        </div>
                    `;
                });
            });

            // Clear history button
            if (total > 0) {
                html += `
                    <button class="history-clear-btn" id="clear-history-btn">
                        🗑️ Clear History
                    </button>
                `;
            }

            list.innerHTML = html;

            // Attach clear handler
            const clearBtn = document.getElementById('clear-history-btn');
            if (clearBtn) {
                clearBtn.addEventListener('click', async () => {
                    if (confirm('Clear all history?')) {
                        try {
                            await Api.clearHistory();
                            showToast('History cleared!', 'success');
                            refresh();
                        } catch (err) {
                            showToast('Failed to clear history');
                        }
                    }
                });
            }

        } catch (err) {
            list.innerHTML = '<div class="history-empty">Failed to load history</div>';
        }
    }

    function formatHistoryDate(dateStr) {
        try {
            const d = new Date(dateStr + 'T00:00:00');
            const today = new Date();
            today.setHours(0,0,0,0);
            const yesterday = new Date(today);
            yesterday.setDate(yesterday.getDate() - 1);

            if (d.getTime() === today.getTime()) return 'Today';
            if (d.getTime() === yesterday.getTime()) return 'Yesterday';

            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        } catch {
            return dateStr;
        }
    }

    return { init, refresh };
})();
