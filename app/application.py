"""High-level DataSpectre application lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.bootstrap import Bootstrapper
from app.context import ApplicationContext
from core.constants import APP_NAME, APP_VERSION


class DataSpectreApplication:
    """Coordinates startup, status reporting, and shutdown."""

    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path
        self.context: ApplicationContext | None = None

    def initialize(self) -> ApplicationContext:
        if self.context is None:
            self.context = Bootstrapper(self.root_path).bootstrap()
        return self.context

    def status(self) -> dict[str, Any]:
        context = self.initialize()
        modules = context.module_manager.list_modules() if context.module_manager else []
        plugins = context.plugin_manager.list_plugins() if context.plugin_manager else []
        projects = context.project_service.list_projects() if context.project_service else []
        health = (
            context.resource_monitor.snapshot(
                {
                    "modules": len(modules),
                    "plugins": len(plugins),
                    "projects": len(projects),
                }
            )
            if context.resource_monitor
            else {}
        )
        return {
            "application": APP_NAME,
            "version": APP_VERSION,
            "root_path": str(context.root_path),
            "modules": len(modules),
            "plugins": len(plugins),
            "projects": len(projects),
            "health": health,
        }

    def session_summary(self) -> dict[str, Any]:
        if self.context is None:
            return {
                "duration_seconds": 0,
                "modules_used": 0,
                "module_ids": [],
                "reports_created": 0,
                "report_ids": [],
                "errors_found": 0,
            }
        context = self.context
        started_at = _parse_datetime(context.started_at)
        duration_seconds = int((datetime.now(timezone.utc) - started_at).total_seconds())
        events = context.event_bus.history() if context.event_bus else []
        module_ids = sorted(
            {
                event.payload.get("module_id")
                for event in events
                if event.name == "module.execution_started" and event.payload.get("module_id")
            }
        )
        errors_found = len(
            [
                event
                for event in events
                if event.name.endswith("_failed") or event.name.endswith(".failed")
            ]
        )
        report_ids: list[str] = []
        if context.report_service:
            for record in context.report_service.list_reports():
                generated_at = _parse_datetime(record.generated_at)
                if generated_at >= started_at:
                    report_ids.append(record.id)
        return {
            "duration_seconds": duration_seconds,
            "modules_used": len(module_ids),
            "module_ids": module_ids,
            "reports_created": len(report_ids),
            "report_ids": report_ids,
            "errors_found": errors_found,
        }

    def shutdown(self) -> None:
        if self.context is None:
            return
        summary = self.session_summary()
        if self.context.module_manager:
            self.context.module_manager.shutdown_all()
        if self.context.plugin_manager:
            self.context.plugin_manager.shutdown_all()
        if self.context.log_service:
            self.context.log_service.record_event(
                component="application",
                level="INFO",
                message=f"{APP_NAME} shutdown completed.",
                details=summary,
            )
        if self.context.history_service:
            self.context.history_service.record_action(
                "application.shutdown",
                result="success",
                details=summary,
            )


# Compatibility alias for extensions/tests built for the original codebase.
SentinelScanApplication = DataSpectreApplication


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
