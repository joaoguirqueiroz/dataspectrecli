"""General activity history storage."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.storage import append_jsonl, ensure_dir


class HistoryService:
    def __init__(self, history_dir: Path) -> None:
        self.history_dir = ensure_dir(history_dir)
        self.history_file = self.history_dir / "activity.jsonl"

    def append(
        self,
        component: str,
        action: str,
        details: dict[str, Any] | None = None,
        result: str = "success",
        error: str | None = None,
        function_name: str | None = None,
    ) -> None:
        append_jsonl(
            self.history_file,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "component": component,
                "action": action,
                "function": function_name or f"{component}.{action}",
                "result": result,
                "error": error,
                "details": details or {},
            },
        )

    def record_action(
        self,
        function_name: str,
        result: str = "success",
        details: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        component, _, action = function_name.partition(".")
        self.append(
            component=component or "application",
            action=action or function_name,
            details=details,
            result=result,
            error=error,
            function_name=function_name,
        )

    def read_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.history_file.exists():
            return []
        lines = self.history_file.read_text(encoding="utf-8").splitlines()
        records: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records
