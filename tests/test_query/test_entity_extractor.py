"""Tests for entity extraction."""

import json
import pytest

from life_optimizer.query.entity_extractor import EntityExtractor
from life_optimizer.storage.database import Database
from life_optimizer.storage.models import ActivityEvent
from life_optimizer.storage.repositories import EntityRepository


@pytest.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_entity.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


@pytest.fixture
def extractor():
    return EntityExtractor()


def _make_event(
    id: int = 1,
    app_name: str = "TestApp",
    window_title: str | None = None,
    context_json: str | None = None,
    timestamp: str = "2025-01-15T10:00:00",
) -> ActivityEvent:
    return ActivityEvent(
        id=id,
        timestamp=timestamp,
        app_name=app_name,
        event_type="poll",
        window_title=window_title,
        context_json=context_json,
    )


async def test_extract_person_from_slack_dm(extractor, db):
    """Test extracting person from Slack DM title."""
    event = _make_event(
        app_name="Slack",
        window_title="John Smith - Acme Corp - Slack",
    )

    count = await extractor.extract_and_store([event], db)
    assert count == 1

    repo = EntityRepository(db)
    entities = await repo.get_entities(entity_type="person")
    assert len(entities) == 1
    assert entities[0].name == "John Smith"
    assert entities[0].entity_type == "person"


async def test_extract_project_from_vscode_title(extractor, db):
    """Test extracting project from VS Code title."""
    event = _make_event(
        app_name="Code",
        window_title="main.py \u2014 my-project \u2014 Visual Studio Code",
    )

    count = await extractor.extract_and_store([event], db)
    assert count == 1

    repo = EntityRepository(db)
    entities = await repo.get_entities(entity_type="project")
    assert len(entities) == 1
    assert entities[0].name == "my-project"


async def test_upsert_updates_last_seen_and_count(extractor, db):
    """Test that re-extracting the same entity updates it."""
    event1 = _make_event(
        id=1,
        app_name="Slack",
        window_title="John Smith - Acme Corp - Slack",
        timestamp="2025-01-15T10:00:00",
    )
    event2 = _make_event(
        id=2,
        app_name="Slack",
        window_title="John Smith - Acme Corp - Slack",
        timestamp="2025-01-15T11:00:00",
    )

    await extractor.extract_and_store([event1], db)
    await extractor.extract_and_store([event2], db)

    repo = EntityRepository(db)
    entities = await repo.get_entities(entity_type="person")
    assert len(entities) == 1
    assert entities[0].interaction_count == 2
    assert entities[0].last_seen == "2025-01-15T11:00:00"


async def test_no_extraction_from_generic_window_titles(extractor, db):
    """Test that generic window titles don't produce entities."""
    event = _make_event(
        app_name="Finder",
        window_title="Documents",
    )

    count = await extractor.extract_and_store([event], db)
    assert count == 0


async def test_extract_person_from_imessage(extractor, db):
    """Test extracting person from iMessage window title."""
    event = _make_event(
        app_name="Messages",
        window_title="Jane Doe",
    )

    count = await extractor.extract_and_store([event], db)
    assert count == 1

    repo = EntityRepository(db)
    entities = await repo.get_entities(entity_type="person")
    assert len(entities) == 1
    assert entities[0].name == "Jane Doe"


async def test_extract_github_project(extractor, db):
    """Test extracting GitHub project from Chrome URL."""
    event = _make_event(
        app_name="Google Chrome",
        window_title="Pull Requests",
        context_json=json.dumps({"url": "https://github.com/user/repo/pulls"}),
    )

    count = await extractor.extract_and_store([event], db)
    assert count == 1

    repo = EntityRepository(db)
    entities = await repo.get_entities(entity_type="project")
    assert len(entities) == 1
    assert entities[0].name == "user/repo"


async def test_extract_mail_sender(extractor, db):
    """Test extracting sender from Mail context."""
    event = _make_event(
        app_name="Mail",
        context_json=json.dumps({"sender": "Bob Jones <bob@example.com>"}),
    )

    count = await extractor.extract_and_store([event], db)
    assert count == 1

    repo = EntityRepository(db)
    entities = await repo.get_entities(entity_type="person")
    assert len(entities) == 1
    assert entities[0].name == "Bob Jones"


async def test_extract_calendar_attendees(extractor, db):
    """Test extracting attendees from Calendar context."""
    event = _make_event(
        app_name="Calendar",
        context_json=json.dumps({
            "attendees": [
                {"name": "Alice"},
                {"name": "Bob"},
            ]
        }),
    )

    count = await extractor.extract_and_store([event], db)
    assert count == 2

    repo = EntityRepository(db)
    entities = await repo.get_entities(entity_type="person")
    assert len(entities) == 2
    names = {e.name for e in entities}
    assert names == {"Alice", "Bob"}


async def test_slack_channel_not_extracted(extractor, db):
    """Test that Slack channel names (with #) are not extracted as people."""
    event = _make_event(
        app_name="Slack",
        window_title="#general - Acme Corp - Slack",
    )

    count = await extractor.extract_and_store([event], db)
    assert count == 0


async def test_extraction_robust_to_bad_json(extractor, db):
    """Test that bad context_json doesn't crash extraction."""
    event = _make_event(
        app_name="Mail",
        context_json="not valid json{{{",
    )

    # Should not raise
    count = await extractor.extract_and_store([event], db)
    assert count == 0


async def test_extract_project_from_cursor(extractor, db):
    """Test extracting project from Cursor editor title."""
    event = _make_event(
        app_name="Cursor",
        window_title="app.py \u2014 backend \u2014 Cursor",
    )

    count = await extractor.extract_and_store([event], db)
    assert count == 1

    repo = EntityRepository(db)
    entities = await repo.get_entities(entity_type="project")
    assert len(entities) == 1
    assert entities[0].name == "backend"
