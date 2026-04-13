// Listen for tab activation changes
chrome.tabs.onActivated.addListener(async (activeInfo) => {
    try {
        const tab = await chrome.tabs.get(activeInfo.tabId);
        if (tab.url) {
            fetch('http://127.0.0.1:8765/api/chrome-extension/tab-switch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: tab.url,
                    title: tab.title,
                    timestamp: new Date().toISOString()
                })
            }).catch(() => {});
        }
    } catch (e) {}
});

// Listen for tab URL updates (navigation)
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.active) {
        fetch('http://127.0.0.1:8765/api/chrome-extension/tab-switch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: tab.url,
                title: tab.title,
                timestamp: new Date().toISOString()
            })
        }).catch(() => {});
    }
});
