"""Run a small local smoke check."""

from __future__ import annotations

import os
from pathlib import Path

from app.application import DataSpectreApplication


def main(root_path: Path | None = None) -> int:
    env_root = os.environ.get("DATASPECTRE_ROOT") or os.environ.get("SENTINELSCAN_ROOT")
    root = root_path or Path(env_root or Path(__file__).resolve().parents[1])
    app = DataSpectreApplication(root)
    try:
        status = app.status()
        print(status)
        return 0
    finally:
        app.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
