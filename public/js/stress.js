/**
 * Stress Meter Module — SVG gauge showing schedule health + fullness
 * Shows how packed/full the schedule is
 */

const Stress = (() => {
    function init() {
        refresh();
    }

    async function refresh() {
        try {
            const data = await Api.getStress();
            render(data);
        } catch (err) {
            // Silent fail
        }
    }

    function render(data) {
        const arc = document.getElementById('stress-arc');
        const valueText = document.getElementById('stress-value');
        const labelText = document.getElementById('stress-label');
        const stats = document.getElementById('stress-stats');
        const fullnessEl = document.getElementById('stress-fullness');

        if (!arc || !valueText) return;

        const score = data.score || 0;
        const level = data.level || 'green';
        const fullness = data.fullness || 0;

        // Arc calculation (semicircle, total length ~251)
        const totalLength = 251;
        const offset = totalLength - (totalLength * score / 100);

        // Color based on level
        const colors = {
            green: '#10B981',
            yellow: '#F59E0B',
            orange: '#F97316',
            red: '#EF4444'
        };

        arc.style.transition = 'stroke-dashoffset 1s ease-out, stroke 0.5s ease';
        arc.setAttribute('stroke-dashoffset', offset);
        arc.setAttribute('stroke', colors[level] || '#10B981');

        valueText.textContent = `${score}%`;
        labelText.textContent = data.label || '';

        // Stats
        if (stats) {
            stats.innerHTML = `
                <span class="stress-stat"><span class="dot" style="background: ${colors.green}"></span> ${data.completed || 0} done</span>
                <span class="stress-stat"><span class="dot" style="background: ${colors.yellow}"></span> ${data.upcoming || 0} upcoming</span>
                <span class="stress-stat"><span class="dot" style="background: ${colors.red}"></span> ${data.missed || 0} missed</span>
            `;
        }

        // Schedule fullness indicator
        if (fullnessEl) {
            const totalHours = data.total_study_hours || 0;
            const avgHours = data.avg_daily_hours || 0;
            const days = data.scheduled_days || 0;

            if (totalHours > 0) {
                // Fullness bar
                const fullnessColor = fullness < 50 ? '#10B981' : fullness < 75 ? '#F59E0B' : '#EF4444';
                const fullnessLabel = fullness < 40 ? 'Light' : fullness < 65 ? 'Moderate' : fullness < 85 ? 'Packed' : 'Overloaded!';
                
                fullnessEl.innerHTML = `
                    <div class="fullness-header">
                        <span class="fullness-title">Schedule Load</span>
                        <span class="fullness-value" style="color: ${fullnessColor}">${fullnessLabel}</span>
                    </div>
                    <div class="fullness-bar">
                        <div class="fullness-fill" style="width: ${Math.min(fullness, 100)}%; background: ${fullnessColor}"></div>
                    </div>
                    <div class="fullness-details">
                        <span>${totalHours}h total</span>
                        <span>${avgHours}h/day avg</span>
                        <span>${days} days</span>
                    </div>
                `;
            } else {
                fullnessEl.innerHTML = '';
            }
        }
    }

    return { init, refresh };
})();
