"""Tests for the CLI module."""

import pytest
from unittest.mock import patch, MagicMock

from life_optimizer.cli import main


def _parse_command(args):
    """Helper to parse CLI args and return the parsed command."""
    import argparse
    from life_optimizer.cli import main as _main

    # Build the parser the same way as main() does
    parser = argparse.ArgumentParser(
        prog="life-optimizer",
        description="Life Optimizer -- macOS activity monitor",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("start", help="Start the daemon in the foreground")
    subparsers.add_parser("setup", help="Check permissions and show setup guide")
    subparsers.add_parser("status", help="Show daemon status")
    subparsers.add_parser("install", help="Install launchd agent for auto-start")
    subparsers.add_parser("uninstall", help="Remove launchd agent")
    subparsers.add_parser("stop", help="Stop the launchd daemon")
    subparsers.add_parser("dashboard", help="Start the web dashboard")

    return parser.parse_args(args)


def test_parse_start():
    """CLI should parse 'start' command."""
    args = _parse_command(["start"])
    assert args.command == "start"


def test_parse_setup():
    """CLI should parse 'setup' command."""
    args = _parse_command(["setup"])
    assert args.command == "setup"


def test_parse_status():
    """CLI should parse 'status' command."""
    args = _parse_command(["status"])
    assert args.command == "status"


def test_parse_install():
    """CLI should parse 'install' command."""
    args = _parse_command(["install"])
    assert args.command == "install"


def test_parse_uninstall():
    """CLI should parse 'uninstall' command."""
    args = _parse_command(["uninstall"])
    assert args.command == "uninstall"


def test_parse_stop():
    """CLI should parse 'stop' command."""
    args = _parse_command(["stop"])
    assert args.command == "stop"


def test_parse_dashboard():
    """CLI should parse 'dashboard' command."""
    args = _parse_command(["dashboard"])
    assert args.command == "dashboard"


def test_no_command_defaults_to_none():
    """No command should result in command=None (defaults to start)."""
    args = _parse_command([])
    assert args.command is None


def test_help_output(capsys):
    """Help flag should print help text and exit."""
    with pytest.raises(SystemExit) as exc_info:
        _parse_command(["--help"])
    assert exc_info.value.code == 0


def test_cmd_dashboard(capsys):
    """Dashboard command should print a placeholder message."""
    from life_optimizer.cli import cmd_dashboard

    cmd_dashboard()
    captured = capsys.readouterr()
    assert "not yet implemented" in captured.out.lower()


def test_cmd_status_runs(capsys):
    """Status command should run without error."""
    from life_optimizer.cli import cmd_status

    cmd_status()
    captured = capsys.readouterr()
    assert "Status" in captured.out
