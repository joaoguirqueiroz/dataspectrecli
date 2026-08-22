"""Argument parser for DataSpectre CLI."""

from __future__ import annotations

import argparse

from core.constants import APP_NAME, APP_VERSION


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dataspectre",
        description=f"{APP_NAME} - plataforma modular de auditoria autorizada.",
    )
    parser.add_argument("--root", help="Application root directory.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Show application health and loaded components.")
    subparsers.add_parser("interactive", help="Open the guided terminal menu.")
    subparsers.add_parser("help", help="Show navigation and command guidance.")

    setup = subparsers.add_parser("setup", help="Run environment checks and assisted setup.")
    setup_sub = setup.add_subparsers(dest="setup_command", required=True)
    setup_check = setup_sub.add_parser("check", help="Verify Python, pip, Git, project files, Nmap, and Nuclei.")
    setup_check.add_argument("--templates", action="store_true", help="Also verify Nuclei templates.")
    setup_tools = setup_sub.add_parser("tools", help="Verify only Nmap and Nuclei related tools.")
    setup_tools.add_argument("--templates", action="store_true", help="Also verify Nuclei templates.")
    setup_wizard = setup_sub.add_parser("wizard", help="Open the assisted setup flow.")
    setup_wizard.add_argument("--install", action="store_true", help="Ask before installing missing tools.")
    setup_wizard.add_argument("--yes", action="store_true", help="Confirm installer prompts automatically.")
    setup_wizard.add_argument("--templates", action="store_true", help="Also verify Nuclei templates.")

    config = subparsers.add_parser("config", help="Manage central configuration.")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    config_sub.add_parser("show", help="Show all configuration.")
    config_get = config_sub.add_parser("get", help="Read one configuration key.")
    config_get.add_argument("key")
    config_set = config_sub.add_parser("set", help="Persist one configuration key.")
    config_set.add_argument("key")
    config_set.add_argument("value")
    config_sub.add_parser("reset", help="Restore default configuration.")

    projects = subparsers.add_parser("projects", help="Manage projects.")
    projects_sub = projects.add_subparsers(dest="projects_command", required=True)
    project_create = projects_sub.add_parser("create", help="Create a project.")
    project_create.add_argument("name")
    project_create.add_argument("--description", default="")
    project_create.add_argument("--owner", default="system")
    projects_sub.add_parser("list", help="List active projects.")
    project_show = projects_sub.add_parser("show", help="Show project details.")
    project_show.add_argument("project_id")
    project_archive = projects_sub.add_parser("archive", help="Archive a project.")
    project_archive.add_argument("project_id")

    sessions = subparsers.add_parser("sessions", help="Manage project sessions.")
    sessions_sub = sessions.add_subparsers(dest="sessions_command", required=True)
    session_start = sessions_sub.add_parser("start", help="Start a session.")
    session_start.add_argument("project_id")
    session_end = sessions_sub.add_parser("end", help="End a session.")
    session_end.add_argument("project_id")
    session_end.add_argument("session_id")
    session_end.add_argument("--state", default="finished")
    session_list = sessions_sub.add_parser("list", help="List sessions from a project.")
    session_list.add_argument("project_id")

    modules = subparsers.add_parser("modules", help="List or run modules.")
    modules_sub = modules.add_subparsers(dest="modules_command", required=True)
    modules_sub.add_parser("list", help="List registered modules.")
    module_run = modules_sub.add_parser("run", help="Run one module.")
    module_run.add_argument("module_id")
    module_run.add_argument("--project")
    module_run.add_argument("--session")
    module_run.add_argument("--param", action="append", default=[], help="Parameter as key=value.")
    module_run.add_argument("--report", action="store_true", help="Generate a report for the result.")
    module_run.add_argument(
        "--report-format",
        choices=["markdown", "txt", "json", "csv", "html"],
        help="Report format used with --report.",
    )

    scan = subparsers.add_parser("scan", help="Run authorized scanner integrations.")
    scan_sub = scan.add_subparsers(dest="scan_command", required=True)
    scan_nmap = scan_sub.add_parser("nmap", help="Executar analise Nmap controlada e autorizada.")
    scan_nmap.add_argument("target")
    scan_nmap.add_argument(
        "--profile",
        default="basic",
        choices=[
            "quick",
            "rapido",
            "rapida",
            "varredura-rapida",
            "basic",
            "basico",
            "services",
            "servicos",
            "deteccao-servicos",
            "scripts",
            "scripts-padrao",
            "servicos-scripts",
            "services-scripts",
            "ports",
            "portas",
            "portas-especificas",
            "custom",
            "personalizado",
        ],
    )
    scan_nmap.add_argument("--ports")
    scan_nmap.add_argument("--timeout", type=int)
    scan_nmap.add_argument("--custom-flag", action="append", default=[])
    scan_nmap.add_argument("--project")
    scan_nmap.add_argument("--session")
    scan_nmap.add_argument("--formats", default="txt,json,csv,html")
    scan_nmap.add_argument("--authorize", action="store_true")
    scan_nmap.add_argument("--extra-confirm", action="store_true")
    scan_nmap.add_argument("--simulate", action="store_true", help="Gerar dados ficticios marcados se o Nmap estiver ausente.")

    scan_nuclei = scan_sub.add_parser("nuclei", help="Executar auditoria Nuclei controlada e autorizada.")
    scan_nuclei.add_argument("target", nargs="*")
    scan_nuclei.add_argument("--target-file", help="Arquivo com um alvo autorizado por linha.")
    scan_nuclei.add_argument(
        "--profile",
        default="basic",
        choices=[
            "basic",
            "basico",
            "technologies",
            "tecnologias",
            "exposure",
            "exposicao",
            "low-medium",
            "baixa-media",
            "medium-high",
            "media-alta",
            "medias-altas",
            "high",
            "alta",
            "altas",
            "critical",
            "critica",
            "criticas",
            "template",
            "template-especifico",
            "custom",
            "personalizado",
        ],
    )
    scan_nuclei.add_argument("--template", action="append", default=[])
    scan_nuclei.add_argument("--tag", action="append", default=[])
    scan_nuclei.add_argument("--severity", action="append", default=[])
    scan_nuclei.add_argument("--timeout", type=int)
    scan_nuclei.add_argument("--concurrency", type=int)
    scan_nuclei.add_argument("--rate-limit", type=int)
    scan_nuclei.add_argument("--max-targets", type=int)
    scan_nuclei.add_argument("--project")
    scan_nuclei.add_argument("--session")
    scan_nuclei.add_argument("--formats", default="txt,json,csv,html")
    scan_nuclei.add_argument("--authorize", action="store_true")
    scan_nuclei.add_argument("--extra-confirm", action="store_true")
    scan_nuclei.add_argument("--simulate", action="store_true", help="Gerar dados ficticios marcados se o Nuclei estiver ausente.")

    scan_smart = scan_sub.add_parser("smart", help="Executar Nmap, selecionar endpoints web e correlacionar Nuclei.")
    scan_smart.add_argument("target", nargs="+")
    scan_smart.add_argument(
        "--profile",
        default="basic",
        choices=["basic", "basico", "intermediate", "intermediario", "advanced", "avancado", "custom", "personalizado"],
    )
    scan_smart.add_argument("--ports")
    scan_smart.add_argument("--timeout", type=int)
    scan_smart.add_argument("--concurrency", type=int)
    scan_smart.add_argument("--rate-limit", type=int)
    scan_smart.add_argument("--max-targets", type=int)
    scan_smart.add_argument("--custom-flag", action="append", default=[])
    scan_smart.add_argument("--template", action="append", default=[])
    scan_smart.add_argument("--template-dir", action="append", default=[])
    scan_smart.add_argument("--tag", action="append", default=[])
    scan_smart.add_argument("--severity", action="append", default=[])
    scan_smart.add_argument("--nse-profile")
    scan_smart.add_argument("--nse-script", action="append", default=[])
    scan_smart.add_argument("--baseline")
    scan_smart.add_argument("--project")
    scan_smart.add_argument("--session")
    scan_smart.add_argument("--formats", default="txt,json,csv,html")
    scan_smart.add_argument("--authorize", action="store_true")
    scan_smart.add_argument("--extra-confirm", action="store_true")
    scan_smart.add_argument("--simulate", action="store_true", help="Gerar dados ficticios marcados se Nmap/Nuclei estiverem ausentes.")

    baseline = subparsers.add_parser("baseline", help="Create and compare defensive exposure baselines.")
    baseline_sub = baseline.add_subparsers(dest="baseline_command", required=True)
    baseline_create = baseline_sub.add_parser("create", help="Create a baseline from a JSON scan payload.")
    baseline_create.add_argument("name")
    baseline_create.add_argument("--data", required=True, help="Path to JSON scan payload.")
    baseline_compare = baseline_sub.add_parser("compare", help="Compare a JSON scan payload with a baseline.")
    baseline_compare.add_argument("name")
    baseline_compare.add_argument("--data", required=True, help="Path to JSON scan payload.")

    reports = subparsers.add_parser("reports", help="Manage generated reports.")
    reports_sub = reports.add_subparsers(dest="reports_command", required=True)
    reports_sub.add_parser("list", help="List generated reports.")
    report_generate = reports_sub.add_parser("generate", help="Generate a manual report.")
    report_generate.add_argument("--title", required=True)
    report_generate.add_argument("--project")
    report_generate.add_argument("--session")
    report_generate.add_argument(
        "--format",
        choices=["markdown", "txt", "json", "csv", "html"],
        default="markdown",
    )
    report_generate.add_argument("--data", default="{}", help="Inline JSON payload.")
    report_generate.add_argument("--data-file", help="Path to a JSON payload file.")

    plugins = subparsers.add_parser("plugins", help="Manage plugins.")
    plugins_sub = plugins.add_subparsers(dest="plugins_command", required=True)
    plugins_sub.add_parser("list", help="List discovered plugins.")

    logs = subparsers.add_parser("logs", help="Inspect logs and audit trail.")
    logs_sub = logs.add_subparsers(dest="logs_command", required=True)
    audit = logs_sub.add_parser("audit", help="Show recent audit records.")
    audit.add_argument("--limit", type=int, default=20)

    maintenance = subparsers.add_parser("maintenance", help="Run safe maintenance tasks.")
    maintenance_sub = maintenance.add_subparsers(dest="maintenance_command", required=True)
    clean_temp = maintenance_sub.add_parser(
        "clean-temp",
        help="Preview or remove disposable cache and temporary files.",
    )
    clean_temp.add_argument(
        "--yes",
        action="store_true",
        help="Confirm removal. Without this flag the command only previews the cleanup.",
    )

    return parser
