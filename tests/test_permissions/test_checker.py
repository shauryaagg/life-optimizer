"""Tests for permission checker."""

import pytest

from life_optimizer.permissions.checker import PermissionChecker


@pytest.fixture
def checker():
    return PermissionChecker()


async def test_check_all_returns_dict(checker):
    """check_all should return a dict with the expected keys."""
    results = await checker.check_all()
    assert isinstance(results, dict)
    expected_keys = {"accessibility", "screen_recording", "automation"}
    assert set(results.keys()) == expected_keys


async def test_check_all_values_are_bool(checker):
    """All values in the results dict should be booleans."""
    results = await checker.check_all()
    for key, value in results.items():
        assert isinstance(value, bool), f"{key} should be bool, got {type(value)}"


async def test_check_accessibility_returns_bool(checker):
    """_check_accessibility should return a bool."""
    result = await checker._check_accessibility()
    assert isinstance(result, bool)


async def test_check_screen_recording_returns_bool(checker):
    """_check_screen_recording should return a bool."""
    result = await checker._check_screen_recording()
    assert isinstance(result, bool)


async def test_check_automation_returns_bool(checker):
    """_check_automation should return a bool."""
    result = await checker._check_automation()
    assert isinstance(result, bool)
