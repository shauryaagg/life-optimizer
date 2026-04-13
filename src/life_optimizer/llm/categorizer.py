"""Activity categorization using LLM or rule-based fallback."""

from __future__ import annotations

import json
import logging
from typing import Any

from life_optimizer.llm.base import BaseLLMClient
from life_optimizer.storage.database import Database
from life_optimizer.storage.models import ActivityEvent
from life_optimizer.storage.repositories import EventRepository

logger = logging.getLogger(__name__)

CATEGORIZATION_SYSTEM = """You are an activity categorizer. Given a list of app usage events, assign each a category and subcategory.

Categories (pick one):
- Deep Work: coding, writing, designing, focused creative tasks
- Communication: email, messaging, video calls
- Browsing: web browsing for work (docs, research, dashboards)
- Social Media: Twitter/X, Instagram, Reddit, TikTok, Facebook
- Entertainment: YouTube, Netflix, Spotify, games
- Planning: Calendar, project management (Linear, Notion, Jira)
- Learning: tutorials, documentation, courses
- Personal: banking, shopping, personal email
- Other: anything that doesn't fit

Subcategories are freeform -- be specific (e.g., "coding-python", "slack-dm", "twitter-timeline", "youtube-music").

IMPORTANT: Respond with ONLY a JSON array. No markdown, no explanation. Example:
[{"id": 1, "category": "Deep Work", "subcategory": "coding-python"}, ...]
"""

CATEGORIZATION_PROMPT = """Categorize these {count} activity events:

{events_json}

Respond with ONLY a JSON array of {{"id": <id>, "category": "<category>", "subcategory": "<subcategory>"}} objects."""

# Rule-based categorization patterns
RULES: dict[str, dict[str, list[str]]] = {
    "Deep Work": {
        "apps": [
            "Code",
            "Cursor",
            "Xcode",
            "Terminal",
            "iTerm2",
            "Sublime Text",
        ],
        "urls": [
            "github.com",
            "gitlab.com",
            "stackoverflow.com",
            "docs.python.org",
        ],
    },
    "Communication": {
        "apps": [
            "Slack",
            "Messages",
            "Mail",
            "Zoom",
            "Microsoft Teams",
            "Discord",
        ],
        "urls": ["mail.google.com", "outlook.com"],
    },
    "Social Media": {
        "apps": [],
        "urls": [
            "x.com",
            "twitter.com",
            "instagram.com",
            "facebook.com",
            "reddit.com",
            "tiktok.com",
            "linkedin.com/feed",
        ],
    },
    "Entertainment": {
        "urls": ["youtube.com", "netflix.com", "twitch.tv", "spotify.com"],
        "apps": ["Spotify", "Music", "TV"],
    },
    "Planning": {
        "apps": ["Calendar", "Notion", "Linear"],
        "urls": ["notion.so", "linear.app", "trello.com", "asana.com"],
    },
    "Browsing": {
        "apps": ["Google Chrome", "Safari", "Firefox"],
    },
}

BATCH_SIZE = 50


def categorize_by_rules(
    app_name: str, context_json: str | None = None
) -> tuple[str, str]:
    """Categorize an event using rule-based pattern matching.

    Returns:
        Tuple of (category, subcategory).
    """
    url = ""
    if context_json:
        try:
            ctx = json.loads(context_json)
            url = ctx.get("url", "")
        except (json.JSONDecodeError, TypeError):
            pass

    # First check URL-based rules (more specific)
    if url:
        for category, patterns in RULES.items():
            url_patterns = patterns.get("urls", [])
            for url_pattern in url_patterns:
                if url_pattern in url:
                    subcategory = _derive_subcategory(
                        category, app_name, url
                    )
                    return category, subcategory

    # Then check app-based rules
    for category, patterns in RULES.items():
        app_patterns = patterns.get("apps", [])
        if app_name in app_patterns:
            subcategory = _derive_subcategory(category, app_name, url)
            return category, subcategory

    return "Other", app_name.lower().replace(" ", "-")


