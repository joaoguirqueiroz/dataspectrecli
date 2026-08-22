"""Thin audit facade for business services."""

from __future__ import annotations

from typing import Any

from services.log_service import LogService


class AuditService:
    def __init__(self, log_service: LogService) -> None:
        self.log_service = log_service

    def record(
        self,
        action: str,
        actor: str = "system",
        target: str | None = None,
        status: str = "success",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.log_service.audit(
            action=action,
            actor=actor,
            target=target,
            status=status,
            details=details,
        )

