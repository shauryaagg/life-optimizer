(function() {
    'use strict';

    // Debounce to avoid spamming
    let lastSent = 0;
    const DEBOUNCE_MS = 2000;

    function getPageMetadata() {
        const meta = {};

        // Basic info
        meta.url = window.location.href;
        meta.title = document.title;
        meta.domain = window.location.hostname;

        // Meta description
        const descTag = document.querySelector('meta[name="description"]');
        meta.description = descTag ? descTag.content : null;

        // Content type detection
        meta.contentType = detectContentType();

        // Text length (proxy for reading time)
        const bodyText = document.body ? document.body.innerText : '';
        meta.textLength = bodyText.length;
        meta.estimatedReadingMinutes = Math.ceil(bodyText.split(/\s+/).length / 250);

        // Social media specifics
        if (meta.domain.includes('x.com') || meta.domain.includes('twitter.com')) {
            meta.social = extractTwitterContext();
        } else if (meta.domain.includes('linkedin.com')) {
            meta.social = extractLinkedInContext();
        } else if (meta.domain.includes('reddit.com')) {
            meta.social = extractRedditContext();
        }

        // Form detection (is user composing?)
        meta.isComposing = detectComposing();

        return meta;
    }

    function detectContentType() {
        const url = window.location.href;
        const domain = window.location.hostname;

        // Video platforms
        if (domain.includes('youtube.com') || domain.includes('vimeo.com') || domain.includes('twitch.tv')) {
            return 'video';
        }
        // Social feeds
        if (domain.includes('x.com') || domain.includes('twitter.com') || domain.includes('instagram.com') || domain.includes('facebook.com') || domain.includes('reddit.com')) {
            if (url.includes('/messages') || url.includes('/direct')) return 'social-dm';
            if (url.includes('/status/') || url.includes('/post/')) return 'social-post';
            return 'social-feed';
        }
        // Documentation
        if (domain.includes('docs.') || domain.includes('documentation') || url.includes('/docs/') || url.includes('/api/')) {
            return 'documentation';
        }
        // Code
        if (domain.includes('github.com') || domain.includes('gitlab.com')) {
            if (url.includes('/pull/') || url.includes('/merge_requests/')) return 'code-review';
            if (url.includes('/issues/')) return 'issue-tracker';
            return 'code';
        }
        // Email
        if (domain.includes('mail.google.com') || domain.includes('outlook.') || domain.includes('protonmail.')) {
            return 'email';
        }
        // Chat
        if (domain.includes('slack.com') || domain.includes('discord.com') || domain.includes('teams.microsoft.com')) {
            return 'chat';
        }
        // Article detection
        const article = document.querySelector('article') || document.querySelector('[role="article"]');
        if (article) return 'article';

        return 'webpage';
    }

    function extractTwitterContext() {
        const context = {};
        // Check if in DMs
        if (window.location.pathname.includes('/messages')) {
            context.section = 'dms';
            // Try to get conversation partner from page
            const header = document.querySelector('[data-testid="DM_Conversation_Header"]') ||
                          document.querySelector('h2');
            if (header) context.partner = header.textContent.trim();
        } else if (window.location.pathname === '/home') {
            context.section = 'timeline';
        } else if (window.location.pathname.includes('/search')) {
            context.section = 'search';
        } else if (window.location.pathname.includes('/notifications')) {
            context.section = 'notifications';
        } else {
            context.section = 'profile-or-tweet';
        }
        return context;
    }

    function extractLinkedInContext() {
        const context = {};
        if (window.location.pathname.includes('/messaging')) {
            context.section = 'messaging';
        } else if (window.location.pathname.includes('/feed')) {
            context.section = 'feed';
        } else if (window.location.pathname.includes('/jobs')) {
            context.section = 'jobs';
        } else {
            context.section = 'other';
        }
        return context;
    }

    function extractRedditContext() {
        const context = {};
        const path = window.location.pathname;
        const subredditMatch = path.match(/\/r\/(\w+)/);
        if (subredditMatch) context.subreddit = subredditMatch[1];
        if (path.includes('/comments/')) context.section = 'post';
        else context.section = 'feed';
        return context;
    }

    function detectComposing() {
        const activeEl = document.activeElement;
        if (!activeEl) return false;
        const tag = activeEl.tagName.toLowerCase();
        if (tag === 'textarea') return true;
        if (tag === 'input' && activeEl.type === 'text') return true;
        if (activeEl.contentEditable === 'true') return true;
        // Check for common rich text editors
        if (activeEl.closest('[role="textbox"]')) return true;
        return false;
    }

    function sendMetadata() {
        const now = Date.now();
        if (now - lastSent < DEBOUNCE_MS) return;
        lastSent = now;

        const metadata = getPageMetadata();

        try {
            fetch('http://127.0.0.1:8765/api/chrome-extension/page-context', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(metadata)
            }).catch(() => {
                // Daemon not running, silently fail
            });
        } catch (e) {
            // Silently fail
        }
    }

    // Send on page load
    sendMetadata();

    // Send on visibility change (tab becomes active)
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            sendMetadata();
        }
    });

    // Send on URL change (SPAs)
    let lastUrl = window.location.href;
    const urlObserver = new MutationObserver(function() {
        if (window.location.href !== lastUrl) {
            lastUrl = window.location.href;
            setTimeout(sendMetadata, 500); // Small delay for SPA to update title
        }
    });
    urlObserver.observe(document.body, { childList: true, subtree: true });
})();
