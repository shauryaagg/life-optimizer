/**
 * Chart rendering functions for the Life Optimizer dashboard.
 */

// Keys normalized to lowercase. Lookups use normalizeCategory() below.
const CATEGORY_COLORS = {
    'deep work': '#10b981',
    'development': '#10b981',
    'communication': '#3b82f6',
    'browsing': '#8b5cf6',
    'social media': '#ef4444',
    'entertainment': '#f59e0b',
    'planning': '#06b6d4',
    'productivity': '#06b6d4',
    'learning': '#84cc16',
    'personal': '#ec4899',
    'other': '#6b7280',
};

function normalizeCategory(cat) {
    if (!cat) return 'other';
    // "Deep Work" -> "deep work", "deep_work" -> "deep work"
    return String(cat).toLowerCase().replace(/_/g, ' ').trim();
}

function categoryColor(cat) {
    return CATEGORY_COLORS[normalizeCategory(cat)] || CATEGORY_COLORS['other'];
}

/**
 * Render a category pie chart.
 * @param {string} canvasId - The canvas element ID.
 * @param {Object} data - Category name -> count mapping.
 * @returns {Chart|null} The Chart instance, or null if no data.
 */
function renderCategoryChart(canvasId, data) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const labels = Object.keys(data);
    const values = Object.values(data);

    if (labels.length === 0) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = '14px sans-serif';
        ctx.fillStyle = '#9ca3af';
        ctx.textAlign = 'center';
        ctx.fillText('No data available', canvas.width / 2, canvas.height / 2);
        return null;
    }

    const colors = labels.map(l => categoryColor(l));

    return new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: labels.map(l => {
                // Normalize label display: "deep_work" -> "Deep Work", leave already-cased strings
                const s = String(l).replace(/_/g, ' ');
                return s.charAt(0).toUpperCase() + s.slice(1);
            }),
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 1,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, padding: 10 },
                },
            },
        },
    });
}

/**
 * Render a top apps bar chart.
 * @param {string} canvasId - The canvas element ID.
 * @param {Array} data - Array of {app, count} objects.
 * @returns {Chart|null} The Chart instance, or null if no data.
 */
function renderAppsChart(canvasId, data) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    if (!data || data.length === 0) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = '14px sans-serif';
        ctx.fillStyle = '#9ca3af';
        ctx.textAlign = 'center';
        ctx.fillText('No data available', canvas.width / 2, canvas.height / 2);
        return null;
    }

    const labels = data.map(d => d.app);
    const values = data.map(d => d.count);

    return new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Events',
                data: values,
                backgroundColor: '#6366f1',
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: { beginAtZero: true, ticks: { precision: 0 } },
            },
        },
    });
}


const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

/**
 * Render a weekly trends grouped bar chart comparing this week vs last week.
 * @param {Object} thisWeekData - Response from /api/stats/weekly?week_offset=0.
 * @param {Object} lastWeekData - Response from /api/stats/weekly?week_offset=1.
 * @param {string} canvasId - The canvas element ID.
 * @returns {Chart|null} The Chart instance, or null if no canvas.
 */
function renderWeeklyTrends(thisWeekData, lastWeekData, canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const thisWeekTotals = (thisWeekData.days || []).map(d => d.total_minutes || 0);
    const lastWeekTotals = (lastWeekData.days || []).map(d => d.total_minutes || 0);

    // Pad to 7 if needed
    while (thisWeekTotals.length < 7) thisWeekTotals.push(0);
    while (lastWeekTotals.length < 7) lastWeekTotals.push(0);

    const hasData = thisWeekTotals.some(v => v > 0) || lastWeekTotals.some(v => v > 0);
    if (!hasData) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = '14px sans-serif';
        ctx.fillStyle = '#9ca3af';
        ctx.textAlign = 'center';
        ctx.fillText('No data available', canvas.width / 2, canvas.height / 2);
        return null;
    }

    return new Chart(canvas, {
        type: 'bar',
        data: {
            labels: DAY_LABELS,
            datasets: [
                {
                    label: 'This Week (min)',
                    data: thisWeekTotals,
                    backgroundColor: '#6366f1',
                    borderRadius: 4,
                },
                {
                    label: 'Last Week (min)',
                    data: lastWeekTotals,
                    backgroundColor: '#c7d2fe',
                    borderRadius: 4,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { boxWidth: 12, padding: 10 },
                },
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Minutes' },
                    ticks: { precision: 0 },
                },
            },
        },
    });
}


