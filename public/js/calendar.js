/**
 * Calendar Module — Interactive mini calendar with color-coded dots,
 * exam highlights, color legend, and clean table detail view.
 * Enhanced: Exam day highlighting with glow, schedule deletion support.
 */

const Calendar = (() => {
    let currentMonth = new Date().getMonth();
    let currentYear = new Date().getFullYear();
    let calendarData = {};
    let subjectColors = {};

    function init() {
        document.getElementById('cal-prev').addEventListener('click', () => {
            currentMonth--;
            if (currentMonth < 0) { currentMonth = 11; currentYear--; }
            render();
        });

        document.getElementById('cal-next').addEventListener('click', () => {
            currentMonth++;
            if (currentMonth > 11) { currentMonth = 0; currentYear++; }
            render();
        });

        document.getElementById('detail-panel-close').addEventListener('click', () => {
            document.getElementById('detail-panel').classList.remove('open');
        });

        refresh();
    }

    async function refresh() {
        try {
            const data = await Api.getCalendar();
            calendarData = data.calendar || {};
            subjectColors = data.subject_colors || {};
            render();
        } catch (err) {
            // Silent fail on calendar refresh
        }
    }

    function render() {
        const label = document.getElementById('cal-month-label');
        const grid = document.getElementById('cal-grid');
        const legendEl = document.getElementById('cal-legend');

        const monthNames = ['January','February','March','April','May','June',
                           'July','August','September','October','November','December'];
        label.textContent = `${monthNames[currentMonth]} ${currentYear}`;

        // Build calendar grid
        const firstDay = new Date(currentYear, currentMonth, 1).getDay();
        const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
        const today = new Date();

        let html = '';

        // Empty cells before first day
        for (let i = 0; i < firstDay; i++) {
            html += '<div class="cal-day empty"></div>';
        }

        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const isToday = today.getFullYear() === currentYear && 
                           today.getMonth() === currentMonth && 
                           today.getDate() === day;
            
            const dayData = calendarData[dateStr];
            let dotsHtml = '';
            let extraClass = '';
            let examColor = '';
            let examStyle = '';

            if (dayData) {
                const subjects = dayData.subjects || [];
                const hasExam = dayData.has_exam || false;

                // Colored dots for subjects (max 4 visible)
                const uniqueColors = [...new Set(subjects.map(s => s.color))];
                dotsHtml = uniqueColors.slice(0, 4).map(c => 
                    `<span class="cal-dot" style="background:${c}"></span>`
                ).join('');

                // Highlight exam dates with special styling
                if (hasExam) {
                    extraClass = 'has-exam exam-highlight';
                    // Use the exam subject's color for the highlight
                    const examSubj = subjects.find(s => s.type === 'exam' || s.type === 'test' || s.type === 'mock');
                    if (examSubj) {
                        examColor = examSubj.color;
                        examStyle = `border-color: ${examColor}; background: ${examColor}20; box-shadow: 0 0 8px ${examColor}40;`;
                    } else {
                        examStyle = 'border-color: #EF4444; background: rgba(239,68,68,0.12); box-shadow: 0 0 8px rgba(239,68,68,0.3);';
                    }
                }
            }

            html += `
                <div class="cal-day ${isToday ? 'today' : ''} ${extraClass} ${dayData ? 'has-events' : ''}" 
                     data-date="${dateStr}" ${examStyle ? `style="${examStyle}"` : ''}>
                    <span class="cal-day-num">${day}</span>
                    ${dotsHtml ? `<div class="cal-dots">${dotsHtml}</div>` : ''}
                </div>
            `;
        }

        grid.innerHTML = html;

        // Click handler for dates
        grid.querySelectorAll('.cal-day:not(.empty)').forEach(el => {
            el.addEventListener('click', () => {
                const dateStr = el.dataset.date;
                showDateDetail(dateStr);
            });
        });

        // Render color legend (only for active subjects)
        renderLegend(legendEl);
    }

    // ─── Color Legend ───────────────────────────────────────

    function renderLegend(container) {
        if (!container) return;

        // Collect unique subjects from ACTIVE calendar data only
        const subjects = new Map();
        Object.values(calendarData).forEach(dayData => {
            (dayData.subjects || []).forEach(s => {
                if (s.subject && s.subject !== 'Break' && s.subject !== 'Long Break') {
                    subjects.set(s.subject, s.color);
                }
            });
        });

        if (subjects.size === 0) {
            container.innerHTML = '';
            return;
        }

        let html = '<div class="cal-legend-inner">';
        subjects.forEach((color, subject) => {
            html += `
                <div class="cal-legend-item" data-subject="${subject}" title="Click to change color">
                    <span class="cal-legend-dot" style="background:${color}"></span>
                    <span class="cal-legend-label">${subject}</span>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;

        // Click to change color
        container.querySelectorAll('.cal-legend-item').forEach(item => {
            item.addEventListener('click', () => {
                const subject = item.dataset.subject;
                const currentDot = item.querySelector('.cal-legend-dot');
                const currentColor = currentDot.style.background;
                showColorPicker(subject, currentColor, item);
            });
        });
    }

    // ─── Color Picker ───────────────────────────────────────

    function showColorPicker(subject, currentColor, anchorEl) {
        // Remove existing picker
        const existing = document.querySelector('.color-picker-popup');
        if (existing) existing.remove();

        const colors = [
            '#4A90D9', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899',
            '#06B6D4', '#D97706', '#059669', '#7C3AED', '#2563EB',
            '#EF4444', '#0891B2', '#DC2626', '#9333EA', '#E11D48',
        ];

        const popup = document.createElement('div');
        popup.className = 'color-picker-popup';
        popup.innerHTML = `
            <div class="color-picker-title">Color for ${subject}</div>
            <div class="color-picker-grid">
                ${colors.map(c => `<div class="color-picker-swatch ${c === currentColor ? 'active' : ''}" data-color="${c}" style="background:${c}"></div>`).join('')}
            </div>
        `;

        anchorEl.appendChild(popup);

        popup.querySelectorAll('.color-picker-swatch').forEach(swatch => {
            swatch.addEventListener('click', async (e) => {
                e.stopPropagation();
                const newColor = swatch.dataset.color;
                try {
                    await Api.updateSubjectColor(subject, newColor);
                    showToast(`${subject} color updated!`, 'success');
                    popup.remove();
                    refresh();
                } catch (err) {
                    showToast('Failed to update color');
                }
            });
        });

        // Close on outside click
        setTimeout(() => {
            document.addEventListener('click', function closePopup(e) {
                if (!popup.contains(e.target)) {
                    popup.remove();
                    document.removeEventListener('click', closePopup);
                }
            });
        }, 100);
    }

    // ─── Date Detail Panel ──────────────────────────────────
    // Shows a CLEAN TABLE for the selected date with delete support

    async function showDateDetail(dateStr) {
        const panel = document.getElementById('detail-panel');
        const titleEl = document.getElementById('detail-panel-title');
        const contentEl = document.getElementById('detail-panel-content');

        // Format date for display
        const dateLabel = formatDateForPanel(dateStr);
        titleEl.textContent = `📅 ${dateLabel}`;

        contentEl.innerHTML = '<div class="detail-loading">Loading...</div>';
        panel.classList.add('open');

        try {
            const data = await Api.getScheduleForDate(dateStr);
            const sessions = data.sessions || [];

            if (sessions.length === 0) {
                contentEl.innerHTML = `
                    <div class="detail-empty">
                        <div class="detail-empty-icon">📭</div>
                        <p>No study tasks planned for this day.</p>
                        <p class="detail-empty-hint">Start a chat to create a study schedule!</p>
                    </div>
                `;
                return;
            }

            // Render as clean TABLE
            let tableHtml = `
                <div class="detail-table-wrapper">
                    <table class="detail-table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Subject</th>
                                <th>Task</th>
                                <th>Status</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            sessions.forEach(s => {
                const statusClass = s.status || 'pending';
                const statusIcon = {
                    'pending': '⏳',
                    'in_progress': '📖',
                    'completed': '✅',
                    'missed': '❌'
                }[statusClass] || '⏳';

                const isBreak = s.session_type === 'break';

                tableHtml += `
                    <tr class="detail-row ${isBreak ? 'is-break-row' : ''}">
                        <td class="detail-time">${s.start_time} – ${s.end_time}</td>
                        <td class="detail-subject">
                            <span class="detail-color-dot" style="background:${s.color}"></span>
                            ${s.subject}
                        </td>
                        <td class="detail-task">${s.topic || s.session_type}</td>
                        <td class="detail-status" data-task-id="${s.id}" data-status="${statusClass}">
                            <span class="status-badge ${statusClass}">${statusIcon} ${statusClass}</span>
                        </td>
                        <td class="detail-actions">
                            ${!isBreak ? `<button class="detail-delete-btn" data-schedule-id="${s.id}" title="Delete">🗑️</button>` : ''}
                        </td>
                    </tr>
                `;
            });

            tableHtml += '</tbody></table></div>';
            contentEl.innerHTML = tableHtml;

            // Click status to cycle
            contentEl.querySelectorAll('.detail-status').forEach(cell => {
                cell.addEventListener('click', async () => {
                    const taskId = cell.dataset.taskId;
                    const current = cell.dataset.status;
                    const next = cycleStatus(current);
                    
                    try {
                        await Api.updateTaskStatus(taskId, next);
                        cell.dataset.status = next;
                        const icon = {'pending':'⏳','in_progress':'📖','completed':'✅','missed':'❌'}[next] || '⏳';
                        cell.innerHTML = `<span class="status-badge ${next}">${icon} ${next}</span>`;
                        Todo.refresh();
                        Stress.refresh();
                        History.refresh();
                    } catch (err) {
                        showToast('Failed to update status');
                    }
                });
            });

            // Delete buttons
            contentEl.querySelectorAll('.detail-delete-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const scheduleId = btn.dataset.scheduleId;
                    if (confirm('Delete this schedule entry?')) {
                        try {
                            await Api.deleteSchedule(scheduleId);
                            showToast('Schedule entry deleted', 'success');
                            // Refresh everything
                            showDateDetail(dateStr);
                            refresh();
                            Todo.refresh();
                            Stress.refresh();
                            History.refresh();
                        } catch (err) {
                            showToast('Failed to delete');
                        }
                    }
                });
            });

        } catch (err) {
            contentEl.innerHTML = `<div class="detail-empty">Failed to load schedule.</div>`;
        }
    }

    function cycleStatus(current) {
        const cycle = ['pending', 'in_progress', 'completed', 'missed'];
        const idx = cycle.indexOf(current);
        return cycle[(idx + 1) % cycle.length];
    }

    function formatDateForPanel(dateStr) {
        try {
            const d = new Date(dateStr + 'T00:00:00');
            const today = new Date();
            today.setHours(0,0,0,0);
            const tomorrow = new Date(today);
            tomorrow.setDate(tomorrow.getDate() + 1);

            if (d.getTime() === today.getTime()) return 'Today';
            if (d.getTime() === tomorrow.getTime()) return 'Tomorrow';

            return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
        } catch {
            return dateStr;
        }
    }

    return { init, refresh };
})();
