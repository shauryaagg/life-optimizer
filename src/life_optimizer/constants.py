"""Constants used throughout the application."""

# Event types
APP_ACTIVATE = "app_activate"
POLL = "poll"
TAB_CHANGE = "tab_change"

# Default category mappings (for future use)
CATEGORY_MAPPINGS: dict[str, str] = {
    "Google Chrome": "browsing",
    "Safari": "browsing",
    "Firefox": "browsing",
    "Code": "development",
    "Terminal": "development",
    "iTerm2": "development",
    "Slack": "communication",
    "Messages": "communication",
    "Mail": "communication",
    "Finder": "system",
    "System Preferences": "system",
    "System Settings": "system",
}
