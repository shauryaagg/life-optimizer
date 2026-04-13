"""Human-friendly permission status display and setup guide."""

from __future__ import annotations

PERMISSION_INSTRUCTIONS = {
    "accessibility": (
        "-> System Settings > Privacy & Security > Accessibility\n"
        "-> Add your terminal app (Terminal.app, iTerm2, etc.)"
    ),
    "screen_recording": (
        "-> System Settings > Privacy & Security > Screen Recording\n"
        "-> Add your terminal app"
    ),
    "automation": (
        "-> Will be prompted automatically on first use\n"
        "-> Or: System Settings > Privacy & Security > Automation"
    ),
}


def print_permission_guide(results: dict[str, bool]):
    """Print a human-friendly permission status and setup guide."""
    print("\nLife Optimizer -- Permission Check")
    print("=" * 40)

    for name, granted in results.items():
        status = "[ok]" if granted else "[!!]"
        label = name.replace("_", " ").title()
        print(
            f"  {status} {label}: {'granted' if granted else 'NOT GRANTED'}"
        )

        if not granted:
            instructions = PERMISSION_INSTRUCTIONS.get(name, "")
            if instructions:
                for line in instructions.split("\n"):
                    print(f"    {line}")

    all_granted = all(results.values())
    if all_granted:
        print("\n  All permissions granted! Ready to run.")
    else:
        print("\n  Some permissions missing. Grant them in System Settings")
        print("  -> Privacy & Security, then restart Life Optimizer.")
    print()