/**
 * Render a GitHub-style monthly heatmap for deep work.
 * @param {Object} monthData - Response from /api/stats/monthly.
 * @param {string} containerId - The container element ID.
 */
function renderMonthlyHeatmap(monthData, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const days = monthData.days || [];
    if (days.length === 0) {
        container.innerHTML = '<div class="text-center py-8 text-gray-500">No data available for this month.</div>';
        return;
    }

    // Build grid: 7 rows (Mon-Sun) x N columns (weeks)
    // First, figure out which weekday the month starts on
    const firstDate = new Date(days[0].date + 'T00:00:00');
    const startDow = (firstDate.getDay() + 6) % 7; // 0=Mon, 6=Sun

    // Compute the number of weeks
    const lastDate = new Date(days[days.length - 1].date + 'T00:00:00');
    const lastDow = (lastDate.getDay() + 6) % 7;
    const totalDays = days.length + startDow;
    const numWeeks = Math.ceil(totalDays / 7);

    // Build a map of date -> data
    const dayMap = {};
    days.forEach(d => { dayMap[d.date] = d; });

    // Color scale for deep work minutes
    function getColor(deepWorkMin) {
        if (deepWorkMin <= 0) return '#ebedf0';
        if (deepWorkMin <= 120) return '#9be9a8';
        if (deepWorkMin <= 240) return '#40c463';
        return '#216e39';
    }

    let html = '<div style="display: grid; grid-template-columns: 30px repeat(' + numWeeks + ', 1fr); gap: 3px; align-items: center;">';

    const dowLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    for (let row = 0; row < 7; row++) {
        // Row label
        html += '<div class="text-xs text-gray-400 text-right pr-1">' + dowLabels[row] + '</div>';
        for (let col = 0; col < numWeeks; col++) {
            const dayIndex = col * 7 + row - startDow;
            if (dayIndex < 0 || dayIndex >= days.length) {
                html += '<div style="width:100%;aspect-ratio:1;border-radius:2px;background:#f9fafb;"></div>';
            } else {
                const d = days[dayIndex];
                const color = getColor(d.deep_work_minutes || 0);
                const tooltip = d.date + '\\nTotal: ' + Math.round(d.total_minutes) + 'min\\nDeep Work: ' + Math.round(d.deep_work_minutes) + 'min' + (d.top_app ? '\\nTop App: ' + d.top_app : '');
                html += '<div style="width:100%;aspect-ratio:1;border-radius:2px;background:' + color + ';cursor:pointer;" title="' + tooltip + '"></div>';
            }
        }
    }
    html += '</div>';
    container.innerHTML = html;
}


/**
 * Render a Gantt-style focus timeline.
 * @param {Array} sessions - Array of session objects from /api/sessions/timeline.
 * @param {string} containerId - The container element ID.
 */
