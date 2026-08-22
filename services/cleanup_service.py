"""Safe cleanup of disposable runtime files."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from services.audit_service import AuditService
from services.storage import ensure_dir


@dataclass
class CleanupResult:
    dry_run: bool
    scanned_paths: int = 0
    removed_files: int = 0
    removed_dirs: int = 0
    freed_bytes: int = 0
    preserved_paths: tuple[str, ...] = ("reports", "logs", "data", "backups", "config")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CleanupService:
    """Removes only cache and disposable temporary files."""

    def __init__(
        self,
        root_path: Path,
        cache_dir: Path,
        audit: AuditService | None = None,
    ) -> None:
        self.root_path = root_path.resolve()
        self.cache_dir = ensure_dir(cache_dir).resolve()
        self.audit = audit

    def preview(self) -> CleanupResult:
        return self.clean(dry_run=True)

    def clean(self, dry_run: bool = True) -> CleanupResult:
        result = CleanupResult(dry_run=dry_run)
        files = self._candidate_files()
        result.scanned_paths = len(files)

        for path in files:
            result.freed_bytes += path.stat().st_size if path.exists() else 0
            if dry_run:
                continue
            path.unlink(missing_ok=True)
            result.removed_files += 1

        if not dry_run:
            for directory in self._candidate_dirs():
                try:
                    directory.rmdir()
                    result.removed_dirs += 1
                except OSError:
                    continue

        self._audit(result)
        return result

    def _candidate_files(self) -> list[Path]:
        if not self.cache_dir.exists():
            return []
        candidates: list[Path] = []
        for path in sorted(self.cache_dir.rglob("*")):
            if not path.is_file() or path.name == ".gitkeep":
                continue
            resolved = path.resolve()
            if not resolved.is_relative_to(self.cache_dir):
                continue
            candidates.append(path)
        return candidates

    def _candidate_dirs(self) -> list[Path]:
        if not self.cache_dir.exists():
            return []
        directories = [
            path
            for path in sorted(self.cache_dir.rglob("*"), reverse=True)
            if path.is_dir() and path.resolve().is_relative_to(self.cache_dir)
        ]
        return [path for path in directories if path != self.cache_dir]

    def _audit(self, result: CleanupResult) -> None:
        if self.audit:
            self.audit.record(
                action="cleanup.temp",
                target="cache",
                details=result.to_dict(),
            )
