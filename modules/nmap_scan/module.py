"""Modulo de integracao Nmap autorizada."""

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


class NmapScanModule(BaseModule):
    metadata = ModuleMetadata(
        id="nmap_scan",
        name="Analise Nmap Autorizada",
        version="1.0.0",
        author="DataSpectre",
        description="Executa Nmap controlado apenas em alvos proprios, laboratorio ou explicitamente autorizados.",
        category="authorized-scanning",
    )

    def validate(self, parameters: dict[str, Any]) -> None:
        scanner = parameters.get("_scanner_service")
        target = parameters.get("target")
        if scanner is None:
            return
        scanner.validate_nmap_target(str(target or ""))
        profile = scanner.normalize_nmap_profile(parameters.get("profile") or "basic")
        if profile == "ports":
            scanner.validate_ports(parameters.get("ports"))
        if profile == "custom":
            scanner.validate_custom_nmap_flags(_list_value(parameters.get("custom_flags")))

    def execute(self, context: ModuleExecutionContext) -> ModuleResult:
        app = context.application
        scanner = app.scanner_service
        parameters = dict(context.parameters)
        parameters["_scanner_service"] = scanner
        self.validate(parameters)

        target = str(parameters["target"]).strip()
        profile = scanner.normalize_nmap_profile(parameters.get("profile") or "basic")
        if not _truthy(parameters.get("authorized")):
            return self._cancelled(app, target, profile, AUTHORIZATION_BLOCK_MESSAGE)
        if profile == "custom" and not _truthy(parameters.get("extra_confirmed")):
            return self._cancelled(app, target, profile, "Perfil personalizado exige confirmacao extra.")

        output_dir = app.report_service.tool_output_dir(context.project_id, context.session_id, "nmap")
        command = scanner.build_nmap_command(
            target=target,
            output_dir=output_dir,
            profile=profile,
            ports=parameters.get("ports"),
            custom_flags=_list_value(parameters.get("custom_flags")),
            timeout=parameters.get("timeout"),
        )
        try:
            execution = scanner.run_nmap(command, output_dir)
            payload = self._payload(
                target,
                profile,
                scanner.nmap_profile_info(profile),
                command.to_dict(),
                execution.to_dict(),
            )
            reports = self._generate_reports(app, payload, context)
            payload["reports"] = reports
            self._history(app, "success", payload)
            return self.result(
                success=True,
                status="completed",
                data=payload,
                messages=["Analise Nmap concluida.", f"Relatorios gerados: {len(reports)}"],
            )
        except ScannerToolUnavailable as exc:
            if _truthy(parameters.get("simulate")):
                execution = scanner.simulate_nmap(command, output_dir, target)
                payload = self._payload(
                    target,
                    profile,
                    scanner.nmap_profile_info(profile),
                    command.to_dict(),
                    execution.to_dict(),
                )
                payload["simulation_notice"] = _simulation_notice()
                reports = self._generate_reports(app, payload, context)
                payload["reports"] = reports
                self._history(app, "simulated", payload)
                return self.result(
                    True,
                    "simulated",
                    payload,
                    [_simulation_notice(), f"Relatorios gerados: {len(reports)}"],
                )
            return self._failure(app, "tool_missing", target, profile, exc)
        except ScannerTimeoutError as exc:
            return self._failure(app, "timeout", target, profile, exc)
        except ScannerParseError as exc:
            return self._failure(app, "parse_error", target, profile, exc)
        except ScannerExecutionError as exc:
            return self._failure(app, "execution_error", target, profile, exc)
        except ScannerError as exc:
            return self._failure(app, "scanner_error", target, profile, exc)

    def _payload(
        self,
        target: str,
        profile: str,
        profile_info: dict[str, str],
        command: dict[str, Any],
        execution: dict[str, Any],
    ) -> dict[str, Any]:
        hosts = execution.get("parsed", {}).get("hosts", [])
        return {
            "tool": "nmap",
            "target": target,
            "profile": profile,
            "profile_info": profile_info,
            "authorized_notice": AUTHORIZED_USE_NOTICE,
            "ethical_notice": ETHICAL_NOTICE,
            "progress": _progress_steps("nmap"),
            "command": command,
            "execution": execution,
            "summary": {
                "hosts": len(hosts),
                "open_ports": sum(
                    1
                    for host in hosts
                    for port in host.get("ports", [])
                    if port.get("state") == "open"
                ),
            },
        }

    def _generate_reports(
        self, app: Any, payload: dict[str, Any], context: ModuleExecutionContext
    ) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        for report_format in _report_formats(context.parameters.get("report_formats")):
            record = app.report_service.generate_report(
                title=f"Nmap autorizado: {payload['target']}",
                results={"success": True, "status": "completed", "data": payload},
                project_id=context.project_id,
                session_id=context.session_id,
                report_format=report_format,
                tool="nmap",
            )
            reports.append(record.to_dict())
        return reports

    def _cancelled(self, app: Any, target: str, profile: str, reason: str) -> ModuleResult:
        payload = {
            "tool": "nmap",
            "target": target,
            "profile": profile,
            "authorized": False,
            "ethical_notice": ETHICAL_NOTICE,
            "reason": reason,
        }
        self._history(app, "cancelled", payload)
        return self.result(True, "cancelled", payload, [reason, "Nmap nao foi executado."])

    def _failure(self, app: Any, status: str, target: str, profile: str, exc: Exception) -> ModuleResult:
        payload = {
            "tool": "nmap",
            "target": target,
            "profile": profile,
            "error": str(exc),
            "install": _nmap_install_instructions(),
            "simulation": "Use --simulate para gerar dados ficticios marcados como simulacao.",
        }
        if app.log_service:
            app.log_service.record_event(
                component="nmap_scan",
                level="ERROR",
                message=f"Nmap scan failed: {status}",
                details=payload,
            )
        self._history(app, "error", payload, str(exc))
        return self.result(False, status, payload, [str(exc), "Detalhes tecnicos foram salvos nos logs."])

    def _history(
        self, app: Any, result: str, details: dict[str, Any], error: str | None = None
    ) -> None:
        if app.history_service:
            app.history_service.record_action(
                "scanner.nmap",
                result=result,
                details=details,
                error=error,
            )


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


def _progress_steps(tool: str) -> list[str]:
    return [
        "Validando alvo",
        "Verificando autorizacao",
        "Verificando ferramenta instalada",
        "Preparando comando",
        f"Executando {tool.upper()}",
        "Interpretando resultado",
        "Gerando relatorio",
        "Finalizado",
    ]


def _simulation_notice() -> str:
    return (
        "Resultado simulado: estes dados sao ficticios e servem apenas para "
        "demonstracao da interface e dos relatorios."
    )


def _nmap_install_instructions() -> dict[str, str]:
    return {
        "debian_ubuntu_kali": "sudo apt update && sudo apt install -y nmap",
        "fedora": "sudo dnf install -y nmap",
        "arch_manjaro": "sudo pacman -S nmap",
    }


MODULE_CLASS = NmapScanModule
