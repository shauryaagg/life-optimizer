"""Tests for the WorkspaceListener module."""

import asyncio

import pytest

from life_optimizer.daemon.workspace_listener import WorkspaceListener


def test_workspace_listener_creation():
    """WorkspaceListener can be created with a queue and loop."""
    loop = asyncio.new_event_loop()
    try:
        queue = asyncio.Queue()
        listener = WorkspaceListener(event_queue=queue, loop=loop)
        assert listener is not None
        assert listener._running is False
    finally:
        loop.close()


def test_workspace_listener_has_start_stop():
    """WorkspaceListener should have start() and stop() methods."""
    loop = asyncio.new_event_loop()
    try:
        queue = asyncio.Queue()
        listener = WorkspaceListener(event_queue=queue, loop=loop)
        assert callable(listener.start)
        assert callable(listener.stop)
    finally:
        loop.close()


def test_workspace_listener_stop_sets_running_false():
    """stop() should set _running to False."""
    loop = asyncio.new_event_loop()
    try:
        queue = asyncio.Queue()
        listener = WorkspaceListener(event_queue=queue, loop=loop)
        listener._running = True
        listener.stop()
        assert listener._running is False
    finally:
        loop.close()


def test_workspace_listener_thread_is_daemon():
    """The background thread should be a daemon thread."""
    loop = asyncio.new_event_loop()
    try:
        queue = asyncio.Queue()
        listener = WorkspaceListener(event_queue=queue, loop=loop)
        assert listener._thread.daemon is True
        assert listener._thread.name == "workspace-listener"
    finally:
        loop.close()
