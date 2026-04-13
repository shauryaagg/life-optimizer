"""Tests for the chat page route."""

import pytest
from starlette.testclient import TestClient

from life_optimizer.config import Config
from life_optimizer.dashboard.app import create_app


@pytest.fixture
def test_config(tmp_path):
    """Create a test config pointing to a temp database."""
    db_path = str(tmp_path / "test_chat_page.db")
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


def test_get_chat_returns_200(client):
    """Test GET /chat returns 200."""
    resp = client.get("/chat")
    assert resp.status_code == 200


def test_chat_page_contains_input_elements(client):
    """Test chat page contains chat input and suggestion chips."""
    resp = client.get("/chat")
    assert resp.status_code == 200
    html = resp.text
    assert 'id="search-input"' in html
    assert "How much deep work today?" in html
    assert "What was I doing at 3pm?" in html
    assert "suggestion-chip" in html
    assert "New Chat" in html
