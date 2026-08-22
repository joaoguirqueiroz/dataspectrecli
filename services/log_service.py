"""Application logging and audit trail service."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone

from core.constants import APPLICATION_LOG_FILE, AUDIT_LOG_FILE
from services.storage import append_jsonl, ensure_dir


class LogService:
    """Configures text logs and structured audit events."""

    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path
        self.log_file = root_path / APPLICATION_LOG_FILE
        self.audit_file = root_path / AUDIT_LOG_FILE
        self.logger = logging.getLogger("dataspectre")
        self.configured = False

    def configure(self, settings: dict[str, Any]) -> None:
        log_settings = settings.get("logging", {})
        ensure_dir(self.log_file.parent)
        level_name = str(log_settings.get("level", "INFO")).upper()
        level = getattr(logging, level_name, logging.INFO)
        self.logger.setLevel(level)
        self.logger.handlers.clear()
        handler = RotatingFileHandler(
            self.log_file,
            maxBytes=int(log_settings.get("max_bytes", 1048576)),
            backupCount=int(log_settings.get("backup_count", 5)),
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.configured = True

    def record_event(
        self,
        component: str,
        level: str,
        message: str,
        category: str = "application",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.configured:
            self.configure({})
        normalized_level = level.upper()
        payload = {
            "id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": normalized_level,
            "component": component,
            "category": category,
            "message": message,
            "details": details or {},
        }
        self.logger.log(getattr(logging, normalized_level, logging.INFO), message)
        append_jsonl(self.audit_file, payload)
        return payload

    def audit(
        self,
        action: str,
        actor: str = "system",
        target: str | None = None,
        status: str = "success",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.record_event(
            component="audit",
            level="INFO" if status == "success" else "WARNING",
            category="audit",
            message=f"{action} [{status}]",
            details={
                "action": action,
                "actor": actor,
                "target": target,
                "status": status,
                "details": details or {},
            },
        )

    def tail_audit(self, limit: int = 20) -> list[str]:
        if not self.audit_file.exists():
            return []
        lines = self.audit_file.read_text(encoding="utf-8").splitlines()
        return lines[-limit:]
