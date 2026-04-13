"""Tests for the dashboard application."""

import pytest
from pathlib import Path

from starlette.testclient import TestClient

from life_optimizer.config import Config
from life_optimizer.dashboard.app import create_app
from life_optimizer.storage.database import Database


@pytest.fixture
def test_config(tmp_path):
    """Create a test config pointing to a temp database."""
    db_path = str(tmp_path / "test.db")
    # Create screenshots dir so the app can mount it
    screenshots_dir = tmp_path / "screenshots"
    screenshots_dir.mkdir()
    config = Config()
    config.storage.db_path = db_path
    return config


@pytest.fixture
def app(test_config):
    """Create a test FastAPI app."""
    return create_app(test_config)


@pytest.fixture
def client(app):
    """Create a test client."""
    with TestClient(app) as c:
        yield c


def test_get_root_returns_200(client):
    """Test GET / returns 200."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_get_timeline_returns_200(client):
    """Test GET /timeline returns 200."""
    resp = client.get("/timeline")
    assert resp.status_code == 200


def test_get_reports_returns_200(client):
    """Test GET /reports returns 200."""
    resp = client.get("/reports")
    assert resp.status_code == 200


def test_get_screenshots_returns_200(client):
    """Test GET /screenshots returns 200."""
    resp = client.get("/screenshots")
    assert resp.status_code == 200


def test_get_settings_returns_200(client):
    """Test GET /settings returns 200."""
    resp = client.get("/settings")
    assert resp.status_code == 200


def test_get_api_events_returns_json(client):
    """Test GET /api/events returns JSON array."""
    resp = client.get("/api/events")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_get_api_stats_returns_json(client):
    """Test GET /api/stats returns JSON with expected keys."""
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "event_count" in data
    assert "category_breakdown" in data
    assert "top_apps" in data


def test_get_api_screenshots_returns_json(client):
    """Test GET /api/screenshots returns JSON array."""
    resp = client.get("/api/screenshots")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_app_creates_with_test_config(test_config):
    """Test the app creates OK with a test config pointing to a temp database."""
    app = create_app(test_config)
    assert app is not None
    assert app.state.config is test_config
