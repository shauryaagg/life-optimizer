async function checkStatus() {
    const el = document.getElementById('status');
    try {
        const response = await fetch('http://127.0.0.1:8765/api/stats');
        if (response.ok) {
            const data = await response.json();
            el.className = 'status connected';
            el.textContent = 'Connected \u2014 ' + (data.event_count || 0) + ' events tracked today';
        } else {
            throw new Error('Not OK');
        }
    } catch (e) {
        el.className = 'status disconnected';
        el.textContent = 'Daemon not running';
    }
}
checkStatus();
