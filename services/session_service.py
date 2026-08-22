"""Project session lifecycle management."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.exceptions import SessionError
from services.audit_service import AuditService
from services.project_service import ProjectService
from services.storage import read_json, write_json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionRecord:
    id: str
    project_id: str
    started_at: str = field(default_factory=utc_now)
    ended_at: str | None = None
    state: str = "active"
    events: list[dict[str, Any]] = field(default_factory=list)
    settings_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SessionService:
    """Creates, updates, and closes project sessions."""

    def __init__(
        self,
        root_path: Path,
        project_service: ProjectService,
        audit: AuditService | None = None,
    ) -> None:
        self.root_path = root_path
        self.project_service = project_service
        self.audit = audit

    def start_session(
        self, project_id: str, settings_snapshot: dict[str, Any] | None = None
    ) -> SessionRecord:
        project = self.project_service.get_project(project_id)
        record = SessionRecord(
            id=f"session-{uuid4().hex[:12]}",
            project_id=project_id,
            settings_snapshot=settings_snapshot or {},
        )
        self._write(project.path, record)
        self.project_service.update_activity(project_id, {"session_started": record.id})
        self._audit("session.started", record.id, {"project_id": project_id})
        return record

    def append_event(
        self, project_id: str, session_id: str, event: dict[str, Any]
    ) -> SessionRecord:
        record = self.get_session(project_id, session_id)
        event_payload = {"timestamp": utc_now(), **event}
        record.events.append(event_payload)
        project = self.project_service.get_project(project_id)
        self._write(project.path, record)
        return record

    def end_session(
        self, project_id: str, session_id: str, state: str = "finished"
    ) -> SessionRecord:
        record = self.get_session(project_id, session_id)
        if record.ended_at:
            return record
        record.ended_at = utc_now()
        record.state = state
        project = self.project_service.get_project(project_id)
        self._write(project.path, record)
        self.project_service.update_activity(project_id, {"session_ended": session_id})
        self._audit("session.ended", session_id, {"project_id": project_id, "state": state})
        return record

    def get_session(self, project_id: str, session_id: str) -> SessionRecord:
        project = self.project_service.get_project(project_id)
        path = self.root_path / project.path / "sessions" / f"{session_id}.json"
        payload = read_json(path, default=None)
        if payload is None:
            raise SessionError(f"Session '{session_id}' was not found.")
        return SessionRecord(**payload)

    def list_sessions(self, project_id: str) -> list[SessionRecord]:
        project = self.project_service.get_project(project_id)
        session_dir = self.root_path / project.path / "sessions"
        records = [SessionRecord(**read_json(path, default={})) for path in session_dir.glob("*.json")]
        return sorted(records, key=lambda record: record.started_at, reverse=True)

    def _write(self, project_path: str, record: SessionRecord) -> None:
        write_json(
            self.root_path / project_path / "sessions" / f"{record.id}.json",
            record.to_dict(),
        )

    def _audit(
        self, action: str, target: str, details: dict[str, Any] | None = None
    ) -> None:
        if self.audit:
            self.audit.record(action=action, target=target, details=details)

