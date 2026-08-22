from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.application import SentinelScanApplication


@pytest.fixture()
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture()
def runtime_root(tmp_path: Path, repo_root: Path) -> Path:
    root = tmp_path / "sentinelscan"
    for dirname in (
        "app",
        "core",
        "cli",
        "services",
        "modules",
        "plugins",
        "config",
        "templates",
        "assets",
        "docs",
        "examples",
        "scripts",
        "requirements",
    ):
        source = repo_root / dirname
        destination = root / dirname
        if source.exists():
            shutil.copytree(source, destination)
        else:
            destination.mkdir(parents=True)
    for dirname in ("reports", "logs", "cache", "data", "backups"):
        (root / dirname).mkdir(parents=True)
    return root


@pytest.fixture()
def app(runtime_root: Path):
    application = SentinelScanApplication(runtime_root)
    try:
        yield application
    finally:
        application.shutdown()


@pytest.fixture()
def context(app: SentinelScanApplication):
    return app.initialize()


@pytest.fixture()
def asset_file(runtime_root: Path) -> Path:
    path = runtime_root / "examples" / "test_assets.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "assets": [
                    {"name": "gateway", "address": "192.0.2.10", "type": "network"},
                    {"name": "web", "address": "192.0.2.20", "type": "host"},
                ]
            }
        ),
        encoding="utf-8",
    )
    return path