def _derive_subcategory(category: str, app_name: str, url: str) -> str:
    """Derive a subcategory string from available information."""
    if url:
        # Extract domain for subcategory
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.hostname or ""
            # Use domain without TLD as subcategory base
            parts = domain.split(".")
            if len(parts) >= 2:
                return parts[-2]
        except Exception:
            pass
    return app_name.lower().replace(" ", "-")


def parse_llm_categorization(response_text: str) -> list[dict[str, Any]]:
    """Parse an LLM categorization response, handling malformed JSON.

    Returns:
        List of dicts with 'id', 'category', 'subcategory' keys.
    """
    text = response_text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Try to find a JSON array in the text
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            result = json.loads(text[start : end + 1])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse LLM categorization response")
    return []


class Categorizer:
    """Categorizes activity events using LLM or rule-based fallback."""

    def __init__(self, client: BaseLLMClient | None, db: Database):
        self._client = client
        self._repo = EventRepository(db)

    async def categorize_uncategorized(self) -> int:
        """Categorize all uncategorized events.

        Returns:
            Number of events categorized.
        """
        events = await self._repo.get_uncategorized_events(limit=500)
        if not events:
            return 0

        total_categorized = 0

        # Process in batches
        for i in range(0, len(events), BATCH_SIZE):
            batch = events[i : i + BATCH_SIZE]
            categorized = await self._categorize_batch(batch)
            total_categorized += categorized

        return total_categorized

    async def _categorize_batch(self, events: list[ActivityEvent]) -> int:
        """Categorize a batch of events."""
        # Try LLM first
        if self._client is not None:
            try:
                return await self._categorize_with_llm(events)
            except Exception as e:
                logger.warning(
                    "LLM categorization failed, falling back to rules: %s", e
                )

        # Fall back to rule-based
        return await self._categorize_with_rules(events)

    async def _categorize_with_llm(self, events: list[ActivityEvent]) -> int:
        """Categorize events using the LLM."""
        # Build the events JSON for the prompt
        events_for_prompt = []
        for event in events:
            entry: dict[str, Any] = {
                "id": event.id,
                "app": event.app_name,
                "title": event.window_title or "",
            }
            if event.context_json:
                try:
                    ctx = json.loads(event.context_json)
                    if "url" in ctx:
                        entry["url"] = ctx["url"]
                except (json.JSONDecodeError, TypeError):
                    pass
            events_for_prompt.append(entry)

        prompt = CATEGORIZATION_PROMPT.format(
            count=len(events),
            events_json=json.dumps(events_for_prompt, indent=2),
        )

        response = await self._client.generate(prompt, system=CATEGORIZATION_SYSTEM)
        results = parse_llm_categorization(response)

        if not results:
            # Fall back to rules if parsing failed
            return await self._categorize_with_rules(events)

        # Build lookup
        result_map = {r["id"]: r for r in results if "id" in r}

        categorized = 0
        for event in events:
            if event.id in result_map:
                r = result_map[event.id]
                category = r.get("category", "Other")
                subcategory = r.get("subcategory", "unknown")
                await self._repo.update_event_category(
                    event.id, category, subcategory
                )
                categorized += 1
            else:
                # LLM missed this event, use rules
                category, subcategory = categorize_by_rules(
                    event.app_name, event.context_json
                )
                await self._repo.update_event_category(
                    event.id, category, subcategory
                )
                categorized += 1

        return categorized

    async def _categorize_with_rules(self, events: list[ActivityEvent]) -> int:
        """Categorize events using rule-based pattern matching."""
        categorized = 0
        for event in events:
            category, subcategory = categorize_by_rules(
                event.app_name, event.context_json
            )
            await self._repo.update_event_category(
                event.id, category, subcategory
            )
            categorized += 1
        return categorized
