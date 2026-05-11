/**
 * API Client — Handles all backend communication
 */

const API_BASE = '';  // Same origin (served by FastAPI)

const Api = {
    /**
     * Generic fetch wrapper
     */
    async request(url, options = {}) {
        const defaults = {
            headers: { 'Content-Type': 'application/json' },
        };
        const config = { ...defaults, ...options };
        if (options.body && typeof options.body === 'object') {
            config.body = JSON.stringify(options.body);
        }

        const response = await fetch(`${API_BASE}${url}`, config);

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || error.message || 'Something went wrong');
        }

        return response.json();
    },

    // ─── Settings ───────────────────────────────────────
    async getSettings() {
        return this.request('/api/settings');
    },

    async saveSettings(data) {
        return this.request('/api/settings', { method: 'POST', body: data });
    },

    // ─── Chats ──────────────────────────────────────────
    async getChats() {
        return this.request('/api/chats');
    },

    async createChat(title = 'New Chat', mode = 'student') {
        return this.request('/api/chats', { method: 'POST', body: { title, mode } });
    },

    async deleteChat(chatId) {
        return this.request(`/api/chats/${chatId}`, { method: 'DELETE' });
    },

    async getMessages(chatId) {
        return this.request(`/api/chats/${chatId}/messages`);
    },

    // ─── Chat (non-streaming) ───────────────────────────
    async sendMessage(content, chatId = null, mode = 'student') {
        return this.request('/api/chat', {
            method: 'POST',
            body: { content, chat_id: chatId, mode }
        });
    },

    // ─── Chat (streaming via SSE) ───────────────────────
    streamMessage(content, chatId = null, mode = 'student', callbacks = {}) {
        const { onMeta, onChunk, onDone, onError } = callbacks;

        fetch(`${API_BASE}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, chat_id: chatId, mode })
        }).then(response => {
            if (!response.ok) {
                response.json().then(err => {
                    if (onError) onError(err.detail || 'Request failed');
                }).catch(() => {
                    if (onError) onError('Request failed');
                });
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            function read() {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        if (onDone && !buffer.includes('"type": "done"')) {
                            onDone({});
                        }
                        return;
                    }

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.type === 'meta' && onMeta) onMeta(data);
                                if (data.type === 'chunk' && onChunk) onChunk(data.content);
                                if (data.type === 'done' && onDone) onDone(data);
                                if (data.type === 'error' && onError) onError(data.message);
                            } catch (e) {
                                // Skip invalid JSON
                            }
                        }
                    }

                    read();
                }).catch(err => {
                    if (onError) onError(err.message);
                });
            }

            read();
        }).catch(err => {
            if (onError) onError(err.message);
        });
    },

    // ─── Schedules ──────────────────────────────────────
    async confirmSchedule(messageId, chatId, sessions) {
        return this.request('/api/schedule/confirm', {
            method: 'POST',
            body: { message_id: messageId, chat_id: chatId, sessions }
        });
    },

    async getCalendar() {
        return this.request('/api/schedule/calendar');
    },

    async getScheduleForDate(dateStr) {
        return this.request(`/api/schedule/date/${dateStr}`);
    },

    async deleteSchedule(scheduleId) {
        return this.request(`/api/schedule/${scheduleId}`, { method: 'DELETE' });
    },

    async expireSchedules() {
        return this.request('/api/schedule/expire', { method: 'POST' });
    },

    // ─── To-Do ──────────────────────────────────────────
    async getTodayTasks() {
        return this.request('/api/todo/today');
    },

    async updateTaskStatus(taskId, status) {
        return this.request(`/api/todo/${taskId}`, {
            method: 'PATCH',
            body: { status }
        });
    },

    // ─── Stress ─────────────────────────────────────────
    async getStress() {
        return this.request('/api/health/stress');
    },

    // ─── Profile ────────────────────────────────────────
    async getProfile() {
        return this.request('/api/profile');
    },

    async saveProfile(data) {
        return this.request('/api/profile', { method: 'POST', body: data });
    },

    // ─── Subject Colors ─────────────────────────────────
    async getSubjectColors() {
        return this.request('/api/subject-colors');
    },

    async updateSubjectColor(subject, color) {
        return this.request('/api/subject-colors', {
            method: 'POST',
            body: { subject, color }
        });
    },

    // ─── History ────────────────────────────────────────
    async getHistory() {
        return this.request('/api/history');
    },

    async clearHistory() {
        return this.request('/api/history', { method: 'DELETE' });
    },

    // ─── Ranking ────────────────────────────────────────
    async computeRanking(subjects) {
        return this.request('/api/ranking/compute', {
            method: 'POST',
            body: { subjects }
        });
    },

    async handleMissedDay(subjects, missedTopics, availableHours) {
        return this.request('/api/ranking/missed-day', {
            method: 'POST',
            body: { subjects, missed_topics: missedTopics, available_hours: availableHours }
        });
    }
};

// Toast notifications
function showToast(message, type = 'error') {
    const existing = document.querySelector('.error-toast, .success-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = type === 'error' ? 'error-toast' : 'success-toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
