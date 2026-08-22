"""CLI command dispatcher."""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.application import DataSpectreApplication
from cli.interface import TerminalRenderer
from cli.messages import error, success, warning
from cli.parser import build_parser
from core.exceptions import DataSpectreError, ValidationError
from core.module import ModuleExecutionContext


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root_path = _resolve_root(args.root)
    renderer = TerminalRenderer()
    application = DataSpectreApplication(root_path)
    context: Any | None = None
    command_name = _command_name(args)

    try:
        context = application.initialize()
        command = args.command or "interactive"
        if command == "interactive":
            _interactive(application, context, renderer)
        elif command == "status":
            renderer.print_status(application.status())
        elif command == "help":
            renderer.print_help()
        elif command == "setup":
            _handle_setup(args, context, renderer)
        elif command == "config":
            _handle_config(args, context, renderer)
        elif command == "projects":
            _handle_projects(args, context, renderer)
        elif command == "sessions":
            _handle_sessions(args, context, renderer)
        elif command == "modules":
            _handle_modules(args, context, renderer)
        elif command == "scan":
            _handle_scan(args, context, renderer)
        elif command == "baseline":
            _handle_baseline(args, context, renderer)
        elif command == "reports":
            _handle_reports(args, context, renderer)
        elif command == "plugins":
            _handle_plugins(args, context, renderer)
        elif command == "logs":
            _handle_logs(args, context)
        elif command == "maintenance":
            _handle_maintenance(args, context, renderer)
        else:
            parser.print_help()
            return 2
        _record_history(context, command_name, result="success")
        return 0
    except DataSpectreError as exc:
        _record_cli_error(context, command_name, exc)
        print(error(f"Nao foi possivel concluir a operacao: {exc}"), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        _record_cli_error(context, command_name, KeyboardInterrupt("interrupted"))
        print(error("Operacao cancelada pelo usuario."), file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI boundary converts faults into safe output.
        _record_cli_error(context, command_name, exc, details={"traceback": traceback.format_exc()})
        print(
            error("Ocorreu um erro inesperado. Detalhes tecnicos foram salvos nos logs."),
            file=sys.stderr,
        )
        return 1
    finally:
        application.shutdown()


def _resolve_root(root_arg: str | None) -> Path:
    if root_arg:
        return Path(root_arg)
    if os.environ.get("DATASPECTRE_ROOT"):
        return Path(os.environ["DATASPECTRE_ROOT"])
    # Backward compatibility with installations of the original project.
    if os.environ.get("SENTINELSCAN_ROOT"):
        return Path(os.environ["SENTINELSCAN_ROOT"])
    return Path(__file__).resolve().parents[1]


def _handle_config(args: Any, context: Any, renderer: TerminalRenderer) -> None:
    if args.config_command == "show":
        renderer.print_json(context.config_service.get())
    elif args.config_command == "get":
        renderer.print_json(context.config_service.get(args.key))
    elif args.config_command == "set":
        context.permission_manager.require("config:write")
        value = _parse_value(args.value)
        context.config_service.set(args.key, value)
        context.audit_service.record("config.updated", target=args.key, details={"value": value})
        print(success(f"Configuration '{args.key}' updated."))
    elif args.config_command == "reset":
        context.permission_manager.require("config:write")
        context.config_service.reset()
        context.audit_service.record("config.reset", target="settings")
        print(success("Configuration restored to defaults."))


def _handle_setup(args: Any, context: Any, renderer: TerminalRenderer) -> None:
    if args.setup_command == "check":
        report = context.setup_service.run_checks(include_templates=args.templates)
        renderer.print_setup_report(report.to_dict())
        context.history_service.record_action(
            "setup.check",
            result=report.overall_status,
            details={"checks": len(report.checks), "report_paths": report.report_paths},
        )
    elif args.setup_command == "tools":
        report = context.setup_service.run_tool_checks(include_templates=args.templates)
        renderer.print_setup_report(report.to_dict())
        context.history_service.record_action(
            "setup.tools",
            result=report.overall_status,
            details={"checks": len(report.checks), "report_paths": report.report_paths},
        )
    elif args.setup_command == "wizard":
        report = _run_assisted_setup(
            context,
            renderer,
            ask_to_install=args.install,
            assume_yes=args.yes,
            include_templates=args.templates,
        )
        context.history_service.record_action(
            "setup.wizard",
            result=report.overall_status,
            details={"checks": len(report.checks), "report_paths": report.report_paths},
        )


def _handle_projects(args: Any, context: Any, renderer: TerminalRenderer) -> None:
    if args.projects_command == "create":
        context.permission_manager.require("projects:write")
        project = context.project_service.create_project(
            args.name, description=args.description, owner=args.owner
        )
        renderer.print_json(project.to_dict())
    elif args.projects_command == "list":
        projects = [project.to_dict() for project in context.project_service.list_projects()]
        renderer.print_table(projects, ["id", "name", "status", "updated_at", "owner"])
    elif args.projects_command == "show":
        renderer.print_json(context.project_service.get_project(args.project_id).to_dict())
    elif args.projects_command == "archive":
        context.permission_manager.require("projects:write")
        project = context.project_service.archive_project(args.project_id)
        print(success(f"Project '{project.id}' archived."))


def _handle_sessions(args: Any, context: Any, renderer: TerminalRenderer) -> None:
    if args.sessions_command == "start":
        context.permission_manager.require("sessions:write")
        session = context.session_service.start_session(
            args.project_id, settings_snapshot=context.config_service.get()
        )
        renderer.print_json(session.to_dict())
    elif args.sessions_command == "end":
        context.permission_manager.require("sessions:write")
        session = context.session_service.end_session(args.project_id, args.session_id, args.state)
        renderer.print_json(session.to_dict())
    elif args.sessions_command == "list":
        sessions = [record.to_dict() for record in context.session_service.list_sessions(args.project_id)]
        renderer.print_table(sessions, ["id", "project_id", "state", "started_at", "ended_at"])


def _handle_modules(args: Any, context: Any, renderer: TerminalRenderer) -> None:
    if args.modules_command == "list":
        renderer.print_modules(context.module_manager.list_modules())
    elif args.modules_command == "run":
        context.permission_manager.require("modules:run")
        parameters = _parse_params(args.param)
        execution_context = ModuleExecutionContext(
            application=context,
            parameters=parameters,
            project_id=args.project,
            session_id=args.session,
        )
        result = context.module_manager.execute(args.module_id, execution_context)
        if args.project and args.session:
            context.session_service.append_event(
                args.project,
                args.session,
                {"type": "module_execution", "module_id": args.module_id, "success": result.success},
            )
        renderer.print_json(result.to_dict())
        if args.report:
            record = context.report_service.generate_report(
                title=f"Module result: {args.module_id}",
                results=result.to_dict(),
                project_id=args.project,
                session_id=args.session,
                report_format=args.report_format
                or context.config_service.get("reports.default_format", "markdown"),
            )
            print(success(f"Report generated: {record.path}"))


def _handle_scan(args: Any, context: Any, renderer: TerminalRenderer) -> None:
    context.permission_manager.require("modules:run")
    if args.scan_command == "nmap":
        parameters = {
            "target": args.target,
            "profile": args.profile,
            "ports": args.ports,
            "timeout": args.timeout,
            "custom_flags": args.custom_flag,
            "authorized": args.authorize,
            "extra_confirmed": args.extra_confirm,
            "simulate": args.simulate,
            "report_formats": args.formats,
        }
        result = context.module_manager.execute(
            "nmap_scan",
            ModuleExecutionContext(
                application=context,
                parameters=parameters,
                project_id=args.project,
                session_id=args.session,
            ),
        )
        renderer.print_scan_result(result.to_dict())
    elif args.scan_command == "nuclei":
        targets = list(args.target)
        if args.target_file:
            targets.extend(_read_lines_file(args.target_file))
        parameters = {
            "targets": targets,
            "profile": args.profile,
            "templates": args.template,
            "tags": args.tag,
            "severities": args.severity,
            "timeout": args.timeout,
            "concurrency": args.concurrency,
            "rate_limit": args.rate_limit,
            "max_targets": args.max_targets,
            "authorized": args.authorize,
            "extra_confirmed": args.extra_confirm,
            "simulate": args.simulate,
            "report_formats": args.formats,
        }
        result = context.module_manager.execute(
            "nuclei_scan",
            ModuleExecutionContext(
                application=context,
                parameters=parameters,
                project_id=args.project,
                session_id=args.session,
            ),
        )
        renderer.print_scan_result(result.to_dict())
    elif args.scan_command == "smart":
        parameters = {
            "targets": args.target,
            "profile": args.profile,
            "ports": args.ports,
            "timeout": args.timeout,
            "concurrency": args.concurrency,
            "rate_limit": args.rate_limit,
            "max_targets": args.max_targets,
            "custom_flags": args.custom_flag,
            "templates": args.template,
            "template_dirs": args.template_dir,
            "tags": args.tag,
            "severities": args.severity,
            "nse_profile": args.nse_profile,
            "nse_scripts": args.nse_script,
            "baseline": args.baseline,
            "authorized": args.authorize,
            "extra_confirmed": args.extra_confirm,
            "simulate": args.simulate,
            "report_formats": args.formats,
        }
        result = context.module_manager.execute(
            "smart_scan",
            ModuleExecutionContext(
                application=context,
                parameters=parameters,
                project_id=args.project,
                session_id=args.session,
            ),
        )
        renderer.print_smart_scan_result(result.to_dict())


def _handle_baseline(args: Any, context: Any, renderer: TerminalRenderer) -> None:
    context.permission_manager.require("reports:write")
    payload = _read_json_file(args.data)
    if args.baseline_command == "create":
        record = context.baseline_service.create_baseline(args.name, payload, source=args.data)
        context.history_service.record_action(
            "baseline.create",
            result="success",
            details={"name": record.name, "path": record.path},
        )
        renderer.print_json(record.to_dict())
    elif args.baseline_command == "compare":
        result = context.baseline_service.compare(args.name, payload)
        context.history_service.record_action(
            "baseline.compare",
            result=result["summary"]["status"],
            details=result["summary"],
        )
        renderer.print_baseline_compare(result)


def _handle_reports(args: Any, context: Any, renderer: TerminalRenderer) -> None:
    if args.reports_command == "list":
        reports = [report.to_dict() for report in context.report_service.list_reports()]
        renderer.print_table(reports, ["id", "title", "format", "project_id", "generated_at", "path"])
    elif args.reports_command == "generate":
        context.permission_manager.require("reports:write")
        payload = (
            _read_json_file(args.data_file)
            if getattr(args, "data_file", None)
            else _parse_json(args.data)
        )
        record = context.report_service.generate_report(
            title=args.title,
            results={"success": True, "status": "manual", "data": payload},
            project_id=args.project,
            session_id=args.session,
            report_format=args.format,
        )
        renderer.print_json(record.to_dict())


def _handle_plugins(args: Any, context: Any, renderer: TerminalRenderer) -> None:
    if args.plugins_command == "list":
        renderer.print_table(
            context.plugin_manager.list_plugins(),
            ["id", "name", "category", "version", "enabled", "state", "description"],
        )


def _handle_logs(args: Any, context: Any) -> None:
    if args.logs_command == "audit":
        context.permission_manager.require("logs:read")
        for line in context.log_service.tail_audit(args.limit):
            print(line)


def _handle_maintenance(args: Any, context: Any, renderer: TerminalRenderer) -> None:
    if args.maintenance_command == "clean-temp":
        context.permission_manager.require("maintenance:clean")
        result = context.cleanup_service.clean(dry_run=not args.yes)
        renderer.print_clean_result(result.to_dict())
        if args.yes:
            print(success("Temporary files cleaned safely."))
        else:
            print(warning("Preview only. Run again with --yes to confirm cleanup."))


def _interactive(
    application: DataSpectreApplication, context: Any, renderer: TerminalRenderer
) -> None:
    renderer.print_dashboard(application.status())
    renderer.print_info("DataSpectre Terminal iniciado. Digite 0 para encerrar com seguranca.")
    while True:
        print(
            renderer.panel(
                "DATASPECTRE // MAIN MENU",
                [
                    "1. Analise de rede autorizada (Nmap)",
                    "2. Auditoria web autorizada (Nuclei)",
                    "3. Smart Scan correlacionado",
                    "4. Inventario de ativos",
                    "5. Diagnostico local do sistema",
                    "6. Central de relatorios",
                    "7. Resumo de projetos",
                    "8. Historico de operacoes",
                    "9. Configuracoes e instalacao",
                    "10. Modulos disponiveis",
                    "11. Ajuda de uso",
                    "12. Limpeza segura de temporarios",
                    "0. Sair",
                ],
            )
        )
        try:
            choice = input("dataspectre> ").strip()
        except EOFError:
            choice = "0"
        if choice == "0":
            renderer.print_final_session_report(application.session_summary())
            print("DataSpectre encerrado com seguranca.")
            return
        if choice == "1":
            _interactive_nmap(context, renderer)
        elif choice == "2":
            _interactive_nuclei(context, renderer)
        elif choice == "3":
            _interactive_smart(context, renderer)
        elif choice == "4":
            _interactive_inventory(context, renderer)
        elif choice == "5":
            _interactive_system_health(context, renderer)
        elif choice == "6":
            _interactive_reports(context, renderer)
        elif choice == "7":
            _interactive_project_summary(context, renderer)
        elif choice == "8":
            renderer.print_panel(
                "Historico de operacoes",
                [
                    "Exibe as ultimas acoes registradas nesta instalacao.",
                    "Nao executa scans, nao altera dados e nao envia informacoes para fora.",
                ],
                style="cyan",
            )
            renderer.print_history(context.history_service.read_recent(20))
        elif choice == "9":
            _interactive_settings(context, renderer)
        elif choice == "10":
            renderer.print_panel(
                "Modulos disponiveis",
                [
                    "Mostra os modulos carregados, a categoria e o estado atual de cada um.",
                    "Use esta tela para confirmar o que esta pronto antes de iniciar uma operacao.",
                ],
                style="cyan",
            )
            renderer.print_modules(context.module_manager.list_modules())
        elif choice == "11":
            renderer.print_help()
        elif choice == "12":
            _interactive_cleanup(context, renderer)
        elif choice.lower() == "status":
            renderer.print_dashboard(application.status())
        elif choice.lower() in {"p", "projects"}:
            renderer.print_table(
                [project.to_dict() for project in context.project_service.list_projects()],
                ["id", "name", "status", "updated_at"],
            )
        elif not choice:
            continue
        else:
            print(warning("Opcao invalida. Digite 12 para abrir a ajuda."))

def _required_input(prompt: str, guidance: str) -> str:
    """Read mandatory interactive input without sending empty data to a module."""
    while True:
        try:
            value = input(prompt).strip()
        except EOFError as exc:
            raise KeyboardInterrupt from exc
        if value:
            return value
        print(warning(guidance))


def _interactive_reports(context: Any, renderer: TerminalRenderer) -> None:
    renderer.print_panel(
        "Central de relatorios",
        [
            "Consulte relatorios ja salvos ou crie um resumo manual a partir de dados JSON.",
            "O titulo identifica o arquivo. Os dados devem ser um objeto JSON, por exemplo: {\"status\":\"ok\"}.",
        ],
        style="cyan",
    )
    while True:
        print(
            renderer.panel(
                "CENTRAL DE RELATORIOS",
                [
                    "1. Listar relatorios",
                    "2. Gerar relatorio manual",
                    "0. Voltar",
                ],
            )
        )
        choice = input("> ").strip()
        if choice == "0":
            return
        if choice == "1":
            _handle_reports(SimpleNamespace(reports_command="list"), context, renderer)
        elif choice == "2":
            renderer.print_panel(
                "Novo relatorio manual",
                [
                    "Titulo: nome que aparecera no relatorio.",
                    "Dados JSON: informe campos entre chaves; Enter usa um objeto vazio.",
                    'Exemplo: {"status":"ok","observacao":"ambiente local"}',
                ],
                style="cyan",
            )
            title = input("Titulo [Relatorio manual]: ").strip() or "Relatorio manual"
            raw_data = input("Dados JSON [{}]: ").strip() or "{}"
            try:
                _handle_reports(
                    SimpleNamespace(
                        reports_command="generate",
                        title=title,
                        project=None,
                        session=None,
                        format="json",
                        data=raw_data,
                    ),
                    context,
                    renderer,
                )
            except ValidationError as exc:
                print(error(f"Dados invalidos: {exc}"))
        else:
            print("Opcao invalida.")


def _interactive_cleanup(context: Any, renderer: TerminalRenderer) -> None:
    renderer.print_panel(
        "Limpeza de temporarios",
        [
            "A limpeza afeta apenas cache e arquivos descartaveis.",
            "Relatorios, logs, projetos, sessoes e dados persistentes sao preservados.",
        ],
        style="yellow",
    )
    renderer.print_clean_result(context.cleanup_service.preview().to_dict())
    if not _confirm("Confirmar limpeza segura dos temporarios?", assume_yes=False):
        print(warning("Limpeza cancelada. Nenhum arquivo foi apagado."))
        context.history_service.record_action(
            "cleanup.temp",
            result="cancelled",
            details={"source": "interactive"},
        )
        return
    result = context.cleanup_service.clean(dry_run=False)
    renderer.print_clean_result(result.to_dict())
    context.history_service.record_action(
        "cleanup.temp",
        result="success",
        details=result.to_dict(),
    )


def _interactive_settings(context: Any, renderer: TerminalRenderer) -> None:
    renderer.print_panel(
        "Configuracoes e instalacao",
        [
            "Consulte as configuracoes atuais, verifique dependencias ou abra o instalador assistido.",
            "Nenhuma ferramenta externa e instalada sem uma confirmacao explicita.",
        ],
        style="cyan",
    )
    while True:
        print(
            renderer.panel(
                "Configuracoes",
                [
                    "1. Ver configuracao atual",
                    "2. Verificar ambiente",
                    "3. Instalador assistido",
                    "4. Verificar Nmap/Nuclei",
                    "0. Voltar",
                ],
            )
        )
        choice = input("> ").strip()
        if choice == "0":
            return
        if choice == "1":
            renderer.print_json(context.config_service.get())
        elif choice == "2":
            report = context.setup_service.run_checks()
            renderer.print_setup_report(report.to_dict())
            context.history_service.record_action(
                "setup.check",
                result=report.overall_status,
                details={"source": "interactive-settings"},
            )
        elif choice == "3":
            _run_assisted_setup(context, renderer, ask_to_install=True)
        elif choice == "4":
            report = context.setup_service.run_tool_checks()
            renderer.print_setup_report(report.to_dict())
            context.history_service.record_action(
                "setup.tools",
                result=report.overall_status,
                details={"source": "interactive-settings"},
            )
        else:
            print("Opcao invalida.")


def _run_assisted_setup(
    context: Any,
    renderer: TerminalRenderer,
    ask_to_install: bool = False,
    assume_yes: bool = False,
    include_templates: bool = False,
) -> Any:
    renderer.print_panel(
        "Instalador assistido",
        [
            "Sera feita uma verificacao segura do ambiente.",
            "Nenhum scan sera executado.",
            "Instalacoes so acontecem com confirmacao explicita.",
        ],
        style="cyan",
    )
    report = context.setup_service.run_checks(include_templates=include_templates)
    renderer.print_setup_report(report.to_dict())
    if not ask_to_install:
        print(warning("Modo verificacao. Nenhuma instalacao foi executada."))
        return report

    missing = {check.name.lower(): check for check in report.checks if check.status in {"Ausente", "Precisa de acao manual", "Erro"}}
    if "dependencias python" in missing and _confirm("Instalar/atualizar dependencias Python?", assume_yes):
        result = context.setup_service.install_python_dependencies()
        print(_format_command_result(result.to_dict()))
    if "nmap" in missing and _confirm("Instalar Nmap usando o gerenciador detectado?", assume_yes):
        for result in context.setup_service.install_nmap():
            print(_format_command_result(result.to_dict()))
    if "nuclei" in missing and _confirm("Instalar Nuclei usando Go, se disponivel?", assume_yes):
        for result in context.setup_service.install_nuclei():
            print(_format_command_result(result.to_dict()))
    rerun = context.setup_service.run_checks(include_templates=include_templates)
    renderer.print_setup_report(rerun.to_dict())
    return rerun


def _interactive_nmap(context: Any, renderer: TerminalRenderer) -> None:
    renderer.print_panel(
        "Analise de rede autorizada",
        [
            "Informe somente um ativo, uma rede privada ou um laboratorio sob sua autorizacao.",
            "Alvo aceito: IP (192.168.1.10), hostname (servidor.interno) ou CIDR privado (192.168.1.0/24).",
            "Perfis: rapida, servicos, scripts-padrao, servicos-scripts, portas e custom.",
            "Para uma analise real, o binario Nmap precisa estar instalado.",
            "A simulacao so e usada se voce confirmar essa opcao no proximo passo.",
        ],
        style="cyan",
    )
    _print_scanner_availability(context, renderer, ("nmap",))
    target = _required_input(
        "Alvo autorizado (IP, hostname ou CIDR privado): ",
        "O alvo e obrigatorio. Informe o endereco do ativo autorizado.",
    )
    profile = input("Perfil [servicos-scripts]: ").strip() or "servicos-scripts"
    ports = input("Portas para perfil portas/custom (ex.: 22,80,443; Enter ignora): ").strip() or None
    authorization = input("Confirmo que tenho autorizacao? [sim/nao]: ").strip()
    extra = "nao"
    if profile.lower() in {"custom", "personalizado"}:
        extra = input("Confirmacao extra para perfil personalizado? [sim/nao]: ").strip()
    simulate = input("Se Nmap estiver ausente, usar simulacao identificada? [sim/nao] [nao]: ").strip() or "nao"
    result = context.module_manager.execute(
        "nmap_scan",
        ModuleExecutionContext(
            application=context,
            parameters={
                "target": target,
                "profile": profile,
                "ports": ports,
                "authorized": authorization,
                "extra_confirmed": extra,
                "simulate": simulate,
            },
        ),
    )
    renderer.print_scan_result(result.to_dict())


def _interactive_nuclei(context: Any, renderer: TerminalRenderer) -> None:
    renderer.print_panel(
        "Auditoria web autorizada",
        [
            "Informe somente URL ou hostname de aplicacao web que voce esta autorizado a auditar.",
            "Alvo aceito: https://app.interna, http://127.0.0.1 ou portal.interno.",
            "Perfis: basic, medium-high, high, critical, template, custom.",
            "Perfis high/critical/template/custom exigem confirmacao extra.",
            "Para uma auditoria real, o binario Nuclei precisa estar instalado.",
            "A simulacao so e usada se voce confirmar essa opcao no proximo passo.",
        ],
        style="cyan",
    )
    _print_scanner_availability(context, renderer, ("nuclei",))
    targets = _required_input(
        "Alvo(s) web autorizados, separados por virgula: ",
        "Informe pelo menos uma URL ou hostname autorizado.",
    )
    profile = input("Perfil [basic]: ").strip() or "basic"
    templates = input("Templates para perfil template/custom (opcional): ").strip()
    authorization = input("Confirmo que tenho autorizacao? [sim/nao]: ").strip()
    extra = "nao"
    if profile.lower() in {"high", "alta", "critical", "critica", "template", "template-especifico", "custom", "personalizado"}:
        extra = input("Confirmacao extra para perfil avancado/personalizado? [sim/nao]: ").strip()
    simulate = input("Se Nuclei estiver ausente, usar simulacao identificada? [sim/nao] [nao]: ").strip() or "nao"
    result = context.module_manager.execute(
        "nuclei_scan",
        ModuleExecutionContext(
            application=context,
            parameters={
                "targets": targets,
                "profile": profile,
                "templates": templates,
                "authorized": authorization,
                "extra_confirmed": extra,
                "simulate": simulate,
            },
        ),
    )
    renderer.print_scan_result(result.to_dict())



def _interactive_smart(context: Any, renderer: TerminalRenderer) -> None:
    renderer.print_panel(
        "SMART SCAN",
        [
            "Executa Nmap no ativo autorizado e usa Nuclei apenas em endpoints web encontrados.",
            "Alvo aceito: IP, hostname ou CIDR privado. Exemplos: 127.0.0.1, servidor.interno, 192.168.1.0/24.",
            "Perfis: basic, intermediate, advanced e custom.",
            "Perfis advanced/custom exigem confirmacao extra.",
            "Para uma varredura real, instale Nmap; Nuclei so roda em endpoints web detectados.",
            "A simulacao so e usada se voce confirmar essa opcao no proximo passo.",
        ],
        style="green",
    )
    _print_scanner_availability(context, renderer, ("nmap", "nuclei"))
    targets = _required_input(
        "Alvo(s) autorizados, separados por virgula: ",
        "Informe pelo menos um ativo autorizado.",
    )
    profile = input("Perfil [basic]: ").strip() or "basic"
    authorization = input("Confirmo que tenho autorizacao? [sim/nao]: ").strip()
    extra = "nao"
    if profile.lower() in {"advanced", "avancado", "custom", "personalizado"}:
        extra = input("Confirmacao extra para perfil avancado/personalizado? [sim/nao]: ").strip()
    simulate = input("Se uma ferramenta estiver ausente, usar simulacao identificada? [sim/nao] [nao]: ").strip() or "nao"
    result = context.module_manager.execute(
        "smart_scan",
        ModuleExecutionContext(
            application=context,
            parameters={
                "targets": [item.strip() for item in targets.split(",") if item.strip()],
                "profile": profile,
                "authorized": authorization,
                "extra_confirmed": extra,
                "simulate": simulate,
            },
        ),
    )
    renderer.print_smart_scan_result(result.to_dict())


def _print_scanner_availability(context: Any, renderer: TerminalRenderer, binaries: tuple[str, ...]) -> None:
    """Show whether an interactive scan will use a real local scanner binary."""
    scanner = context.scanner_service
    available = [binary for binary in binaries if scanner and scanner.is_installed(binary)]
    missing = [binary for binary in binaries if binary not in available]
    if not missing:
        renderer.print_panel(
            "Modo de execucao",
            [f"{', '.join(binary.title() for binary in available)} detectado(s): a execucao usara a ferramenta real."],
            style="green",
        )
        return
    renderer.print_panel(
        "Modo de execucao",
        [
            f"Ausente: {', '.join(binary.title() for binary in missing)}.",
            "Para instalar, abra Menu 9 > 3 (Instalador assistido) ou execute: python3 dataspectre.py setup wizard --install.",
            "Sem instalacao, escolha 'sim' apenas se quiser dados ficticios claramente marcados.",
        ],
        style="yellow",
    )


def _interactive_inventory(context: Any, renderer: TerminalRenderer) -> None:
    renderer.print_panel(
        "ASSET INVENTORY",
        [
            "Normaliza inventarios fornecidos pelo operador.",
            "Informe um arquivo JSON local ou uma lista de IPs, hostnames ou nomes de ativos separados por virgula.",
            'Exemplo manual: 192.168.1.10, servidor.interno, notebook-lab.',
            'Exemplo de arquivo: {"assets":[{"name":"servidor","address":"192.168.1.10"}]}.',
            "Nenhuma coleta externa e executada por este modulo.",
        ],
        style="green",
    )
    input_file = input("Arquivo JSON local (Enter para informar ativos manualmente): ").strip()
    parameters: dict[str, Any]
    if input_file:
        parameters = {"input_file": input_file, "source": "interactive-file"}
    else:
        assets = _required_input(
            "Ativos separados por virgula: ",
            "Informe ao menos um ativo ou volte para informar um arquivo JSON valido.",
        )
        parameters = {"assets": assets, "source": "interactive-manual"}
    result = context.module_manager.execute(
        "asset_inventory",
        ModuleExecutionContext(application=context, parameters=parameters),
    )
    renderer.print_json(result.to_dict())


def _interactive_system_health(context: Any, renderer: TerminalRenderer) -> None:
    renderer.print_panel(
        "Diagnostico local do sistema",
        [
            "Coleta versao do Python, sistema operacional, uso de recursos e estado da aplicacao local.",
            "Nao acessa redes externas, nao altera configuracoes e nao exige nenhum dado de entrada.",
        ],
        style="green",
    )
    result = context.module_manager.execute(
        "system_health",
        ModuleExecutionContext(application=context, parameters={}),
    )
    renderer.print_json(result.to_dict())


def _interactive_project_summary(context: Any, renderer: TerminalRenderer) -> None:
    renderer.print_panel(
        "Resumo de projetos",
        [
            "Use Enter para um resumo de todos os projetos ou informe um ID existente para ver um unico projeto.",
            "Para encontrar IDs, volte ao menu e use o atalho 'p' ou 'projects'.",
        ],
        style="cyan",
    )
    project_id = input("ID do projeto (Enter para resumo geral): ").strip() or None
    result = context.module_manager.execute(
        "project_summary",
        ModuleExecutionContext(
            application=context,
            parameters={"project_id": project_id} if project_id else {},
            project_id=project_id,
        ),
    )
    renderer.print_json(result.to_dict())

def _command_name(args: Any) -> str:
    parts = [args.command or "interactive"]
    for attribute in (
        "config_command",
        "projects_command",
        "sessions_command",
        "modules_command",
        "scan_command",
        "reports_command",
        "plugins_command",
        "logs_command",
        "maintenance_command",
        "setup_command",
        "baseline_command",
    ):
        value = getattr(args, attribute, None)
        if value:
            parts.append(value)
    return "cli." + ".".join(parts)


def _confirm(question: str, assume_yes: bool = False) -> bool:
    if assume_yes:
        print(f"{question} [sim]")
        return True
    answer = input(f"{question} [sim/nao]: ").strip().lower()
    return answer in {"s", "sim", "y", "yes"}


def _format_command_result(result: dict[str, Any]) -> str:
    command = " ".join(result.get("command") or ["acao-manual"])
    status = result.get("return_code")
    if status == 0:
        return success(f"Comando concluido: {command}")
    details = result.get("stderr") or result.get("stdout") or "Falha sem detalhes."
    return warning(f"Comando requer atencao ({status}): {command} | {details}")


def _record_history(
    context: Any | None,
    function_name: str,
    result: str,
    details: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    if context and context.history_service:
        context.history_service.record_action(
            function_name=function_name,
            result=result,
            details=details,
            error=error_message,
        )


def _record_cli_error(
    context: Any | None,
    command_name: str,
    exc: BaseException,
    details: dict[str, Any] | None = None,
) -> None:
    payload = {
        "command": command_name,
        "error_type": type(exc).__name__,
        "error": str(exc),
    }
    if details:
        payload.update(details)
    if context and context.log_service:
        context.log_service.record_event(
            component="cli",
            level="ERROR",
            message=f"Command failed: {command_name}",
            details=payload,
        )
    _record_history(
        context,
        command_name,
        result="error",
        details={"command": command_name},
        error_message=str(exc),
    )


def _parse_params(values: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for item in values:
        if "=" not in item:
            raise ValidationError(f"Invalid parameter '{item}'. Use key=value.")
        key, value = item.split("=", 1)
        parsed[key] = _parse_value(value)
    return parsed


def _parse_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _parse_json(value: str) -> dict[str, Any]:
    parsed = _parse_value(value)
    if not isinstance(parsed, dict):
        raise ValidationError("Report data must be a JSON object.")
    return parsed


def _read_json_file(path_value: str) -> dict[str, Any]:
    path = Path(path_value)
    if not path.exists():
        raise ValidationError(f"JSON file not found: {path_value}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON file: {path_value}") from exc
    if not isinstance(payload, dict):
        raise ValidationError("Baseline data file must contain a JSON object.")
    return payload


def _read_lines_file(path_value: str) -> list[str]:
    path = Path(path_value)
    if not path.exists():
        raise ValidationError(f"Target file not found: {path_value}")
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        raise ValidationError(f"Target file is empty: {path_value}")
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
