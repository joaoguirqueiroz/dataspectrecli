"""CLI message helpers."""

from __future__ import annotations

import os
import sys
from typing import TextIO


COLORS = {
    "green": "32",
    "yellow": "33",
    "red": "31",
    "blue": "34",
    "cyan": "36",
    "bold": "1",
}


def colorize(message: str, color: str, stream: TextIO | None = None) -> str:
    """Apply ANSI colors only when the current terminal supports it."""
    target = stream or sys.stdout
    if os.environ.get("NO_COLOR") or not getattr(target, "isatty", lambda: False)():
        return message
    code = COLORS.get(color)
    if not code:
        return message
    return f"\033[{code}m{message}\033[0m"


def success(message: str) -> str:
    return colorize(f"[OK] {message}", "green")


def warning(message: str) -> str:
    return colorize(f"[WARN] {message}", "yellow")


def error(message: str) -> str:
    return colorize(f"[ERROR] {message}", "red", sys.stderr)


def info(message: str) -> str:
    return colorize(f"[INFO] {message}", "cyan")
