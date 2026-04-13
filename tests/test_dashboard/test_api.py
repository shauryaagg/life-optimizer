"""Tests for the dashboard API routes."""

import pytest
from pathlib import Path

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


def test_api_events_with_date_filter(client):
    """Test /api/events with date filter returns empty list for unknown date."""
    resp = client.get("/api/events?date=2000-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_api_events_with_app_filter(client):
    """Test /api/events with app filter returns empty list for unknown app."""
    resp = client.get("/api/events?app=NonExistentApp")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_api_summaries_returns_empty_list(client):
    """Test /api/summaries returns empty list when no summaries exist."""
    resp = client.get("/api/summaries")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_api_stats_returns_expected_keys(client):
    """Test /api/stats returns category_breakdown and top_apps."""
    resp = client.get("/api/stats?date=2025-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert "category_breakdown" in data
    assert "top_apps" in data
    assert isinstance(data["category_breakdown"], dict)
    assert isinstance(data["top_apps"], list)


def test_api_sessions_returns_json(client):
    """Test /api/sessions returns JSON array."""
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_api_screenshots_returns_json(client):
    """Test /api/screenshots returns JSON array."""
    resp = client.get("/api/screenshots")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
