"""Defensive network exposure baselines."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.exceptions import ValidationError
from services.storage import ensure_dir, read_json, write_json


@dataclass
class BaselineRecord:
    name: str
    created_at: str
    source: str
    snapshot: dict[str, Any]
    path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaselineService:
    """Stores and compares known-good exposure snapshots."""

    def __init__(self, root_path: Path, baseline_dir: Path | None = None) -> None:
        self.root_path = root_path.resolve()
        self.baseline_dir = ensure_dir(baseline_dir or self.root_path / "data" / "baselines")

    def create_baseline(self, name: str, scan_data: dict[str, Any], source: str = "manual") -> BaselineRecord:
        safe_name = self._safe_name(name)
        snapshot = self.snapshot(scan_data)
        path = self._path(safe_name)
        record = BaselineRecord(
            name=safe_name,
            created_at=datetime.now(timezone.utc).isoformat(),
            source=source,
            snapshot=snapshot,
            path=str(path.relative_to(self.root_path)),
        )
        write_json(path, record.to_dict())
        return record

    def load_baseline(self, name: str) -> BaselineRecord:
        path = self._path(self._safe_name(name))
        payload = read_json(path, default=None)
        if not payload:
            raise ValidationError(f"Baseline '{name}' was not found.")
        return BaselineRecord(**payload)

    def compare(self, name: str, scan_data: dict[str, Any]) -> dict[str, Any]:
        baseline = self.load_baseline(name)
        current = self.snapshot(scan_data)
        before_services = set(baseline.snapshot["services"])
        after_services = set(current["services"])
        before_findings = set(baseline.snapshot["findings"])
        after_findings = set(current["findings"])
        version_changes = self._version_changes(
            baseline.snapshot.get("versions", {}),
            current.get("versions", {}),
        )
        result = {
            "baseline": baseline.to_dict(),
            "current": current,
            "new_services": sorted(after_services - before_services),
            "removed_services": sorted(before_services - after_services),
            "new_findings": sorted(after_findings - before_findings),
            "resolved_findings": sorted(before_findings - after_findings),
            "persistent_findings": sorted(before_findings & after_findings),
            "version_changes": version_changes,
        }
        result["summary"] = {
            "new_services": len(result["new_services"]),
            "removed_services": len(result["removed_services"]),
            "new_findings": len(result["new_findings"]),
            "resolved_findings": len(result["resolved_findings"]),
            "persistent_findings": len(result["persistent_findings"]),
            "version_changes": len(version_changes),
            "status": "changed" if any(
                result[key]
                for key in ("new_services", "removed_services", "new_findings", "resolved_findings", "version_changes")
            ) else "unchanged",
        }
        return result

    def snapshot(self, scan_data: dict[str, Any]) -> dict[str, Any]:
        if isinstance(scan_data.get("results"), dict):
            scan_data = scan_data["results"].get("data", scan_data["results"])
        data = scan_data.get("data", scan_data)
        if "correlation" in data:
            data = data["correlation"]
        hosts = data.get("hosts") or data.get("nmap", {}).get("hosts") or []
        findings = data.get("findings") or data.get("correlated_findings") or []
        services: list[str] = []
        versions: dict[str, str] = {}
        for host in hosts:
            host_id = str(host.get("host") or host.get("ip") or "")
            for port in host.get("ports", []):
                if port.get("state") != "open":
                    continue
                key = f"{host_id}:{port.get('port')}/{port.get('protocol', 'tcp')}/{port.get('service', 'unknown')}"
                services.append(key)
                versions[key] = str(port.get("version") or "")
        finding_keys = [
            f"{finding.get('target')}|{finding.get('template')}|{finding.get('severity')}"
            for finding in findings
        ]
        return {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "services": sorted(set(services)),
            "versions": versions,
            "findings": sorted(set(finding_keys)),
        }

    def _version_changes(self, before: dict[str, str], after: dict[str, str]) -> list[dict[str, str]]:
        changes: list[dict[str, str]] = []
        for key in sorted(set(before) & set(after)):
            if before.get(key) != after.get(key):
                changes.append({"service": key, "before": before.get(key, ""), "after": after.get(key, "")})
        return changes

    def _safe_name(self, name: str) -> str:
        safe = "".join(char for char in name.strip().lower().replace(" ", "-") if char.isalnum() or char in "-_")
        if not safe:
            raise ValidationError("Baseline name cannot be empty.")
        return safe

    def _path(self, name: str) -> Path:
        return self.baseline_dir / f"{name}.json"
