"""Presentation helpers for the DataSpectre terminal interface."""

from __future__ import annotations

import json
import os
import shutil
import textwrap
from typing import Any

from cli.messages import colorize, info
from cli.tables import format_table
from core.constants import APP_VERSION
from services.scanner_service import ETHICAL_NOTICE

try:  # pragma: no cover - depends on terminal/runtime.
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
except ImportError:  # pragma: no cover
    Console = None
    Panel = None
    Text = None


class TerminalRenderer:
    """Renders a compact, terminal-native DataSpectre interface."""

    def __init__(self, width: int | None = None) -> None:
        detected = shutil.get_terminal_size((100, 24)).columns
        requested = width or detected
        # Keep the layout inside narrow terminals and cap it on ultrawide displays.
        self.width = max(24, min(int(requested), 118))
        self.rich_console = (
            Console(width=self.width, soft_wrap=False)
            if Console and getattr(os.sys.stdout, "isatty", lambda: False)()
            else None
        )

    def banner(self) -> str:
        return "\n".join(
            [
                self.brand(),
                f"[ v{APP_VERSION} ]",
                "[ COMANDO: python3 dataspectre.py help ]",
            ]
        )

    def print_banner(self) -> None:
        print(colorize(self.banner(), "green"))

    def brand(self) -> str:
        """Return the compact terminal brand without decorative artwork."""
        return "DATASPECTRECLI"

    def print_json(self, payload: Any) -> None:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))

    def print_table(self, rows: list[dict[str, Any]], columns: list[str]) -> None:
        print(format_table(rows, columns, max_width=self.width))

    def print_status(self, status: dict[str, Any]) -> None:
        self.print_dashboard(status)

    def print_dashboard(self, status: dict[str, Any]) -> None:
        health = status.get("health", {})
        print(colorize(self.dashboard_banner(status), "cyan"))
        notice = "USO AUTORIZADO // " + ETHICAL_NOTICE
        print(colorize("\n".join(textwrap.wrap(notice, width=self.width)), "red"))
        runtime_details = [
            ("PATH", status["root_path"]),
            ("USUARIO", health.get("user", "-")),
            ("CPU", health.get("cpu_count", "-")),
            ("RAM MB", health.get("memory_total_mb", "-")),
            ("UPTIME", f"{health.get('uptime_seconds', 0)}s"),
        ]
        print(colorize(self.metric_badges(runtime_details), "blue"))

    def dashboard_banner(self, status: dict[str, Any]) -> str:
        """Build the compact option-two dashboard header with inline metrics."""
        health = status.get("health", {})
        summary = [
            ("SISTEMA", health.get("os", "-")),
            ("PYTHON", health.get("python_version", "-")),
            ("MODULOS", status["modules"]),
            ("PLUGINS", status["plugins"]),
            ("PROJETOS", status["projects"]),
            ("IP LOCAL", health.get("local_ip", "-")),
        ]
        return "\n".join(
            [
                self.brand(),
                f"[ v{APP_VERSION} ]",
                self.metric_badges(summary),
            ]
        )

    def metric_badges(self, metrics: list[tuple[str, Any]]) -> str:
        """Keep dashboard facts small and side-by-side whenever the terminal allows it."""
        badges = [f"[ {label}: {value if value not in (None, '') else '-'} ]" for label, value in metrics]
        rows: list[str] = []
        current = ""
        for badge in badges:
            candidate = badge if not current else f"{current} {badge}"
            if current and len(candidate) > self.width:
                rows.append(current)
                current = badge
            else:
                current = candidate
        if current:
            rows.append(current)
        return "\n".join(rows)

    def print_help(self) -> None:
        print(
            self.panel(
                "DATASPECTRE // HELP",
                [
                    "Navegar: digite o numero da opcao no menu interativo e pressione Enter.",
                    "Voltar ou sair: use 0 no menu interativo.",
                    "Cancelar: Ctrl+C interrompe a acao atual com seguranca.",
                    "Listar modulos: python3 dataspectre.py modules list.",
                    "Nmap autorizado: python3 dataspectre.py scan nmap <alvo> --authorize.",
                    "Nuclei autorizado: python3 dataspectre.py scan nuclei <alvo> --authorize.",
                    "Smart Scan: python3 dataspectre.py scan smart <alvo> --authorize.",
                    "Baseline: python3 dataspectre.py baseline create nome --data resultado.json.",
                    "Setup: python3 dataspectre.py setup check ou setup wizard --install.",
                    "Relatorios: reports/<projeto>/<ano>/<mes>/<dia>/<sessao>/<ferramenta>.",
                    "Formatos: markdown, txt, json, csv e html.",
                    "Atalho opcional: dataspectre <comando> e ./START_DATASPECTRE.sh <comando>.",
                ],
            )
        )
        commands = [
            {"command": "python3 dataspectre.py status", "purpose": "Ver saude do sistema"},
            {"command": "python3 dataspectre.py interactive", "purpose": "Abrir console guiado"},
            {"command": "python3 dataspectre.py modules list", "purpose": "Listar modulos"},
            {"command": "python3 dataspectre.py scan nmap 127.0.0.1 --authorize", "purpose": "Nmap autorizado"},
            {"command": "python3 dataspectre.py scan nuclei http://localhost --authorize", "purpose": "Nuclei autorizado"},
            {"command": "python3 dataspectre.py scan smart 127.0.0.1 --authorize", "purpose": "Correlacionar Nmap/Nuclei"},
            {"command": "python3 dataspectre.py baseline compare base --data resultado.json", "purpose": "Comparar exposicao"},
            {"command": "python3 dataspectre.py setup check", "purpose": "Verificar ambiente"},
            {"command": "python3 dataspectre.py reports list", "purpose": "Listar relatorios"},
            {"command": "python3 dataspectre.py maintenance clean-temp", "purpose": "Simular limpeza"},
        ]
        self.print_table(commands, ["command", "purpose"])

    def print_modules(self, modules: list[dict[str, Any]]) -> None:
        if not modules:
            self.print_panel(
                "MODULOS",
                ["Nenhum modulo carregado. Verifique modules/ e os logs tecnicos."],
                style="yellow",
            )
            return
        self.print_panel(
            "MODULOS CARREGADOS",
            [f"Total: {len(modules)}", "Os modulos sao isolados e auditados pelo gerenciador central."],
            style="green",
        )
        self.print_table(modules, ["id", "name", "category", "version", "state", "description"])

    def print_history(self, records: list[dict[str, Any]]) -> None:
        rows = [
            {
                "timestamp": record.get("timestamp"),
                "function": record.get("function"),
                "result": record.get("result"),
                "error": record.get("error") or "",
            }
            for record in records
        ]
        self.print_panel("HISTORICO", [f"Eventos recentes: {len(rows)}"], style="green")
        self.print_table(rows, ["timestamp", "function", "result", "error"])

    def print_scan_result(self, result: dict[str, Any]) -> None:
        data = result.get("data", {})
        reports = data.get("reports", [])
        self.print_panel(
            f"RESULTADO // {result.get('module_id')}",
            [
                f"Status: {result.get('status')}",
                f"Sucesso: {result.get('success')}",
                f"Ferramenta: {data.get('tool')}",
                f"Perfil: {data.get('profile')}",
                f"Relatorios: {len(reports)}",
            ],
            style="green" if result.get("success") else "red",
        )
        messages = _result_messages(result, data)
        if messages:
            self.print_panel("MENSAGENS", messages, style="yellow")
        if reports:
            self.print_table(reports, ["format", "path", "generated_at"])
        if data.get("simulation_notice"):
            self.print_panel("SIMULACAO", [data["simulation_notice"]], style="yellow")
        if data.get("progress"):
            self.print_panel("ETAPAS", data["progress"], style="green")

    def print_smart_scan_result(self, result: dict[str, Any]) -> None:
        data = result.get("data", {})
        correlation = data.get("correlation", {})
        summary = correlation.get("summary", {})
        reports = data.get("reports", [])
        self.print_panel(
            "SMART SCAN // CORRELATION",
            [
                f"Status: {result.get('status')}",
                f"Sucesso: {result.get('success')}",
                f"Perfil: {data.get('profile')}",
                f"Hosts: {summary.get('hosts', 0)}",
                f"Portas abertas: {summary.get('open_ports', 0)}",
                f"Endpoints web: {summary.get('web_endpoints', 0)}",
                f"Achados: {summary.get('findings', 0)}",
                f"Relatorios: {len(reports)}",
            ],
            style="green" if result.get("success") else "red",
        )
        messages = _result_messages(result, data)
        if messages:
            self.print_panel("MENSAGENS", messages, style="yellow")
        findings = correlation.get("findings", [])
        if findings:
            self.print_table(findings[:10], ["risk", "severity", "target", "port", "service", "template"])
        decisions = correlation.get("decisions", [])
        if decisions:
            self.print_panel("DECISOES DO MOTOR", decisions[:8], style="green")
        if reports:
            self.print_table(reports, ["format", "path", "generated_at"])
        if data.get("simulation_notice"):
            self.print_panel("SIMULACAO", [data["simulation_notice"]], style="yellow")
        if data.get("progress"):
            self.print_panel("ETAPAS", data["progress"], style="green")

    def print_baseline_compare(self, result: dict[str, Any]) -> None:
        summary = result.get("summary", {})
        self.print_panel(
            "BASELINE // COMPARE",
            [
                f"Status: {summary.get('status')}",
                f"Novos servicos: {summary.get('new_services', 0)}",
                f"Servicos removidos: {summary.get('removed_services', 0)}",
                f"Novos achados: {summary.get('new_findings', 0)}",
                f"Achados resolvidos: {summary.get('resolved_findings', 0)}",
                f"Mudancas de versao: {summary.get('version_changes', 0)}",
            ],
            style="yellow" if summary.get("status") == "changed" else "green",
        )
        rows: list[dict[str, Any]] = []
        for key in ("new_services", "removed_services", "new_findings", "resolved_findings"):
            rows.extend({"type": key, "value": value} for value in result.get(key, []))
        if rows:
            self.print_table(rows[:20], ["type", "value"])

    def print_setup_report(self, report: dict[str, Any]) -> None:
        checks = report.get("checks", [])
        self.print_panel(
            "ENVIRONMENT CHECK",
            [
                f"Status final: {report.get('overall_status')}",
                f"Sistema: {report.get('operating_system')}",
                f"Gerenciador: {report.get('package_manager') or 'nao detectado'}",
                f"Relatorio TXT: {report.get('report_paths', {}).get('txt', '-')}",
                f"Relatorio JSON: {report.get('report_paths', {}).get('json', '-')}",
            ],
            style="green" if report.get("overall_status") == "OK" else "yellow",
        )
        rows = [
            {
                "item": check.get("name"),
                "status": check.get("status"),
                "version": check.get("version") or "-",
                "action": check.get("action") or "-",
            }
            for check in checks
        ]
        self.print_table(rows, ["item", "status", "version", "action"])

    def print_final_session_report(self, summary: dict[str, Any]) -> None:
        print(
            self.panel(
                "SESSION // FINAL REPORT",
                [
                    f"Tempo total: {summary.get('duration_seconds', 0)}s",
                    f"Modulos usados: {summary.get('modules_used', 0)}",
                    f"Relatorios criados: {summary.get('reports_created', 0)}",
                    f"Erros encontrados: {summary.get('errors_found', 0)}",
                ],
            )
        )
        modules = summary.get("module_ids") or []
        if modules:
            self.print_table([{"module": module_id} for module_id in modules], ["module"])

    def print_clean_result(self, result: dict[str, Any]) -> None:
        status = "simulacao" if result.get("dry_run") else "concluida"
        print(
            self.panel(
                f"CLEANUP // {status.upper()}",
                [
                    f"Arquivos analisados: {result.get('scanned_paths', 0)}",
                    f"Arquivos removidos: {result.get('removed_files', 0)}",
                    f"Diretorios removidos: {result.get('removed_dirs', 0)}",
                    f"Espaco liberado: {result.get('freed_bytes', 0)} bytes",
                    "Relatorios, logs, projetos, sessoes e dados persistentes foram preservados.",
                ],
            )
        )

    def print_panel(self, title: str, lines: list[str] | str, style: str = "green") -> None:
        if self.rich_console and Panel and Text:
            content = "\n".join(lines if isinstance(lines, list) else [lines])
            self.rich_console.print(Panel(Text(content), title=title, border_style=style))
            return
        rendered = self.panel(title, lines)
        print(colorize(rendered, style if style in {"green", "yellow", "red", "cyan", "blue"} else "green"))

    def panel(self, title: str, lines: list[str] | str) -> str:
        content = [lines] if isinstance(lines, str) else lines
        inner_width = self.width - 4
        top = "+" + "-" * (self.width - 2) + "+"
        clean_title = str(title)[:inner_width]
        title_line = f"| {clean_title.ljust(inner_width)} |"
        rendered = [top, title_line, top]
        for line in content:
            wrapped = textwrap.wrap(str(line), width=inner_width, replace_whitespace=False) or [""]
            for item in wrapped:
                rendered.append(f"| {item[:inner_width].ljust(inner_width)} |")
        rendered.append(top)
        return "\n".join(rendered)

    def progress_bar(self, current: int, total: int, width: int = 28) -> str:
        if total <= 0:
            total = 1
        ratio = max(0.0, min(float(current) / float(total), 1.0))
        filled = int(round(width * ratio))
        bar = "#" * filled + "." * (width - filled)
        return f"[{bar}] {int(ratio * 100)}%"

    def print_info(self, message: str) -> None:
        print(info(message))


def _result_messages(result: dict[str, Any], data: dict[str, Any]) -> list[str]:
    messages = [str(message) for message in result.get("messages", []) if str(message).strip()]
    reason = str(data.get("reason") or "").strip()
    if reason and reason not in messages:
        messages.insert(0, reason)
    return messages
