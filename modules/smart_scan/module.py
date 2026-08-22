"""Smart authorized Nmap + Nuclei workflow."""

from __future__ import annotations

from typing import Any

from core.exceptions import ValidationError
from core.module import BaseModule, ModuleExecutionContext, ModuleMetadata, ModuleResult
from services.scanner_service import (
    AUTHORIZATION_BLOCK_MESSAGE,
    AUTHORIZED_USE_NOTICE,
    ETHICAL_NOTICE,
    ScannerError,
    ScannerExecutionError,
    ScannerParseError,
    ScannerTimeoutError,
    ScannerToolUnavailable,
)


PROFILE_ALIASES = {
    "basic": "basic",
    "basico": "basic",
    "intermediate": "intermediate",
    "intermediario": "intermediate",
    "advanced": "advanced",
    "avancado": "advanced",
    "custom": "custom",
    "personalizado": "custom",
}


class SmartScanModule(BaseModule):
    metadata = ModuleMetadata(
        id="smart_scan",
        name="Smart Scan Nmap + Nuclei",
        version="1.0.0",
        author="DataSpectre",
        description="Correlaciona descoberta Nmap autorizada com validacao Nuclei direcionada.",
        category="authorized-scanning",
    )

    def validate(self, parameters: dict[str, Any]) -> None:
        scanner = parameters.get("_scanner_service")
        if scanner is None:
            return
        targets = _targets(parameters)
        for target in targets:
            scanner.validate_nmap_target(target)
        profile = _profile(parameters.get("profile"))
        if profile == "custom":
            if parameters.get("ports"):
                scanner.validate_ports(parameters.get("ports"))
            scanner.validate_custom_nmap_flags(_list_value(parameters.get("custom_flags")))
            scanner.validate_nuclei_templates(_list_value(parameters.get("templates")))
        scanner.validate_nuclei_tags(_list_value(parameters.get("tags")))
        scanner.validate_nuclei_severities(_list_value(parameters.get("severities")))

    def execute(self, context: ModuleExecutionContext) -> ModuleResult:
        app = context.application
        scanner = app.scanner_service
        smart = app.smart_scan_service
        parameters = dict(context.parameters)
        parameters["_scanner_service"] = scanner
        self.validate(parameters)

        targets = _targets(parameters)
        profile = _profile(parameters.get("profile"))
        if not _truthy(parameters.get("authorized")):
            return self._cancelled(app, targets, profile, AUTHORIZATION_BLOCK_MESSAGE)
        large_threshold = int(
            app.settings.get("scanners", {}).get("smart", {}).get("large_target_threshold", 10)
        )
        if (profile in {"advanced", "custom"} or len(targets) > large_threshold) and not _truthy(
            parameters.get("extra_confirmed")
        ):
            return self._cancelled(
                app,
                targets,
                profile,
                "Perfil avancado, personalizado ou lista grande exige confirmacao extra.",
            )

        output_dir = app.report_service.tool_output_dir(context.project_id, context.session_id, "smart_scan")
        all_hosts: list[dict[str, Any]] = []
        nmap_executions: list[dict[str, Any]] = []
        decisions: list[str] = []
        nuclei_execution: dict[str, Any] | None = None
        nuclei_findings: list[dict[str, Any]] = []
        try:
            for target in targets:
                nmap_command = scanner.build_nmap_command(
                    target=target,
                    output_dir=output_dir,
                    profile=_nmap_profile(profile),
                    ports=parameters.get("ports"),
                    custom_flags=_list_value(parameters.get("custom_flags")),
                    nse_profile=_nse_profile(profile, parameters),
                    nse_scripts=_list_value(parameters.get("nse_scripts")),
                    timeout=parameters.get("timeout"),
                )
                try:
                    nmap_result = scanner.run_nmap(nmap_command, output_dir)
                except ScannerToolUnavailable:
                    if not _truthy(parameters.get("simulate")):
                        raise
                    nmap_result = scanner.simulate_nmap(nmap_command, output_dir, target)
                    decisions.append(_simulation_notice())
                nmap_payload = nmap_result.to_dict()
                nmap_executions.append({"command": nmap_command.to_dict(), "execution": nmap_payload})
                all_hosts.extend(nmap_payload.get("parsed", {}).get("hosts", []))

            endpoints, endpoint_decisions = smart.select_web_endpoints(all_hosts)
            decisions.extend(endpoint_decisions)
            if endpoints and scanner.is_installed("nuclei"):
                nuclei_command = scanner.build_nuclei_command(
                    targets=[endpoint["url"] for endpoint in endpoints],
                    output_dir=output_dir,
                    profile=_nuclei_profile(profile),
                    templates=_list_value(parameters.get("templates")),
                    template_dirs=_list_value(parameters.get("template_dirs")),
                    tags=_list_value(parameters.get("tags")),
                    severities=_list_value(parameters.get("severities")),
                    timeout=parameters.get("timeout"),
                    concurrency=parameters.get("concurrency"),
                    rate_limit=parameters.get("rate_limit"),
                    max_targets=parameters.get("max_targets"),
                )
                nuclei_result = scanner.run_nuclei(nuclei_command, output_dir)
                nuclei_execution = {
                    "command": nuclei_command.to_dict(),
                    "execution": nuclei_result.to_dict(),
                }
                nuclei_findings = nuclei_result.parsed.get("findings", [])
            elif endpoints and _truthy(parameters.get("simulate")):
                nuclei_command = scanner.build_nuclei_command(
                    targets=[endpoint["url"] for endpoint in endpoints],
                    output_dir=output_dir,
                    profile=_nuclei_profile(profile),
                    templates=_list_value(parameters.get("templates")),
                    template_dirs=_list_value(parameters.get("template_dirs")),
                    tags=_list_value(parameters.get("tags")),
                    severities=_list_value(parameters.get("severities")),
                    timeout=parameters.get("timeout"),
                    concurrency=parameters.get("concurrency"),
                    rate_limit=parameters.get("rate_limit"),
                    max_targets=parameters.get("max_targets"),
                )
                nuclei_result = scanner.simulate_nuclei(
                    nuclei_command,
                    output_dir,
                    [endpoint["url"] for endpoint in endpoints],
                )
                nuclei_execution = {
                    "command": nuclei_command.to_dict(),
                    "execution": nuclei_result.to_dict(),
                }
                nuclei_findings = nuclei_result.parsed.get("findings", [])
                decisions.append(_simulation_notice())
            elif endpoints:
                decisions.append("Nuclei nao instalado; use --simulate para demonstrar a validacao sem ferramenta real.")
            else:
                decisions.append("Nenhum endpoint web candidato foi encontrado; Nuclei nao foi executado.")

            correlation = smart.correlate(all_hosts, nuclei_findings, endpoints, decisions)
            payload = {
                "tool": "smart_scan",
                "targets": targets,
                "profile": profile,
                "authorized_notice": AUTHORIZED_USE_NOTICE,
                "ethical_notice": ETHICAL_NOTICE,
                "progress": _progress_steps(),
                "nmap": {"executions": nmap_executions, "hosts": all_hosts},
                "nuclei": {"execution": nuclei_execution, "findings": nuclei_findings},
                "correlation": correlation,
                "templates": {
                    "templates": _list_value(parameters.get("templates")),
                    "template_dirs": _list_value(parameters.get("template_dirs")),
                    "tags": _list_value(parameters.get("tags")),
                    "severities": _list_value(parameters.get("severities")),
                },
            }
            baseline_name = parameters.get("baseline")
            if baseline_name:
                payload["baseline_compare"] = app.baseline_service.compare(str(baseline_name), payload)
            reports = self._generate_reports(app, payload, context)
            payload["reports"] = reports
            self._history(app, "success", payload)
            return self.result(
                True,
                "completed",
                payload,
                [
                    "Smart Scan concluido.",
                    f"Hosts: {correlation['summary']['hosts']}",
                    f"Endpoints web: {correlation['summary']['web_endpoints']}",
                    f"Achados: {correlation['summary']['findings']}",
                ],
            )
        except ScannerToolUnavailable as exc:
            return self._failure(app, "tool_missing", targets, profile, exc)
        except ScannerTimeoutError as exc:
            return self._failure(app, "timeout", targets, profile, exc)
        except ScannerParseError as exc:
            return self._failure(app, "parse_error", targets, profile, exc)
        except ScannerExecutionError as exc:
            return self._failure(app, "execution_error", targets, profile, exc)
        except ScannerError as exc:
            return self._failure(app, "scanner_error", targets, profile, exc)

    def _generate_reports(
        self, app: Any, payload: dict[str, Any], context: ModuleExecutionContext
    ) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        for report_format in _report_formats(context.parameters.get("report_formats")):
            record = app.report_service.generate_report(
                title="Smart Scan autorizado",
                results={"success": True, "status": "completed", "data": payload},
                project_id=context.project_id,
                session_id=context.session_id,
                report_format=report_format,
                tool="smart_scan",
            )
            reports.append(record.to_dict())
        return reports

    def _cancelled(self, app: Any, targets: list[str], profile: str, reason: str) -> ModuleResult:
        payload = {
            "tool": "smart_scan",
            "targets": targets,
            "profile": profile,
            "authorized": False,
            "ethical_notice": ETHICAL_NOTICE,
            "reason": reason,
        }
        self._history(app, "cancelled", payload)
        return self.result(True, "cancelled", payload, [reason, "Nmap e Nuclei nao foram executados."])

    def _failure(
        self, app: Any, status: str, targets: list[str], profile: str, exc: Exception
    ) -> ModuleResult:
        payload = {
            "tool": "smart_scan",
            "targets": targets,
            "profile": profile,
            "error": str(exc),
            "simulation": "Use --simulate para gerar dados ficticios marcados como simulacao.",
        }
        if app.log_service:
            app.log_service.record_event(
                component="smart_scan",
                level="ERROR",
                message=f"Smart scan failed: {status}",
                details=payload,
            )
        self._history(app, "error", payload, str(exc))
        return self.result(False, status, payload, [str(exc), "Detalhes tecnicos foram salvos nos logs."])

    def _history(
        self, app: Any, result: str, details: dict[str, Any], error: str | None = None
    ) -> None:
        if app.history_service:
            app.history_service.record_action(
                "scanner.smart",
                result=result,
                details=details,
                error=error,
            )


