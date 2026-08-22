"""Project catalog and project workspace management."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.exceptions import ProjectError
from core.validators import slugify, validate_non_empty
from services.audit_service import AuditService
from services.storage import ensure_dir, read_json, write_json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    status: str = "active"
    owner: str = "system"
    path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProjectService:
    """Creates, lists, archives, and validates project workspaces."""

    def __init__(self, root_path: Path, workdir: Path, audit: AuditService | None = None) -> None:
        self.root_path = root_path
        self.workdir = workdir
        self.audit = audit
        self.catalog_path = workdir / "catalog.json"
        ensure_dir(workdir)

    def create_project(
        self, name: str, description: str = "", owner: str = "system"
    ) -> Project:
        clean_name = validate_non_empty(name, "project name")
        project_id = f"{slugify(clean_name)}-{uuid4().hex[:8]}"
        project_dir = self.workdir / project_id
        ensure_dir(project_dir)
        for dirname in ("sessions", "reports", "files", "cache", "history"):
            ensure_dir(project_dir / dirname)
        project = Project(
            id=project_id,
            name=clean_name,
            description=description,
            owner=owner,
            path=str(project_dir.relative_to(self.root_path)),
        )
        write_json(project_dir / "project.json", project.to_dict())
        catalog = self._load_catalog()
        catalog[project.id] = project.to_dict()
        write_json(self.catalog_path, catalog)
        self._audit("project.created", project.id, {"name": clean_name})
        return project

    def list_projects(self, include_archived: bool = False) -> list[Project]:
        projects = [Project(**payload) for payload in self._load_catalog().values()]
        if not include_archived:
            projects = [project for project in projects if project.status != "archived"]
        return sorted(projects, key=lambda project: project.updated_at, reverse=True)

    def get_project(self, project_id: str) -> Project:
        catalog = self._load_catalog()
        if project_id not in catalog:
            raise ProjectError(f"Project '{project_id}' was not found.")
        return Project(**catalog[project_id])

    def archive_project(self, project_id: str) -> Project:
        project = self.get_project(project_id)
        project.status = "archived"
        project.updated_at = utc_now()
        self._save_project(project)
        self._audit("project.archived", project.id)
        return project

    def update_activity(self, project_id: str, details: dict[str, Any] | None = None) -> None:
        project = self.get_project(project_id)
        project.updated_at = utc_now()
        self._save_project(project)
        history_path = self.root_path / project.path / "history" / "activity.jsonl"
        from services.storage import append_jsonl

        append_jsonl(
            history_path,
            {"timestamp": project.updated_at, "project_id": project_id, "details": details or {}},
        )

    def stats(self, project_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        project_path = self.root_path / project.path
        project_workspace_reports = [
            path for path in (project_path / "reports").rglob("*") if path.is_file()
        ]
        central_reports = [
            path for path in (self.root_path / "reports" / project_id).rglob("*") if path.is_file()
        ]
        return {
            "project_id": project_id,
            "status": project.status,
            "sessions": len(list((project_path / "sessions").glob("*.json"))),
            "reports": len(project_workspace_reports) + len(central_reports),
            "last_update": project.updated_at,
        }

    def _save_project(self, project: Project) -> None:
        project_path = self.root_path / project.path
        write_json(project_path / "project.json", project.to_dict())
        catalog = self._load_catalog()
        catalog[project.id] = project.to_dict()
        write_json(self.catalog_path, catalog)

    def _load_catalog(self) -> dict[str, dict[str, Any]]:
        return read_json(self.catalog_path, default={}) or {}

    def _audit(
        self, action: str, target: str, details: dict[str, Any] | None = None
    ) -> None:
        if self.audit:
            self.audit.record(action=action, target=target, details=details)
