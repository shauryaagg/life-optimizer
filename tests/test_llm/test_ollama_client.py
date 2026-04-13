"""Tests for the Ollama LLM client."""

import pytest

from life_optimizer.llm.ollama_client import OllamaClient


def test_ollama_client_creation_defaults():
    """Test OllamaClient creation with default parameters."""
    client = OllamaClient()
    assert client._model == "llama3.1:8b"
    assert client._base_url == "http://localhost:11434"


def test_ollama_client_creation_custom():
    """Test OllamaClient creation with custom base_url and model."""
    client = OllamaClient(model="mistral:7b", base_url="http://myhost:9999")
    assert client._model == "mistral:7b"
    assert client._base_url == "http://myhost:9999"


def test_name_property():
    """Test that the name property returns the expected format."""
    client = OllamaClient(model="llama3.1:8b")
    assert client.name == "ollama (llama3.1:8b)"


def test_name_property_custom_model():
    """Test name property with a custom model."""
    client = OllamaClient(model="mistral:7b")
    assert client.name == "ollama (mistral:7b)"


async def test_is_available_returns_false_when_not_running():
    """Test that is_available returns False when Ollama is not running (bad port)."""
    client = OllamaClient(base_url="http://localhost:1")
    result = await client.is_available()
    assert result is False