def _profile(value: Any) -> str:
    clean = str(value or "basic").strip().lower()
    if clean not in PROFILE_ALIASES:
        raise ValidationError(f"Unsupported smart scan profile: {value}.")
    return PROFILE_ALIASES[clean]


def _nmap_profile(profile: str) -> str:
    return "custom" if profile == "custom" else "services-scripts"


def _nuclei_profile(profile: str) -> str:
    if profile == "advanced":
        return "high"
    if profile == "intermediate":
        return "exposure"
    if profile == "custom":
        return "custom"
    return "basic"


def _nse_profile(profile: str, parameters: dict[str, Any]) -> str | None:
    if parameters.get("nse_profile"):
        return str(parameters.get("nse_profile"))
    if profile == "advanced":
        return "safe"
    if profile == "intermediate":
        return "version"
    return None


def _targets(parameters: dict[str, Any]) -> list[str]:
    raw = parameters.get("targets", parameters.get("target"))
    values = _list_value(raw)
    if not values:
        raise ValidationError("Smart scan target list cannot be empty.")
    return values


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "sim", "s", "confirmo"}


def _list_value(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _report_formats(value: Any) -> list[str]:
    formats = _list_value(value) or ["txt", "json", "csv", "html"]
    allowed = {"txt", "json", "csv", "html", "markdown"}
    invalid = [item for item in formats if item not in allowed]
    if invalid:
        raise ValidationError(f"Unsupported report format: {invalid[0]}")
    return formats


def _progress_steps() -> list[str]:
    return [
        "Validando alvo",
        "Verificando autorizacao",
        "Verificando Nmap",
        "Preparando comando Nmap",
        "Executando Nmap",
        "Interpretando XML do Nmap",
        "Identificando servicos web",
        "Executando Nuclei apenas em endpoints web",
        "Correlacionando resultados",
        "Gerando relatorio",
        "Finalizado",
    ]


def _simulation_notice() -> str:
    return (
        "Resultado simulado: estes dados sao ficticios e servem apenas para "
        "demonstracao da interface e dos relatorios."
    )


MODULE_CLASS = SmartScanModule
