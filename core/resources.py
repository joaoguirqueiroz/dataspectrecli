"""Resource and health snapshots."""

from __future__ import annotations

import platform
import getpass
import os
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ResourceMonitor:
    """Collects lightweight runtime health indicators."""

    root_path: Path
    started_at: float = field(default_factory=time.perf_counter)

    def snapshot(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        uptime = time.perf_counter() - self.started_at
        payload: dict[str, Any] = {
            "uptime_seconds": round(uptime, 4),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "os": platform.system(),
            "user": getpass.getuser(),
            "local_ip": self._local_ip(),
            "cpu_count": os.cpu_count(),
            "memory_total_mb": self._memory_total_mb(),
            "root_path": str(self.root_path),
        }
        if extra:
            payload.update(extra)
        return payload

    def _local_ip(self) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                return sock.getsockname()[0]
        except OSError:
            return "unavailable"

    def _memory_total_mb(self) -> int | str:
        if hasattr(os, "sysconf"):
            try:
                pages = os.sysconf("SC_PHYS_PAGES")
                page_size = os.sysconf("SC_PAGE_SIZE")
                return int((pages * page_size) / (1024 * 1024))
            except (OSError, ValueError):
                return "unavailable"
        return "unavailable"
