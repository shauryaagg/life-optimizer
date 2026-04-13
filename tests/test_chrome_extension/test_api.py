"""Tests for the Chrome extension API endpoints."""

import json

import pytest
from starlette.testclient import TestClient

from life_optimizer.config import Config
from life_optimizer.dashboard.app import create_app


@pytest.fixture
def test_config(tmp_path):
    """Create a test config pointing to a temp database."""
    db_path = str(tmp_path / "test.db")
    screenshots_dir = tmp_path / "screenshots"
    screenshots_dir.mkdir()
    config = Config()
    config.storage.db_path = db_path
    return config


@pytest.fixture
def client(test_config):
    """Create a test client."""
    app = create_app(test_config)
    with TestClient(app) as c:
        yield c


def test_page_context_returns_200(client):
    """Test POST /api/chrome-extension/page-context with valid data returns 200."""
    payload = {
        "url": "https://example.com",
        "title": "Example Page",
        "domain": "example.com",
        "description": "A test page",
        "contentType": "webpage",
        "textLength": 1500,
        "estimatedReadingMinutes": 6,
        "isComposing": False,
    }
    resp = client.post("/api/chrome-extension/page-context", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_tab_switch_returns_200(client):
    """Test POST /api/chrome-extension/tab-switch with valid data returns 200."""
    payload = {
        "url": "https://example.com/new-page",
        "title": "New Page",
        "timestamp": "2025-06-01T10:00:00",
    }
    resp = client.post("/api/chrome-extension/tab-switch", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_page_context_stored_in_database(client):
    """Test that page-context events are actually stored in the database."""
    payload = {
        "url": "https://github.com/test",
        "title": "GitHub Test",
        "domain": "github.com",
        "contentType": "code",
    }
    client.post("/api/chrome-extension/page-context", json=payload)

    # Retrieve events via the API
    resp = client.get("/api/events?limit=10")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1

    # Find the chrome extension event
    chrome_events = [e for e in events if e["event_type"] == "chrome_extension"]
    assert len(chrome_events) >= 1
    event = chrome_events[0]
    assert event["app_name"] == "Google Chrome"
    assert event["window_title"] == "GitHub Test"

    # Verify context_json contains the posted data
    context = json.loads(event["context_json"])
    assert context["url"] == "https://github.com/test"
    assert context["contentType"] == "code"


def test_tab_switch_stored_in_database(client):
    """Test that tab-switch events are actually stored in the database."""
    payload = {
        "url": "https://docs.python.org",
        "title": "Python Docs",
        "timestamp": "2025-06-01T12:00:00",
    }
    client.post("/api/chrome-extension/tab-switch", json=payload)

    resp = client.get("/api/events?limit=10")
    assert resp.status_code == 200
    events = resp.json()

    tab_events = [e for e in events if e["event_type"] == "chrome_extension_tab_switch"]
    assert len(tab_events) >= 1
    event = tab_events[0]
    assert event["app_name"] == "Google Chrome"
    assert event["window_title"] == "Python Docs"


def test_page_context_with_missing_fields(client):
    """Test that page-context handles missing optional fields gracefully."""
    payload = {}
    resp = client.post("/api/chrome-extension/page-context", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_tab_switch_with_missing_fields(client):
    """Test that tab-switch handles missing optional fields gracefully."""
    payload = {"url": "https://example.com"}
    resp = client.post("/api/chrome-extension/tab-switch", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_page_context_with_social_data(client):
    """Test page-context with social media metadata."""
    payload = {
        "url": "https://x.com/home",
        "title": "Home / X",
        "domain": "x.com",
        "contentType": "social-feed",
        "social": {"section": "timeline"},
        "isComposing": False,
    }
    resp = client.post("/api/chrome-extension/page-context", json=payload)
    assert resp.status_code == 200

    # Verify stored data
    resp = client.get("/api/events?limit=10")
    events = resp.json()
    chrome_events = [e for e in events if e["event_type"] == "chrome_extension"]
    assert len(chrome_events) >= 1
    context = json.loads(chrome_events[0]["context_json"])
    assert context["social"]["section"] == "timeline"
