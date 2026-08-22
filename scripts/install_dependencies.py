"""Install or update Python dependencies after explicit confirmation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cli.messages import success, warning  # noqa: E402
from services.setup_service import SetupService  # noqa: E402


def install(root_path: Path | None = None) -> dict:
    service = SetupService(root_path or PROJECT_ROOT)
    return service.install_python_dependencies().to_dict()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install Python dependencies from requirements.txt.")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--yes", action="store_true", help="Confirm dependency installation.")
    args = parser.parse_args(argv)

    if not args.yes:
        answer = input("Executar python -m pip install -r requirements.txt? [sim/nao]: ").strip().lower()
        if answer not in {"s", "sim", "y", "yes"}:
            print(warning("Instalacao cancelada pelo usuario."))
            return 0
    result = install(args.root)
    command = " ".join(result["command"])
    if result["return_code"] == 0:
        print(success(f"Dependencias instaladas: {command}"))
        return 0
    print(warning(f"Falha ao instalar dependencias: {command} | {result['stderr'] or result['stdout']}"))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
