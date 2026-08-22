from __future__ import annotations

from core.module import ModuleExecutionContext
from services.scanner_service import ScannerExecution


def test_scanner_modules_are_discovered(context):
    module_ids = {module["id"] for module in context.module_manager.list_modules()}

    assert {"nmap_scan", "nuclei_scan", "smart_scan"} <= module_ids


def test_nmap_module_cancelled_without_authorization(context):
    result = context.module_manager.execute(
        "nmap_scan",
        ModuleExecutionContext(
            application=context,
            parameters={"target": "127.0.0.1", "profile": "basic"},
        ),
    )

    assert result.success is True
    assert result.status == "cancelled"
    assert result.data["tool"] == "nmap"


def test_nmap_module_reports_missing_tool(context, monkeypatch):
    monkeypatch.setattr(context.scanner_service, "is_installed", lambda binary: False)

    result = context.module_manager.execute(
        "nmap_scan",
        ModuleExecutionContext(
            application=context,
            parameters={"target": "127.0.0.1", "authorized": True},
        ),
    )

    assert result.success is False
    assert result.status == "tool_missing"
    assert "Nmap" in result.messages[0]


def test_nmap_module_can_simulate_when_tool_is_missing(context, monkeypatch):
    monkeypatch.setattr(context.scanner_service, "is_installed", lambda binary: False)

    result = context.module_manager.execute(
        "nmap_scan",
        ModuleExecutionContext(
            application=context,
            parameters={"target": "127.0.0.1", "authorized": True, "simulate": True},
        ),
    )

    assert result.success is True
    assert result.status == "simulated"
    assert result.data["execution"]["simulated"] is True
    assert "Resultado simulado" in result.data["simulation_notice"]
    assert all("\\nmap\\" in report["path"] or "/nmap/" in report["path"] for report in result.data["reports"])


def test_nmap_module_success_generates_reports_and_history(context, monkeypatch):
    def fake_run(command, output_dir):
        return ScannerExecution(
            tool="nmap",
            profile=command.profile,
            command=command.args,
            return_code=0,
            output_files=command.output_files,
            parsed={
                "hosts": [
                    {
                        "host": "127.0.0.1",
                        "status": "up",
                        "ports": [{"port": "80", "protocol": "tcp", "state": "open"}],
                    }
                ]
            },
        )

    monkeypatch.setattr(context.scanner_service, "run_nmap", fake_run)

    result = context.module_manager.execute(
        "nmap_scan",
        ModuleExecutionContext(
            application=context,
            parameters={"target": "127.0.0.1", "authorized": True},
        ),
    )

    assert result.success is True
    assert result.data["summary"]["open_ports"] == 1
    assert len(result.data["reports"]) == 4
    assert all("\\nmap\\" in report["path"] or "/nmap/" in report["path"] for report in result.data["reports"])
    assert any(record["function"] == "scanner.nmap" for record in context.history_service.read_recent(10))


def test_nuclei_module_requires_extra_confirmation_for_high_profile(context):
    result = context.module_manager.execute(
        "nuclei_scan",
        ModuleExecutionContext(
            application=context,
            parameters={"target": "http://localhost", "profile": "high", "authorized": True},
        ),
    )

    assert result.success is True
    assert result.status == "cancelled"
    assert "confirmacao extra" in result.messages[0].lower()


def test_nuclei_module_success_generates_reports_and_history(context, monkeypatch):
    def fake_run(command, output_dir):
        return ScannerExecution(
            tool="nuclei",
            profile=command.profile,
            command=command.args,
            return_code=0,
            output_files=command.output_files,
            parsed={
                "findings": [
                    {
                        "target": "http://localhost",
                        "template": "test-template",
                        "name": "Test Finding",
                        "severity": "medium",
                        "endpoint": "http://localhost/login",
                        "timestamp": "2026-07-06T10:00:00Z",
                    }
                ]
            },
        )

    monkeypatch.setattr(context.scanner_service, "run_nuclei", fake_run)

    result = context.module_manager.execute(
        "nuclei_scan",
        ModuleExecutionContext(
            application=context,
            parameters={"target": "http://localhost", "authorized": True},
        ),
    )

    assert result.success is True
    assert result.data["summary"]["findings"] == 1
    assert result.data["summary"]["severities"] == {"medium": 1}
    assert len(result.data["reports"]) == 4
    assert all(
        "\\nuclei\\" in report["path"] or "/nuclei/" in report["path"]
        for report in result.data["reports"]
    )
    assert any(record["function"] == "scanner.nuclei" for record in context.history_service.read_recent(10))


