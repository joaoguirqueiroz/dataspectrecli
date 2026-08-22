"""Check Nmap and Nuclei availability without running scans."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cli.interface import TerminalRenderer  # noqa: E402
from services.setup_service import SetupService  # noqa: E402


def run(root_path: Path | None = None, include_templates: bool = False) -> dict:
    service = SetupService(root_path or PROJECT_ROOT)
    report = service.run_tool_checks(include_templates=include_templates)
    return report.to_dict()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Nmap and Nuclei installation.")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--templates", action="store_true", help="Also verify Nuclei templates.")
    args = parser.parse_args(argv)

    renderer = TerminalRenderer()
    renderer.print_setup_report(run(args.root, args.templates))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
