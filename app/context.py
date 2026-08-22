"""Runtime dependency container."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ApplicationContext:
    root_path: Path
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    settings: dict[str, Any] = field(default_factory=dict)
    event_bus: Any | None = None
    config_service: Any | None = None
    log_service: Any | None = None
    audit_service: Any | None = None
    project_service: Any | None = None
    session_service: Any | None = None
    report_service: Any | None = None
    history_service: Any | None = None
    cleanup_service: Any | None = None
    scanner_service: Any | None = None
    smart_scan_service: Any | None = None
    baseline_service: Any | None = None
    setup_service: Any | None = None
    module_manager: Any | None = None
    plugin_manager: Any | None = None
    permission_manager: Any | None = None
    resource_monitor: Any | None = None
