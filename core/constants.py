"""Application-wide constants."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "DataSpectre CLI"
APP_VERSION = "2.0.1"
APP_AUTHOR = "DataSpectre"
APP_COMMAND = "dataspectre"
MIN_PYTHON_VERSION = (3, 10)

REQUIRED_DIRECTORIES = (
    "app",
    "core",
    "cli",
    "modules",
    "services",
    "config",
    "reports",
    "logs",
    "cache",
    "data",
    "plugins",
    "templates",
    "assets",
    "tests",
    "scripts",
    "docs",
    "examples",
    "backups",
    "requirements",
)

RUNTIME_DIRECTORIES = (
    Path("logs"),
    Path("reports"),
    Path("cache"),
    Path("data"),
    Path("data/config"),
    Path("data/projects"),
    Path("data/history"),
    Path("backups"),
)

DEFAULT_CONFIG_FILE = Path("config/default_config.json")
RUNTIME_CONFIG_FILE = Path("data/config/settings.json")
AUDIT_LOG_FILE = Path("logs/audit.jsonl")
APPLICATION_LOG_FILE = Path("logs/application.log")
