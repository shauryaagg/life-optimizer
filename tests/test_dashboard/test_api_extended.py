"""Tests for the extended API endpoints (weekly, monthly, timeline, entity graph)."""

import pytest
from starlette.testclient import TestClient

from life_optimizer.config import Config
from life_optimizer.dashboard.app import create_app


@pytest.fixture
def test_config(tmp_path):
    """Create a test config pointing to a temp database."""
    db_path = str(tmp_path / "test_api_ext.db")
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


def test_weekly_stats_returns_expected_structure(client):
    """Test GET /api/stats/weekly returns expected structure with days array."""
    resp = client.get("/api/stats/weekly")
    assert resp.status_code == 200
    data = resp.json()
    assert "week_start" in data
    assert "days" in data
    assert isinstance(data["days"], list)
    assert len(data["days"]) == 7
    for day in data["days"]:
        assert "date" in day
        assert "categories" in day
        assert "total_minutes" in day
        assert isinstance(day["categories"], dict)


def test_weekly_stats_with_offset(client):
    """Test GET /api/stats/weekly with week_offset=1 returns different week_start."""
    resp0 = client.get("/api/stats/weekly?week_offset=0")
    resp1 = client.get("/api/stats/weekly?week_offset=1")
    assert resp0.status_code == 200
    assert resp1.status_code == 200
    data0 = resp0.json()
    data1 = resp1.json()
    assert data0["week_start"] != data1["week_start"]
    assert len(data1["days"]) == 7


def test_monthly_stats_returns_expected_structure(client):
    """Test GET /api/stats/monthly returns expected structure."""
    resp = client.get("/api/stats/monthly")
    assert resp.status_code == 200
    data = resp.json()
    assert "month" in data
    assert "days" in data
    assert isinstance(data["days"], list)
    # Should have at least one day (today)
    if data["days"]:
        day = data["days"][0]
        assert "date" in day
        assert "total_minutes" in day
        assert "deep_work_minutes" in day


def test_monthly_stats_with_explicit_month(client):
    """Test GET /api/stats/monthly with explicit month."""
    resp = client.get("/api/stats/monthly?month=2025-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["month"] == "2025-01"
    assert isinstance(data["days"], list)


def test_sessions_timeline_returns_sessions_array(client):
    """Test GET /api/sessions/timeline returns sessions array."""
    resp = client.get("/api/sessions/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert "sessions" in data
    assert isinstance(data["sessions"], list)


def test_sessions_timeline_with_days_param(client):
    """Test GET /api/sessions/timeline with days parameter."""
    resp = client.get("/api/sessions/timeline?days=3")
    assert resp.status_code == 200
    data = resp.json()
    assert "sessions" in data
    assert isinstance(data["sessions"], list)


def test_entities_graph_returns_nodes_and_edges(client):
    """Test GET /api/entities/graph returns nodes and edges arrays."""
    resp = client.get("/api/entities/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_entities_graph_with_days_param(client):
    """Test GET /api/entities/graph with days parameter."""
    resp = client.get("/api/entities/graph?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data


def test_all_endpoints_handle_empty_database(client):
    """Test all new endpoints handle empty database gracefully."""
    endpoints = [
        "/api/stats/weekly",
        "/api/stats/weekly?week_offset=1",
        "/api/stats/monthly",
        "/api/stats/monthly?month=2025-06",
        "/api/sessions/timeline",
        "/api/sessions/timeline?days=1",
        "/api/entities/graph",
        "/api/entities/graph?days=7",
    ]
    for endpoint in endpoints:
        resp = client.get(endpoint)
        assert resp.status_code == 200, f"Failed for {endpoint}: {resp.status_code}"