def test_nuclei_module_can_simulate_when_tool_is_missing(context, monkeypatch):
    monkeypatch.setattr(context.scanner_service, "is_installed", lambda binary: False)

    result = context.module_manager.execute(
        "nuclei_scan",
        ModuleExecutionContext(
            application=context,
            parameters={"target": "http://localhost", "authorized": True, "simulate": True},
        ),
    )

    assert result.success is True
    assert result.status == "simulated"
    assert result.data["execution"]["simulated"] is True
    assert result.data["summary"]["findings"] == 1
    assert "Resultado simulado" in result.data["simulation_notice"]


def test_smart_scan_module_cancelled_without_authorization(context):
    result = context.module_manager.execute(
        "smart_scan",
        ModuleExecutionContext(
            application=context,
            parameters={"target": "127.0.0.1", "profile": "basic"},
        ),
    )

    assert result.success is True
    assert result.status == "cancelled"
    assert result.data["tool"] == "smart_scan"


def test_smart_scan_module_requires_extra_confirmation_for_advanced(context):
    result = context.module_manager.execute(
        "smart_scan",
        ModuleExecutionContext(
            application=context,
            parameters={"target": "127.0.0.1", "profile": "advanced", "authorized": True},
        ),
    )

    assert result.success is True
    assert result.status == "cancelled"
    assert "confirmacao extra" in result.messages[0].lower()


def test_smart_scan_module_success_correlates_and_generates_reports(context, monkeypatch):
    monkeypatch.setattr(context.scanner_service, "is_installed", lambda binary: True)

    def fake_nmap(command, output_dir):
        return ScannerExecution(
            tool="nmap",
            profile=command.profile,
            command=command.args,
            return_code=0,
            output_files=command.output_files,
            parsed={
                "hosts": [
                    {
                        "host": "127.0.0.1",
                        "ip": "127.0.0.1",
                        "hostnames": [{"name": "localhost", "type": "user"}],
                        "status": "up",
                        "ports": [
                            {
                                "port": "80",
                                "protocol": "tcp",
                                "state": "open",
                                "service": "http",
                                "version": "nginx 1.25",
                            }
                        ],
                    }
                ]
            },
        )

    def fake_nuclei(command, output_dir):
        return ScannerExecution(
            tool="nuclei",
            profile=command.profile,
            command=command.args,
            return_code=0,
            output_files=command.output_files,
            parsed={
                "findings": [
                    {
                        "target": "http://localhost:80",
                        "template": "exposure-test",
                        "name": "Exposed Panel",
                        "severity": "high",
                        "description": "Panel exposed",
                        "endpoint": "http://localhost:80/login",
                        "timestamp": "2026-07-06T10:00:00Z",
                    }
                ]
            },
        )

    monkeypatch.setattr(context.scanner_service, "run_nmap", fake_nmap)
    monkeypatch.setattr(context.scanner_service, "run_nuclei", fake_nuclei)

    result = context.module_manager.execute(
        "smart_scan",
        ModuleExecutionContext(
            application=context,
            parameters={"target": "127.0.0.1", "authorized": True},
        ),
    )

    assert result.success is True
    assert result.data["correlation"]["summary"]["web_endpoints"] == 1
    assert result.data["correlation"]["summary"]["findings"] == 1
    assert result.data["correlation"]["findings"][0]["risk"] == "Critico"
    assert len(result.data["reports"]) == 4
    assert all(
        "\\smart_scan\\" in report["path"] or "/smart_scan/" in report["path"]
        for report in result.data["reports"]
    )
    assert any(record["function"] == "scanner.smart" for record in context.history_service.read_recent(10))


def test_smart_scan_module_simulates_missing_tools_and_keeps_web_scope(context, monkeypatch):
    monkeypatch.setattr(context.scanner_service, "is_installed", lambda binary: False)

    result = context.module_manager.execute(
        "smart_scan",
        ModuleExecutionContext(
            application=context,
            parameters={"target": "127.0.0.1", "authorized": True, "simulate": True},
        ),
    )

    assert result.success is True
    assert result.status == "completed"
    assert result.data["nmap"]["executions"][0]["execution"]["simulated"] is True
    assert result.data["nuclei"]["execution"]["execution"]["simulated"] is True
    assert result.data["correlation"]["summary"]["web_endpoints"] >= 1
    assert all(
        "\\smart_scan\\" in report["path"] or "/smart_scan/" in report["path"]
        for report in result.data["reports"]
    )
