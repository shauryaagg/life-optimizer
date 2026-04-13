"""Entity extraction from activity events."""

from __future__ import annotations

import json
import logging
import re

from life_optimizer.storage.database import Database
from life_optimizer.storage.models import ActivityEvent

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extracts people and project entities from activity events."""

    async def extract_and_store(
        self, events: list[ActivityEvent], db: Database
    ) -> int:
        """Extract entities from events and store them in the database.

        Args:
            events: List of activity events to process.
            db: Database instance.

        Returns:
            Number of new mentions created.
        """
        from life_optimizer.storage.repositories import EntityRepository

        repo = EntityRepository(db)
        mention_count = 0

        for event in events:
            try:
                entities = self._extract_entities(event)
                for entity_type, name, mention_type in entities:
                    entity_id = await repo.upsert_entity(
                        entity_type=entity_type,
                        name=name,
                        timestamp=event.timestamp,
                    )
                    await repo.add_mention(
                        entity_id=entity_id,
                        event_id=event.id,
                        mention_type=mention_type,
                        timestamp=event.timestamp,
                        context=event.window_title,
                    )
                    mention_count += 1
            except Exception as e:
                logger.warning("Entity extraction failed for event %s: %s", event.id, e)
                continue

        return mention_count

    def _extract_entities(
        self, event: ActivityEvent
    ) -> list[tuple[str, str, str]]:
        """Extract entities from a single event.

        Returns:
            List of (entity_type, name, mention_type) tuples.
        """
        entities: list[tuple[str, str, str]] = []

        # Extract people from Slack DM titles: "Person Name - Workspace - Slack"
        if event.app_name == "Slack" and event.window_title:
            person = self._extract_slack_person(event.window_title)
            if person:
                entities.append(("person", person, "slack_dm"))

        # Extract people from iMessage window titles
        if event.app_name in ("Messages", "iMessage") and event.window_title:
            name = event.window_title.strip()
            if name and not name.startswith("+") and len(name) > 1:
                entities.append(("person", name, "imessage"))

        # Extract people from Mail sender in context_json
        if event.app_name == "Mail" and event.context_json:
            sender = self._extract_mail_sender(event.context_json)
            if sender:
                entities.append(("person", sender, "email_sender"))

        # Extract people from Calendar attendees in context_json
        if event.app_name == "Calendar" and event.context_json:
            attendees = self._extract_calendar_attendees(event.context_json)
            for attendee in attendees:
                entities.append(("person", attendee, "calendar_attendee"))

        # Extract projects from VS Code / Cursor titles
        if event.app_name in ("Code", "Cursor", "Visual Studio Code") and event.window_title:
            project = self._extract_vscode_project(event.window_title)
            if project:
                entities.append(("project", project, "editor"))

        # Extract projects from GitHub URLs in Chrome context
        if event.app_name in ("Google Chrome", "Chrome", "Safari") and event.context_json:
            project = self._extract_github_project(event.context_json)
            if project:
                entities.append(("project", project, "github"))

        return entities

    @staticmethod
    def _extract_slack_person(title: str) -> str | None:
        """Extract person name from Slack DM title.

        Format: "Person Name - Workspace - Slack"
        """
        match = re.match(r"^(.+?)\s*-\s*.+\s*-\s*Slack$", title)
        if match:
            name = match.group(1).strip()
            # Filter out channel names (start with #) and generic titles
            if not name.startswith("#") and len(name) > 1:
                return name
        return None

    @staticmethod
    def _extract_vscode_project(title: str) -> str | None:
        """Extract project name from VS Code title.

        Format: "filename — project-name — Visual Studio Code"
        or: "filename — project-name — Cursor"
        """
        # Split on em-dash (\u2014) or spaced-dash (" - ") but not dashes within words
        parts = re.split(r"\s*\u2014\s*|\s+[-\u2015]\s+", title)
        if len(parts) >= 3:
            project = parts[-2].strip()
            if project and len(project) > 1:
                return project
        elif len(parts) == 2:
            # "project-name — Editor"
            project = parts[0].strip()
            if project and len(project) > 1:
                return project
        return None

    @staticmethod
    def _extract_mail_sender(context_json: str) -> str | None:
        """Extract sender from Mail context JSON."""
        try:
            ctx = json.loads(context_json)
            sender = ctx.get("sender") or ctx.get("from")
            if sender and isinstance(sender, str):
                # Strip email address if present: "Name <email@example.com>"
                match = re.match(r"^(.+?)\s*<", sender)
                if match:
                    return match.group(1).strip()
                if "@" not in sender:
                    return sender.strip()
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    @staticmethod
    def _extract_calendar_attendees(context_json: str) -> list[str]:
        """Extract attendee names from Calendar context JSON."""
        try:
            ctx = json.loads(context_json)
            attendees = ctx.get("attendees", [])
            if isinstance(attendees, list):
                names = []
                for att in attendees:
                    if isinstance(att, str):
                        name = att.strip()
                        if name and "@" not in name:
                            names.append(name)
                    elif isinstance(att, dict):
                        name = att.get("name", "").strip()
                        if name:
                            names.append(name)
                return names
        except (json.JSONDecodeError, TypeError):
            pass
        return []

    @staticmethod
    def _extract_github_project(context_json: str) -> str | None:
        """Extract GitHub project from Chrome context JSON URL."""
        try:
            ctx = json.loads(context_json)
            url = ctx.get("url", "")
            match = re.search(r"github\.com/([^/]+/[^/]+)", url)
            if match:
                return match.group(1)
        except (json.JSONDecodeError, TypeError):
            pass
        return None
