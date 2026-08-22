"""Public module interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.context import ApplicationContext


class ModuleState(str, Enum):
    NOT_LOADED = "not_loaded"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    ERROR = "error"
    FINALIZED = "finalized"


@dataclass(frozen=True)
class ModuleMetadata:
    id: str
    name: str
    version: str
    author: str
    description: str
    category: str
    dependencies: list[str] = field(default_factory=list)
    min_app_version: str = "1.0.0"


@dataclass
class ModuleExecutionContext:
    application: "ApplicationContext"
    parameters: dict[str, Any] = field(default_factory=dict)
    project_id: str | None = None
    session_id: str | None = None
    output_dir: Path | None = None


@dataclass
class ModuleResult:
    module_id: str
    success: bool
    status: str
    data: dict[str, Any] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    finished_at: str | None = None

    def finish(self) -> "ModuleResult":
        self.finished_at = datetime.now(timezone.utc).isoformat()
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "success": self.success,
            "status": self.status,
            "data": self.data,
            "messages": self.messages,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class BaseModule:
    """Base class that every module must implement."""

    metadata: ModuleMetadata

    def initialize(self, context: "ApplicationContext") -> None:
        return None

    def validate(self, parameters: dict[str, Any]) -> None:
        return None

    def execute(self, context: ModuleExecutionContext) -> ModuleResult:
        raise NotImplementedError

    def shutdown(self) -> None:
        return None

    def result(
        self,
        success: bool,
        status: str,
        data: dict[str, Any] | None = None,
        messages: list[str] | None = None,
    ) -> ModuleResult:
        return ModuleResult(
            module_id=self.metadata.id,
            success=success,
            status=status,
            data=data or {},
            messages=messages or [],
        ).finish()

