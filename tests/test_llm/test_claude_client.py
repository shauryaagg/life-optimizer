"""Tests for the Claude LLM client."""

import pytest

from life_optimizer.llm.claude_client import ClaudeClient


def test_claude_client_creation_with_api_key():
    """Test that ClaudeClient can be created with an explicit API key."""
    client = ClaudeClient(api_key="test-key-123")
    assert client._api_key == "test-key-123"
    assert client._model == "claude-sonnet-4-20250514"


def test_claude_client_creation_with_custom_model():
    """Test that ClaudeClient accepts a custom model."""
    client = ClaudeClient(model="claude-3-haiku-20240307", api_key="key")
    assert client._model == "claude-3-haiku-20240307"


def test_claude_client_creation_without_api_key():
    """Test that ClaudeClient can be created without an API key."""
    client = ClaudeClient(api_key="")
    assert client._api_key == ""


async def test_is_available_returns_false_with_empty_api_key():
    """Test that is_available returns False when no API key is set."""
    client = ClaudeClient(api_key="")
    assert await client.is_available() is False


def test_name_property():
    """Test that the name property returns the expected format."""
    client = ClaudeClient(model="claude-sonnet-4-20250514", api_key="key")
    assert client.name == "claude (claude-sonnet-4-20250514)"


def test_name_property_custom_model():
    """Test name property with a custom model."""
    client = ClaudeClient(model="claude-3-haiku-20240307", api_key="key")
    assert client.name == "claude (claude-3-haiku-20240307)"


async def test_is_available_returns_true_with_api_key():
    """Test that is_available returns True when an API key is set (client creation succeeds)."""
    client = ClaudeClient(api_key="test-key-not-real")
    # This should return True since it just checks if the client can be created
    # (it doesn't actually make an API call)
    result = await client.is_available()
    assert result is True
