"""CLI entry point for Life Optimizer."""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys


PLIST_LABEL = "com.lifeoptimizer.daemon"
PLIST_FILENAME = f"{PLIST_LABEL}.plist"


def main():
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

    args = parser.parse_args()

    if args.command is None or args.command == "start":
        cmd_start()
    elif args.command == "setup":
        asyncio.run(cmd_setup())
    elif args.command == "status":
        cmd_status()
    elif args.command == "install":
        cmd_install()
    elif args.command == "uninstall":
        cmd_uninstall()
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "dashboard":
        cmd_dashboard()


def cmd_start():
    """Start the daemon in the foreground."""
    from life_optimizer.config import load_config
    from life_optimizer.daemon.core import Daemon

    config = load_config()
    daemon = Daemon(config)
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        print("\nShutting down...")


async def cmd_setup():
    """Check permissions and show setup guide."""
    from life_optimizer.permissions.checker import PermissionChecker
    from life_optimizer.permissions.guide import print_permission_guide

    checker = PermissionChecker()
    results = await checker.check_all()
    print_permission_guide(results)


def cmd_status():
    """Show daemon status."""
    print("\nLife Optimizer -- Status")
    print("=" * 40)

    try:
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if PLIST_LABEL in result.stdout:
            # Parse the line to get PID and status
            for line in result.stdout.splitlines():
                if PLIST_LABEL in line:
                    parts = line.split()
                    pid = parts[0] if len(parts) >= 1 else "-"
                    status_code = parts[1] if len(parts) >= 2 else "-"
                    if pid == "-":
                        print(f"  Daemon: installed but NOT running")
                    else:
                        print(f"  Daemon: running (PID {pid})")
                    print(f"  Exit status: {status_code}")
                    break
        else:
            print("  Daemon: not installed as launchd agent")
    except Exception as e:
        print(f"  Could not check launchd status: {e}")

    # Check if plist exists
    plist_path = os.path.expanduser(f"~/Library/LaunchAgents/{PLIST_FILENAME}")
    print(f"  Plist: {'exists' if os.path.exists(plist_path) else 'not found'}")
    print()


def cmd_install():
    """Install launchd agent for auto-start."""
    # Find the plist template
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "scripts",
        PLIST_FILENAME,
    )

    if not os.path.exists(template_path):
        print(f"Error: plist template not found at {template_path}")
        sys.exit(1)

    with open(template_path, "r") as f:
        plist_content = f.read()

    # Substitute template variables
    python_path = sys.executable
    working_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    log_dir = os.path.expanduser("~/Library/Logs/LifeOptimizer")
    os.makedirs(log_dir, exist_ok=True)

    plist_content = plist_content.replace("{{PYTHON_PATH}}", python_path)
    plist_content = plist_content.replace("{{WORKING_DIR}}", working_dir)
    plist_content = plist_content.replace("{{LOG_DIR}}", log_dir)

    # Write to LaunchAgents
    launch_agents_dir = os.path.expanduser("~/Library/LaunchAgents")
    os.makedirs(launch_agents_dir, exist_ok=True)
    dest_path = os.path.join(launch_agents_dir, PLIST_FILENAME)

    with open(dest_path, "w") as f:
        f.write(plist_content)

    print(f"Plist installed to {dest_path}")
    print(f"  Python: {python_path}")
    print(f"  Working dir: {working_dir}")
    print(f"  Logs: {log_dir}")

    # Load with launchctl
    result = subprocess.run(
        ["launchctl", "load", dest_path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("  Daemon loaded successfully!")
    else:
        stderr = result.stderr.strip()
        print(f"  Warning: launchctl load returned: {stderr or 'non-zero exit'}")
        print("  You may need to run: launchctl load", dest_path)
    print()


def cmd_uninstall():
    """Remove launchd agent."""
    dest_path = os.path.expanduser(f"~/Library/LaunchAgents/{PLIST_FILENAME}")

    if not os.path.exists(dest_path):
        print("Launchd agent is not installed.")
        return

    # Unload first
    subprocess.run(
        ["launchctl", "unload", dest_path],
        capture_output=True,
        text=True,
    )

    os.remove(dest_path)
    print(f"Removed {dest_path}")
    print("Launchd agent uninstalled.")


def cmd_stop():
    """Stop the launchd daemon."""
    result = subprocess.run(
        ["launchctl", "stop", PLIST_LABEL],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("Daemon stop signal sent.")
    else:
        print(f"Could not stop daemon: {result.stderr.strip() or 'not running?'}")


def cmd_dashboard():
    """Placeholder for web dashboard."""
    print("Dashboard not yet implemented (coming in Phase 5)")
