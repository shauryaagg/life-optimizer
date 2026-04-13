/**
 * Chart rendering functions for the Life Optimizer dashboard.
 */

const CATEGORY_COLORS = {
    'deep_work': '#10b981',
    'communication': '#3b82f6',
    'browsing': '#8b5cf6',
    'social_media': '#ef4444',
    'entertainment': '#f59e0b',
    'planning': '#06b6d4',
    'learning': '#84cc16',
    'personal': '#ec4899',
    'other': '#6b7280',
};

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

    const colors = labels.map(l => CATEGORY_COLORS[l] || CATEGORY_COLORS['other']);

    return new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: labels.map(l => l.replace('_', ' ')),
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
