"""Assisted setup wizard for DataSpectre CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cli.interface import TerminalRenderer  # noqa: E402
from cli.messages import success, warning  # noqa: E402
from services.setup_service import SetupReport, SetupService  # noqa: E402


InputFunc = Callable[[str], str]


def run_wizard(
    root_path: Path | None = None,
    ask_to_install: bool = True,
    assume_yes: bool = False,
    include_templates: bool = False,
    input_func: InputFunc = input,
) -> SetupReport:
    service = SetupService(root_path or PROJECT_ROOT)
    renderer = TerminalRenderer()
    renderer.print_panel(
        "DataSpectre Setup Wizard",
        [
            "Este assistente verifica o ambiente local com seguranca.",
            "Nenhum scan Nmap ou Nuclei sera executado.",
            "Instalacoes exigem confirmacao explicita.",
        ],
        style="cyan",
    )
    report = service.run_checks(include_templates=include_templates)
    renderer.print_setup_report(report.to_dict())
    if not ask_to_install:
        print(warning("Modo verificacao. Nenhuma instalacao foi executada."))
        return report

    missing = {check.name.lower() for check in report.checks if check.status != "OK"}
    if "dependencias python" in missing and _confirm(
        "Executar python -m pip install -r requirements.txt?", assume_yes, input_func
    ):
        print(_format_result(service.install_python_dependencies().to_dict()))
    if "nmap" in missing and _confirm(
        "Instalar Nmap com o gerenciador de pacotes detectado?", assume_yes, input_func
    ):
        for result in service.install_nmap():
            print(_format_result(result.to_dict()))
    if "nuclei" in missing and _confirm(
        "Instalar Nuclei via Go, se disponivel?", assume_yes, input_func
    ):
        for result in service.install_nuclei():
            print(_format_result(result.to_dict()))
    final_report = service.run_checks(include_templates=include_templates)
    renderer.print_setup_report(final_report.to_dict())
    return final_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the DataSpectre assisted setup wizard.")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--check-only", action="store_true", help="Only verify the environment.")
    parser.add_argument("--install", action="store_true", help="Ask before installing missing dependencies/tools.")
    parser.add_argument("--yes", action="store_true", help="Confirm installer prompts automatically.")
    parser.add_argument("--templates", action="store_true", help="Also verify Nuclei templates.")
    args = parser.parse_args(argv)

    ask_to_install = args.install or not args.check_only
    run_wizard(
        root_path=args.root,
        ask_to_install=ask_to_install,
        assume_yes=args.yes,
        include_templates=args.templates,
    )
    return 0


def _confirm(question: str, assume_yes: bool, input_func: InputFunc) -> bool:
    if assume_yes:
        print(f"{question} [sim]")
        return True
    answer = input_func(f"{question} [sim/nao]: ").strip().lower()
    return answer in {"s", "sim", "y", "yes"}


def _format_result(result: dict) -> str:
    command = " ".join(result.get("command") or ["acao-manual"])
    if result.get("return_code") == 0:
        return success(f"Comando concluido: {command}")
    return warning(
        f"Comando requer acao manual ({result.get('return_code')}): "
        f"{command} | {result.get('stderr') or result.get('stdout') or '-'}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
