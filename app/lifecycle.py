"""Lifecycle utility helpers."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.application import DataSpectreApplication
from app.context import ApplicationContext


@contextmanager
def managed_application(root_path: Path) -> Iterator[ApplicationContext]:
    application = DataSpectreApplication(root_path)
    try:
        yield application.initialize()
    finally:
        application.shutdown()

