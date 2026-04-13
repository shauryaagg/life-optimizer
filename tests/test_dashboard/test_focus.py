"""Tests for the focus timeline route."""

import pytest
from starlette.testclient import TestClient

from life_optimizer.config import Config
from life_optimizer.dashboard.app import create_app


@pytest.fixture
def test_config(tmp_path):
    """Create a test config pointing to a temp database."""
    db_path = str(tmp_path / "test_focus.db")
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


def test_get_focus_returns_200(client):
    """Test GET /focus returns 200."""
    resp = client.get("/focus")
    assert resp.status_code == 200


def test_focus_page_contains_timeline_elements(client):
    """Test focus page contains timeline UI elements."""
    resp = client.get("/focus")
    assert resp.status_code == 200
    html = resp.text
    assert "Focus Timeline" in html
    assert 'id="focus-timeline"' in html
    assert 'id="days-select"' in html
