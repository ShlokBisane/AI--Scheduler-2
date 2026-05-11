/**
 * To-Do Module — Fully functional task list with status toggles,
 * overdue tracking, priority highlighting, and next-task indicator.
 */

const Todo = (() => {
    let isExpanded = true;

    function init() {
        const toggle = document.getElementById('todo-toggle');
        const list = document.getElementById('todo-list');

        if (toggle) {
            toggle.addEventListener('click', () => {
                isExpanded = !isExpanded;
                list.classList.toggle('collapsed', !isExpanded);
                toggle.classList.toggle('collapsed', !isExpanded);
            });
        }

        refresh();
    }

    async function refresh() {
        const list = document.getElementById('todo-list');
        const countBadge = document.getElementById('todo-count');

        try {
            const data = await Api.getTodayTasks();
            const tasks = data.tasks || [];
            const overdue = data.overdue || [];
            const nextTask = data.next_task;
            const stats = data.stats || {};

            // Update count badge
            const activeCount = (stats.pending || 0) + (stats.in_progress || 0) + overdue.length;
            countBadge.textContent = activeCount;
            countBadge.className = 'badge' + (activeCount > 0 ? ' has-items' : '');

            if (tasks.length === 0 && overdue.length === 0) {
                list.innerHTML = '<div class="todo-empty">No tasks for today</div>';
                return;
            }

            let html = '';

            // Overdue tasks section
            if (overdue.length > 0) {
                html += `<div class="todo-section-label overdue-label">⚠️ Overdue (${overdue.length})</div>`;
                overdue.forEach(task => {
                    html += renderTodoItem(task, true);
                });
            }

            // Next upcoming task highlight
            if (nextTask) {
                html += `<div class="todo-section-label next-label">⏭️ Next Up</div>`;
                html += renderTodoItem(nextTask, false, true);
            }

            // Today's tasks grouped by status
            const studyTasks = tasks.filter(t => t.session_type !== 'break');
            const pending = studyTasks.filter(t => t.status === 'pending' && (!nextTask || t.id !== nextTask.id));
            const inProgress = studyTasks.filter(t => t.status === 'in_progress');
            const completed = studyTasks.filter(t => t.status === 'completed');
            const missed = studyTasks.filter(t => t.status === 'missed');

            if (inProgress.length > 0) {
                html += `<div class="todo-section-label">📖 In Progress</div>`;
                inProgress.forEach(t => { html += renderTodoItem(t); });
            }

            if (pending.length > 0) {
                html += `<div class="todo-section-label">⏳ Pending (${pending.length})</div>`;
                pending.forEach(t => { html += renderTodoItem(t); });
            }

            if (completed.length > 0) {
                html += `<div class="todo-section-label completed-label">✅ Completed (${completed.length})</div>`;
                completed.forEach(t => { html += renderTodoItem(t); });
            }

            if (missed.length > 0) {
                html += `<div class="todo-section-label missed-label">❌ Missed (${missed.length})</div>`;
                missed.forEach(t => { html += renderTodoItem(t); });
            }

            list.innerHTML = html;

            // Attach click handlers for status toggle
            list.querySelectorAll('.todo-item').forEach(item => {
                item.addEventListener('click', async () => {
                    const taskId = item.dataset.taskId;
                    const currentStatus = item.dataset.status;
                    const nextStatus = cycleStatus(currentStatus);

                    try {
                        await Api.updateTaskStatus(taskId, nextStatus);
                        item.dataset.status = nextStatus;
                        refresh(); // Re-render the whole list
                        Stress.refresh();
                        Calendar.refresh();
                        if (typeof History !== 'undefined') History.refresh();
                    } catch (err) {
                        showToast('Failed to update task');
                    }
                });
            });

        } catch (err) {
            list.innerHTML = '<div class="todo-empty">Failed to load tasks</div>';
        }
    }

    function renderTodoItem(task, isOverdue = false, isNext = false) {
        const statusIcons = {
            'pending': '○',
            'in_progress': '◐',
            'completed': '●',
            'missed': '✕'
        };

        const icon = statusIcons[task.status] || '○';
        const priorityClass = task.priority >= 4 ? 'high-priority' : task.priority >= 3 ? 'med-priority' : '';

        return `
            <div class="todo-item ${task.status} ${isOverdue ? 'overdue' : ''} ${isNext ? 'next-up' : ''} ${priorityClass}" 
                 data-task-id="${task.id}" data-status="${task.status}">
                <span class="todo-status-icon">${icon}</span>
                <div class="todo-info">
                    <div class="todo-subject">
                        <span class="todo-color-dot" style="background:${task.color}"></span>
                        ${task.subject}
                    </div>
                    <div class="todo-topic">${task.topic || task.session_type}</div>
                </div>
                <span class="todo-time">${task.start_time}–${task.end_time}</span>
            </div>
        `;
    }

    function cycleStatus(current) {
        const cycle = ['pending', 'in_progress', 'completed', 'missed'];
        const idx = cycle.indexOf(current);
        return cycle[(idx + 1) % cycle.length];
    }

    return { init, refresh };
})();
