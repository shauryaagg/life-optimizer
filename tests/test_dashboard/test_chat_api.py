"""Tests for the chat API routes."""

import pytest
from starlette.testclient import TestClient

from life_optimizer.config import Config
from life_optimizer.dashboard.app import create_app


@pytest.fixture
def test_config(tmp_path):
    """Create a test config pointing to a temp database."""
    db_path = str(tmp_path / "test_chat.db")
    screenshots_dir = tmp_path / "screenshots"
    screenshots_dir.mkdir()
    config = Config()
    config.storage.db_path = db_path
    config.llm.provider = "none"
    return config


@pytest.fixture
def client(test_config):
    """Create a test client."""
    app = create_app(test_config)
    with TestClient(app) as c:
        yield c


def test_post_chat_returns_200(client):
    """Test POST /api/chat returns 200 with expected structure."""
    resp = client.post(
        "/api/chat",
        json={"question": "how many events?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "query_type" in data
    assert "session_id" in data
    assert "follow_up_suggestions" in data
    assert isinstance(data["follow_up_suggestions"], list)


def test_post_chat_with_session_id(client):
    """Test POST /api/chat with a session_id."""
    resp = client.post(
        "/api/chat",
        json={"question": "hello", "session_id": "test-session-123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "test-session-123"


def test_post_chat_with_history(client):
    """Test POST /api/chat with conversation history."""
    resp = client.post(
        "/api/chat",
        json={
            "question": "tell me more",
            "history": [
                {"role": "user", "content": "what did I do?"},
                {"role": "assistant", "content": "You had 5 events."},
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data


def test_get_status_returns_expected_fields(client):
    """Test GET /api/status returns expected fields."""
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "daemon_running" in data
    assert "tracking_status" in data
    assert "event_count" in data
    assert "last_event_time" in data
    assert isinstance(data["event_count"], int)


def test_get_entities_returns_list(client):
    """Test GET /api/entities returns a list."""
    resp = client.get("/api/entities")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_get_entities_with_type_filter(client):
    """Test GET /api/entities with type filter."""
    resp = client.get("/api/entities?type=person")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_get_chat_history(client):
    """Test GET /api/chat/history returns list."""
    # First, create a chat to have history
    client.post(
        "/api/chat",
        json={"question": "hello", "session_id": "history-test"},
    )

    resp = client.get("/api/chat/history?session_id=history-test")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # user message + assistant response
    assert data[0]["role"] == "user"
    assert data[1]["role"] == "assistant"
