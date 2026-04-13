"""Tests for the JXA bridge."""

import pytest

from life_optimizer.collectors.jxa_bridge import JXABridge


@pytest.fixture
def bridge():
    return JXABridge(max_concurrent=3, timeout=5.0)


@pytest.fixture
def slow_bridge():
    """Bridge with a very short timeout for testing timeout handling."""
    return JXABridge(max_concurrent=3, timeout=1.0)


async def test_run_jxa_returns_string(bridge: JXABridge):
    """Test that run_jxa returns a string for a simple JXA script."""
    result = await bridge.run_jxa('JSON.stringify({a: 1})')
    assert result is not None
    assert '"a":1' in result.replace(" ", "")


async def test_run_applescript_returns_output(bridge: JXABridge):
    """Test that run_applescript returns output for a simple script."""
    result = await bridge.run_applescript('return "hello"')
    assert result is not None
    assert result == "hello"


async def test_run_jxa_timeout(slow_bridge: JXABridge):
    """Test that scripts exceeding the timeout return None."""
    # This JXA script uses a delay to exceed the timeout
    script = """
    (function() {
        var app = Application.currentApplication();
        app.includeStandardAdditions = true;
        delay(10);
        return "done";
    })()
    """
    result = await slow_bridge.run_jxa(script)
    assert result is None


async def test_run_jxa_json_parses_correctly(bridge: JXABridge):
    """Test that run_jxa_json correctly parses JSON output."""
    script = 'JSON.stringify({name: "test", value: 42})'
    result = await bridge.run_jxa_json(script)
    assert result is not None
    assert result["name"] == "test"
    assert result["value"] == 42


async def test_run_jxa_json_returns_none_for_null(bridge: JXABridge):
    """Test that run_jxa_json returns None for null JSON output."""
    result = await bridge.run_jxa_json('JSON.stringify(null)')
    assert result is None


async def test_run_jxa_json_returns_none_for_invalid(bridge: JXABridge):
    """Test that run_jxa_json returns None for invalid JSON."""
    result = await bridge.run_jxa_json('"not json object"')
    # A plain string is not a dict, so should return None
    assert result is None


async def test_run_applescript_invalid_script(bridge: JXABridge):
    """Test that invalid AppleScript returns None."""
    result = await bridge.run_applescript("this is not valid applescript syntax!!!")
    assert result is None
