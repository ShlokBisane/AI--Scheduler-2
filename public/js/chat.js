/**
 * Chat Module — Handles the chat interface, messages, and schedule cards
 * V2: Strips raw JSON/code from display, groups multi-day schedules
 */

const Chat = (() => {
    let currentChatId = null;
    let currentMode = 'student';
    let isStreaming = false;

    const elements = {};

    function init() {
        elements.messages = document.getElementById('chat-messages');
        elements.input = document.getElementById('chat-input');
        elements.sendBtn = document.getElementById('send-btn');
        elements.welcomeScreen = document.getElementById('welcome-screen');
        elements.titleDisplay = document.getElementById('chat-title-display');

        // Send message
        elements.sendBtn.addEventListener('click', sendMessage);
        elements.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Auto-resize textarea
        elements.input.addEventListener('input', () => {
            elements.input.style.height = 'auto';
            elements.input.style.height = Math.min(elements.input.scrollHeight, 150) + 'px';
            elements.sendBtn.disabled = !elements.input.value.trim();
        });

        // Welcome card clicks
        document.querySelectorAll('.welcome-card').forEach(card => {
            card.addEventListener('click', () => {
                const prompt = card.dataset.prompt;
                elements.input.value = prompt;
                elements.sendBtn.disabled = false;
                sendMessage();
            });
        });
    }

    function setMode(mode) {
        currentMode = mode;
    }

    function setChatId(id) {
        currentChatId = id;
    }

    function getChatId() {
        return currentChatId;
    }

    async function loadChat(chatId) {
        currentChatId = chatId;
        elements.messages.innerHTML = '';

        // Hide welcome screen
        const ws = document.getElementById('welcome-screen');
        if (ws) ws.style.display = 'none';

        // Show chat area
        const chatArea = document.getElementById('chat-area');
        if (chatArea) chatArea.style.display = 'flex';

        // Hide profile if visible
        const profilePage = document.getElementById('profile-page');
        if (profilePage) profilePage.style.display = 'none';

        try {
            const data = await Api.getMessages(chatId);
            const messages = data.messages || [];

            for (const msg of messages) {
                if (msg.role === 'system') continue;
                appendMessage(msg.role === 'user' ? 'user' : 'assistant', msg.content, msg.schedule_json, msg.id, msg.confirmed);
            }

            scrollToBottom();
        } catch (err) {
            showToast('Failed to load chat: ' + err.message);
        }
    }

    function newChat() {
        currentChatId = null;
        elements.messages.innerHTML = '';
        elements.titleDisplay.textContent = 'Master Scheduler AI';

        // Show chat area, hide profile
        const chatArea = document.getElementById('chat-area');
        if (chatArea) chatArea.style.display = 'flex';
        const profilePage = document.getElementById('profile-page');
        if (profilePage) profilePage.style.display = 'none';

        // Re-add welcome screen
        const welcome = createWelcomeScreen();
        elements.messages.appendChild(welcome);
    }

    function createWelcomeScreen() {
        const div = document.createElement('div');
        div.className = 'welcome-screen';
        div.id = 'welcome-screen';
        div.innerHTML = `
            <div class="welcome-icon">✦</div>
            <h2>Master Scheduler AI</h2>
            <p class="welcome-subtitle">Your intelligent study planner & academic scheduler</p>
            <div class="welcome-cards">
                <div class="welcome-card" data-prompt="I have a Physics exam on May 15 and need a study plan">
                    <div class="wc-icon">📚</div>
                    <div class="wc-text">Create a study plan for an upcoming exam</div>
                </div>
                <div class="welcome-card" data-prompt="I'm preparing for JEE and have 3 months left. Help me plan">
                    <div class="wc-icon">🎯</div>
                    <div class="wc-text">Plan for competitive exams like JEE or NEET</div>
                </div>
                <div class="welcome-card" data-prompt="I missed 2 days of study. Help me recover my schedule">
                    <div class="wc-icon">🔄</div>
                    <div class="wc-text">Reschedule after missing study days</div>
                </div>
                <div class="welcome-card" data-prompt="I need to schedule 6 class tests within 10 days">
                    <div class="wc-icon">👨‍🏫</div>
                    <div class="wc-text">Teacher: Schedule tests and exams</div>
                </div>
            </div>
        `;

        div.querySelectorAll('.welcome-card').forEach(card => {
            card.addEventListener('click', () => {
                elements.input.value = card.dataset.prompt;
                elements.sendBtn.disabled = false;
                sendMessage();
            });
        });

        return div;
    }

    // ─── STREAMING MESSAGE ──────────────────────────────────

    async function sendMessage() {
        const content = elements.input.value.trim();
        if (!content || isStreaming) return;

        // Remove welcome screen
        const welcome = document.getElementById('welcome-screen');
        if (welcome) welcome.remove();

        // Add user message
        appendMessage('user', content);
        elements.input.value = '';
        elements.input.style.height = 'auto';
        elements.sendBtn.disabled = true;

        // Show typing indicator
        const typingEl = showTyping();
        isStreaming = true;

        // Create streaming message container
        const aiMsg = appendMessage('assistant', '', null, null, false, true);
        const contentEl = aiMsg.querySelector('.message-text');

        let fullResponse = '';
        let streamChatId = currentChatId;

        Api.streamMessage(content, currentChatId, currentMode, {
            onMeta(data) {
                streamChatId = data.chat_id;
                currentChatId = data.chat_id;
            },
            onChunk(text) {
                if (typingEl.parentNode) typingEl.remove();
                fullResponse += text;
                // Strip raw schedule JSON from display during streaming
                const cleanText = stripScheduleBlocks(fullResponse);
                contentEl.innerHTML = formatMarkdown(cleanText);
                scrollToBottom();
            },
            onDone(data) {
                isStreaming = false;
                if (typingEl.parentNode) typingEl.remove();

                if (data.chat_id) {
                    currentChatId = data.chat_id;
                }

                // Update chat title
                if (data.chat_title) {
                    elements.titleDisplay.textContent = data.chat_title;
                }
                
                // Always refresh chat list
                App.refreshChatList();

                // Clean the final displayed text (remove any leftover code)
                const finalClean = stripScheduleBlocks(fullResponse);
                contentEl.innerHTML = formatMarkdown(finalClean);

                // Render schedule card if present
                if (data.schedule) {
                    const card = createScheduleCard(data.schedule, data.message_id, currentChatId);
                    aiMsg.querySelector('.message-content').appendChild(card);
                    scrollToBottom();
                }

                // Refresh sidebar data
                Calendar.refresh();
                Todo.refresh();
                Stress.refresh();
            },
            onError(message) {
                isStreaming = false;
                if (typingEl.parentNode) typingEl.remove();
                contentEl.innerHTML = `<p style="color: var(--red);">⚠️ ${message}</p>`;
                scrollToBottom();
                App.refreshChatList();
            }
        });
    }

    // ─── STRIP SCHEDULE JSON FROM DISPLAY ───────────────────
    // This is the KEY fix: never show raw code/JSON to the user

    function stripScheduleBlocks(text) {
        if (!text) return '';
        let cleaned = text;

        // Remove complete ```schedule...``` blocks
        cleaned = cleaned.replace(/```[Ss]chedule\s*\n[\s\S]*?\n```/g, '');
        
        // Remove complete ```json blocks containing "sessions"
        cleaned = cleaned.replace(/```(?:json|JSON)?\s*\n[\s\S]*?"sessions"[\s\S]*?\n```/g, '');

        // Remove partial schedule blocks still being streamed
        // If we see ```schedule or ```json{ with "sessions" but no closing ```, hide it
        cleaned = cleaned.replace(/```[Ss]chedule\s*\n[\s\S]*$/g, '');
        cleaned = cleaned.replace(/```(?:json|JSON)?\s*\n\s*\{[\s\S]*"sessions"[\s\S]*$/g, '');

        // Remove any bare JSON blocks that look like schedule data
        cleaned = cleaned.replace(/\{[^{}]*"sessions"\s*:\s*\[[\s\S]*?\]\s*\}/g, '');

        // Remove partial bare JSON with "sessions" still streaming
        cleaned = cleaned.replace(/\{[^{}]*"sessions"\s*:\s*\[[\s\S]*$/g, '');

        // Clean up excessive whitespace
        cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

        return cleaned.trim();
    }

    // ─── APPEND MESSAGE ─────────────────────────────────────

    function appendMessage(role, content, scheduleData = null, messageId = null, confirmed = false, isStreamingMsg = false) {
        const div = document.createElement('div');
        div.className = `message ${role}`;

        const avatar = role === 'user' ? '👤' : '✦';
        // Strip schedule blocks from saved messages too
        const cleanContent = isStreamingMsg ? '' : stripScheduleBlocks(content);
        const formattedContent = isStreamingMsg ? '' : formatMarkdown(cleanContent);

        div.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-text">${formattedContent}</div>
            </div>
        `;

        // Add schedule card if present
        if (scheduleData && !isStreamingMsg) {
            const card = createScheduleCard(scheduleData, messageId, currentChatId, confirmed);
            div.querySelector('.message-content').appendChild(card);
        }

        elements.messages.appendChild(div);
        scrollToBottom();
        return div;
    }

    // ─── SCHEDULE CARD ──────────────────────────────────────
    // V2: Groups sessions by date for multi-day readability

    function createScheduleCard(schedule, messageId, chatId, isConfirmed = false) {
        const card = document.createElement('div');
        card.className = 'schedule-card';

        const title = schedule.title || 'Proposed Schedule';
        const sessions = schedule.sessions || [];

        // Group sessions by date
        const grouped = {};
        sessions.forEach(s => {
            const dateKey = s.date || 'Unscheduled';
            if (!grouped[dateKey]) grouped[dateKey] = [];
            grouped[dateKey].push(s);
        });

        const dates = Object.keys(grouped).sort();
        const studySessions = sessions.filter(s => s.type !== 'break');

        let sessionsHtml = '';
        
        if (dates.length > 1) {
            // Multi-day: show date headers
            sessionsHtml = dates.map(dateStr => {
                const daySessions = grouped[dateStr];
                const dateLabel = formatDateLabel(dateStr);
                const dayHtml = daySessions.map(s => renderSessionRow(s)).join('');
                return `
                    <div class="schedule-date-group">
                        <div class="schedule-date-header">📅 ${dateLabel}</div>
                        ${dayHtml}
                    </div>
                `;
            }).join('');
        } else {
            // Single day: no date headers needed
            sessionsHtml = sessions.map(s => renderSessionRow(s)).join('');
        }

        const confirmBtnText = isConfirmed ? '✓ Saved to Calendar' : '✓ Confirm & Save to Calendar';
        const confirmBtnClass = isConfirmed ? 'confirm-btn confirmed' : 'confirm-btn';
        const confirmBtnDisabled = isConfirmed ? 'disabled' : '';
        const deleteBtnHtml = isConfirmed && messageId
            ? `<button class="schedule-delete-btn" data-message-id="${messageId}" data-chat-id="${chatId}">Delete from Calendar</button>`
            : '';

        card.innerHTML = `
            <div class="schedule-card-header">
                <span class="schedule-card-title">${title}</span>
                <span style="font-size:12px; color: var(--text-tertiary)">${studySessions.length} study sessions · ${dates.length} day${dates.length > 1 ? 's' : ''}</span>
            </div>
            <div class="schedule-sessions">${sessionsHtml}</div>
            <div class="schedule-card-footer">
                <button class="${confirmBtnClass}" data-message-id="${messageId}" data-chat-id="${chatId}" ${confirmBtnDisabled}>${confirmBtnText}</button>
                ${deleteBtnHtml}
            </div>
        `;

        // Confirm button handler (always attach)
        const btn = card.querySelector('.confirm-btn');
        btn.addEventListener('click', async () => {
            if (btn.disabled || btn.classList.contains('confirmed')) return;
            if (!messageId || !chatId) {
                showToast('Missing schedule metadata');
                return;
            }

            try {
                btn.disabled = true;
                btn.textContent = 'Saving...';

                await Api.confirmSchedule(messageId, chatId, sessions);

                btn.className = 'confirm-btn confirmed';
                btn.textContent = '✓ Saved to Calendar';
                btn.disabled = true;
                ensureDeleteButton();
                showToast('Schedule saved to calendar!', 'success');

                // Refresh sidebar
                Calendar.refresh();
                Todo.refresh();
                Stress.refresh();
                if (typeof History !== 'undefined') History.refresh();
            } catch (err) {
                btn.disabled = false;
                btn.textContent = '✓ Confirm & Save to Calendar';
                showToast('Failed to save: ' + err.message);
            }
        });

        // Delete button handler
        const existingDeleteBtn = card.querySelector('.schedule-delete-btn');
        if (existingDeleteBtn) {
            attachDeleteHandler(existingDeleteBtn);
        }

        function ensureDeleteButton() {
            if (!messageId) return;
            const footer = card.querySelector('.schedule-card-footer');
            if (footer.querySelector('.schedule-delete-btn')) return;
            const delBtn = document.createElement('button');
            delBtn.className = 'schedule-delete-btn';
            delBtn.dataset.messageId = messageId;
            delBtn.dataset.chatId = chatId;
            delBtn.textContent = 'Delete from Calendar';
            footer.appendChild(delBtn);
            attachDeleteHandler(delBtn);
        }

        function attachDeleteHandler(deleteBtn) {
            deleteBtn.addEventListener('click', async () => {
                if (!messageId) return;
                if (!confirm('Remove this schedule from calendar?')) return;

                const originalText = deleteBtn.textContent;
                deleteBtn.disabled = true;
                deleteBtn.textContent = 'Deleting...';

                try {
                    const result = await Api.deleteScheduleBatch(messageId);
                    const deletedCount = result && typeof result.deleted_count === 'number'
                        ? result.deleted_count
                        : 0;
                    if (deletedCount <= 0) {
                        throw new Error('No schedule entries were deleted');
                    }

                    btn.className = 'confirm-btn';
                    btn.textContent = '✓ Confirm & Save to Calendar';
                    btn.disabled = false;
                    deleteBtn.remove();

                    const restored = result && result.restored;
                    const msg = restored
                        ? 'Schedule removed. Previous schedule restored.'
                        : 'Schedule removed from calendar.';
                    showToast(msg, 'success');

                    Calendar.refresh();
                    Todo.refresh();
                    Stress.refresh();
                    if (typeof History !== 'undefined') History.refresh();
                } catch (err) {
                    deleteBtn.disabled = false;
                    deleteBtn.textContent = originalText;
                    showToast('Failed to delete schedule: ' + err.message);
                }
            });
        }

        return card;
    }

    function renderSessionRow(s) {
        return `
            <div class="schedule-session ${s.type === 'break' ? 'is-break' : ''}">
                <div class="session-color-bar" style="background: ${s.color}"></div>
                <span class="session-subject">${s.subject}</span>
                <span class="session-topic">${s.topic || ''}</span>
                <span class="session-time">${s.start_time} – ${s.end_time}</span>
                <span class="session-type-badge ${s.type}">${s.type}</span>
            </div>
        `;
    }

    function formatDateLabel(dateStr) {
        try {
            const d = new Date(dateStr + 'T00:00:00');
            const today = new Date();
            today.setHours(0,0,0,0);
            const tomorrow = new Date(today);
            tomorrow.setDate(tomorrow.getDate() + 1);

            if (d.getTime() === today.getTime()) return 'Today';
            if (d.getTime() === tomorrow.getTime()) return 'Tomorrow';

            return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        } catch {
            return dateStr;
        }
    }

    // ─── TYPING INDICATOR ───────────────────────────────────

    function showTyping() {
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.innerHTML = `
            <div class="message-avatar">✦</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        elements.messages.appendChild(div);
        scrollToBottom();
        return div;
    }

    // ─── MARKDOWN FORMATTING ────────────────────────────────

    function formatMarkdown(text) {
        if (!text) return '';

        let html = text
            // Bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Inline code (but NOT code blocks)
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Headers
            .replace(/^### (.*$)/gm, '<h4>$1</h4>')
            .replace(/^## (.*$)/gm, '<h3>$1</h3>')
            .replace(/^# (.*$)/gm, '<h2>$1</h2>')
            // Unordered lists
            .replace(/^\* (.*$)/gm, '<li>$1</li>')
            .replace(/^- (.*$)/gm, '<li>$1</li>')
            // Numbered lists
            .replace(/^\d+\. (.*$)/gm, '<li>$1</li>')
            // Line breaks
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

        // Wrap in paragraphs
        if (!html.startsWith('<')) {
            html = '<p>' + html + '</p>';
        }

        // Wrap consecutive <li> in <ul>
        html = html.replace(/(<li>.*?<\/li>)+/gs, (match) => '<ul>' + match + '</ul>');

        return html;
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            elements.messages.scrollTop = elements.messages.scrollHeight;
        });
    }

    return { init, setMode, setChatId, getChatId, loadChat, newChat, sendMessage };
})();