function renderFocusTimeline(sessions, containerId, numDays) {
    const container = document.getElementById(containerId);
    if (!container) return;

    sessions = sessions || [];
    numDays = numDays || 7;

    // Group by date
    const byDate = {};
    sessions.forEach(s => {
        if (!byDate[s.date]) byDate[s.date] = [];
        byDate[s.date].push(s);
    });

    // Always render `numDays` rows (today going back), even if empty, so
    // the chart has consistent shape. Dates ordered newest first.
    const today = new Date();
    const dates = [];
    for (let i = 0; i < numDays; i++) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        dates.push(d.toISOString().slice(0, 10));
    }

    const TOTAL_MIN = 24 * 60;

    // For each day, collapse consecutive sessions with the same category
    // into contiguous blocks so the user sees clean colored bands instead
    // of hundreds of pinstripes from per-poll sessions.
    function buildBlocks(daySessions) {
        const parsed = [];
        daySessions.forEach(s => {
            if (!s.start_time) return;
            const sp = s.start_time.split(':');
            const startMin = parseInt(sp[0]) * 60 + parseInt(sp[1]);
            let endMin;
            if (s.end_time) {
                const ep = s.end_time.split(':');
                endMin = parseInt(ep[0]) * 60 + parseInt(ep[1]);
                // Handle wrap-around (end past midnight on next UTC day)
                if (endMin < startMin) endMin += TOTAL_MIN;
            } else {
                endMin = startMin + Math.max(s.duration_minutes || 0.5, 0.5);
            }
            endMin = Math.min(endMin, TOTAL_MIN);
            parsed.push({
                start: startMin,
                end: endMin,
                category: s.category || 'Other',
                app: s.app_name,
            });
        });
        parsed.sort((a, b) => a.start - b.start);

        // Merge adjacent blocks of the same category if they touch or
        // overlap (within 2 minutes).
        const blocks = [];
        parsed.forEach(p => {
            const last = blocks[blocks.length - 1];
            if (last && last.category === p.category && p.start <= last.end + 2) {
                last.end = Math.max(last.end, p.end);
                last.apps[p.app] = (last.apps[p.app] || 0) + (p.end - p.start);
            } else {
                blocks.push({
                    start: p.start,
                    end: p.end,
                    category: p.category,
                    apps: { [p.app]: p.end - p.start },
                });
            }
        });
        return blocks;
    }

    let html = '<div class="overflow-x-auto"><div style="min-width: 720px;">';

    // Rows: one per day
    dates.forEach(dt => {
        const blocks = buildBlocks(byDate[dt] || []);
        const totalMin = blocks.reduce((sum, b) => sum + (b.end - b.start), 0);
        const hoursStr = totalMin > 0
            ? Math.floor(totalMin / 60) + 'h ' + Math.round(totalMin % 60) + 'm'
            : '—';

        html += '<div class="flex items-center mb-2">';
        html += '<div style="width:100px;flex-shrink:0;" class="pr-2">'
             + '<div class="text-sm text-gray-700 font-medium">' + dt + '</div>'
             + '<div class="text-xs text-gray-400">' + hoursStr + '</div>'
             + '</div>';
        html += '<div class="relative bg-gray-100 rounded border border-gray-200" style="flex:1;height:32px;">';

        blocks.forEach(b => {
            const leftPct = (b.start / TOTAL_MIN) * 100;
            const widthPct = Math.max(((b.end - b.start) / TOTAL_MIN) * 100, 0.3);
            const dur = Math.round(b.end - b.start);
            const topApp = Object.entries(b.apps).sort((a, c) => c[1] - a[1])[0][0];
            const pad = n => (n < 10 ? '0' : '') + n;
            const startH = Math.floor(b.start / 60), startM = b.start % 60;
            const endH = Math.floor(b.end / 60) % 24, endM = Math.round(b.end % 60);
            const tooltip = b.category + ' · ' + pad(startH) + ':' + pad(startM) + '–' + pad(endH) + ':' + pad(endM) + ' · ' + dur + 'min · mostly ' + topApp;

            html += '<div class="absolute" style="left:' + leftPct + '%;width:' + widthPct + '%;height:100%;background:' + categoryColor(b.category) + ';opacity:0.9;" title="' + tooltip.replace(/"/g, '&quot;') + '"></div>';
        });

        // Subtle hour gridlines
        for (let h = 6; h < 24; h += 6) {
            const pct = (h / 24) * 100;
            html += '<div class="absolute" style="left:' + pct + '%;top:0;bottom:0;width:1px;background:rgba(0,0,0,0.04);"></div>';
        }

        html += '</div></div>';
    });

    // Time axis at bottom — 00, 06, 12, 18, 24
    html += '<div class="flex items-start mt-1">';
    html += '<div style="width:100px;flex-shrink:0;"></div>';
    html += '<div class="relative" style="flex:1;height:18px;">';
    for (let h = 0; h <= 24; h += 6) {
        const pct = (h / 24) * 100;
        const align = h === 0 ? '0' : (h === 24 ? '100% - 3ch' : '-50%');
        html += '<div class="text-xs text-gray-500 absolute" style="left:' + pct + '%;transform:translateX(' + (h === 0 ? '0' : (h === 24 ? '-100%' : '-50%')) + ');">' + (h < 10 ? '0' : '') + h + ':00</div>';
    }
    html += '</div></div>';

    html += '</div></div>';
    container.innerHTML = html;
}
