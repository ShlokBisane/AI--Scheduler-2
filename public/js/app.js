/**
 * App Module — Main initialization, sidebar management, settings
 */

const App = (() => {
    let sidebarOpen = true;

    function init() {
        // Initialize all modules
        Chat.init();
        Calendar.init();
        Todo.init();
        Stress.init();
        Voice.init();
        Profile.init();
        History.init();

        setupSidebar();
        setupModeToggle();
        refreshChatList();

        // Auto-expire past schedules on page load
        expireOldSchedules();

        // Close sidebar on mobile by default
        if (window.innerWidth <= 768) {
            sidebarOpen = false;
            document.getElementById('sidebar').classList.add('collapsed');
        }
    }

    // ─── Sidebar ────────────────────────────────────────

    function setupSidebar() {
        const sidebar = document.getElementById('sidebar');
        const toggleBtn = document.getElementById('sidebar-toggle');
        const closeBtn = document.getElementById('sidebar-close');
        const newChatBtn = document.getElementById('new-chat-btn');
        const profileBtn = document.getElementById('profile-btn');

        toggleBtn.addEventListener('click', () => {
            sidebarOpen = !sidebarOpen;
            sidebar.classList.toggle('collapsed', !sidebarOpen);
        });

        closeBtn.addEventListener('click', () => {
            sidebarOpen = false;
            sidebar.classList.add('collapsed');
        });

        newChatBtn.addEventListener('click', () => {
            Chat.newChat();
            // Deselect all chat items
            document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
            // Close sidebar on mobile
            if (window.innerWidth <= 768) {
                sidebarOpen = false;
                sidebar.classList.add('collapsed');
            }
        });

        // Mobile: close sidebar when clicking outside
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && sidebarOpen) {
                if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                    sidebarOpen = false;
                    sidebar.classList.add('collapsed');
                }
            }
        });

        // Mobile: swipe to close
        let touchStartX = 0;
        sidebar.addEventListener('touchstart', (e) => {
            touchStartX = e.touches[0].clientX;
        }, { passive: true });

        sidebar.addEventListener('touchend', (e) => {
            const touchEndX = e.changedTouches[0].clientX;
            const diff = touchStartX - touchEndX;
            if (diff > 80) { // Swipe left
                sidebarOpen = false;
                sidebar.classList.add('collapsed');
            }
        }, { passive: true });
    }

    // ─── Chat List ──────────────────────────────────────

    async function refreshChatList() {
        const list = document.getElementById('chat-list');

        try {
            const data = await Api.getChats();
            const chats = data.chats || [];

            if (chats.length === 0) {
                list.innerHTML = '<div class="no-chats">No conversations yet</div>';
                return;
            }

            list.innerHTML = chats.map(chat => {
                const isActive = chat.id === Chat.getChatId();
                const icon = chat.mode === 'teacher' ? '👨‍🏫' : '💬';
                return `
                    <div class="chat-item ${isActive ? 'active' : ''}" data-chat-id="${chat.id}">
                        <span>${icon}</span>
                        <span style="flex:1; overflow:hidden; text-overflow:ellipsis">${chat.title}</span>
                        <button class="chat-delete" data-chat-id="${chat.id}" title="Delete chat">×</button>
                    </div>
                `;
            }).join('');

            // Click to load chat
            list.querySelectorAll('.chat-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    if (e.target.classList.contains('chat-delete')) return;
                    const chatId = parseInt(item.dataset.chatId);
                    
                    // Update active state
                    list.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
                    item.classList.add('active');
                    
                    Chat.loadChat(chatId);

                    // Update title
                    const titleSpan = item.querySelector('span:nth-child(2)');
                    document.getElementById('chat-title-display').textContent = titleSpan.textContent;

                    // Close sidebar on mobile
                    if (window.innerWidth <= 768) {
                        sidebarOpen = false;
                        document.getElementById('sidebar').classList.add('collapsed');
                    }
                });
            });

            // Delete chat
            list.querySelectorAll('.chat-delete').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const chatId = parseInt(btn.dataset.chatId);
                    if (confirm('Delete this chat?')) {
                        try {
                            await Api.deleteChat(chatId);
                            if (chatId === Chat.getChatId()) {
                                Chat.newChat();
                            }
                            refreshChatList();
                            Calendar.refresh();
                            Todo.refresh();
                            Stress.refresh();
                        } catch (err) {
                            showToast('Failed to delete chat');
                        }
                    }
                });
            });

        } catch (err) {
            list.innerHTML = '<div class="no-chats">Failed to load chats</div>';
        }
    }

    // ─── Mode Toggle ────────────────────────────────────

    function setupModeToggle() {
        const studentBtn = document.getElementById('mode-student');
        const teacherBtn = document.getElementById('mode-teacher');

        studentBtn.addEventListener('click', () => {
            studentBtn.classList.add('active');
            teacherBtn.classList.remove('active');
            Chat.setMode('student');
        });

        teacherBtn.addEventListener('click', () => {
            teacherBtn.classList.add('active');
            studentBtn.classList.remove('active');
            Chat.setMode('teacher');
        });
    }

    // ─── Auto-expire old schedules ──────────────────────

    async function expireOldSchedules() {
        try {
            const result = await Api.expireSchedules();
            if (result.expired_count > 0) {
                Calendar.refresh();
                Todo.refresh();
                Stress.refresh();
                History.refresh();
            }
        } catch (err) {
            // Silent fail
        }
    }

    return { init, refreshChatList };
})();

// ─── Bootstrap ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
