from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import cli.app as cli_app
from cli.app import _parse_json, _parse_params, _parse_value, _read_lines_file, main
from cli.app import _resolve_root
from core.exceptions import ValidationError


def run_cli(capsys, runtime_root, *args):
    exit_code = main(["--root", str(runtime_root), *args])
    captured = capsys.readouterr()
    return exit_code, captured


def test_cli_status_initializes_application(runtime_root, capsys):
    exit_code, captured = run_cli(capsys, runtime_root, "status")

    assert exit_code == 0
    assert "DataSpectre CLI" in captured.out
    assert "MODULOS:" in captured.out
    assert "SISTEMA:" in captured.out


def test_cli_config_show_get_set_and_reset(runtime_root, capsys):
    assert run_cli(capsys, runtime_root, "config", "set", "ui.theme", '"light"')[0] == 0
    exit_code, captured = run_cli(capsys, runtime_root, "config", "get", "ui.theme")
    assert exit_code == 0
    assert "light" in captured.out

    assert run_cli(capsys, runtime_root, "config", "show")[0] == 0
    assert run_cli(capsys, runtime_root, "config", "reset")[0] == 0


def test_cli_project_and_session_flow(runtime_root, capsys):
    exit_code, captured = run_cli(
        capsys,
        runtime_root,
        "projects",
        "create",
        "Projeto CLI",
        "--description",
        "Fluxo funcional",
    )
    project = json.loads(captured.out)

    assert exit_code == 0
    assert run_cli(capsys, runtime_root, "projects", "show", project["id"])[0] == 0
    assert run_cli(capsys, runtime_root, "projects", "list")[0] == 0

    exit_code, captured = run_cli(capsys, runtime_root, "sessions", "start", project["id"])
    session = json.loads(captured.out)

    assert exit_code == 0
    assert run_cli(capsys, runtime_root, "sessions", "list", project["id"])[0] == 0
    assert run_cli(capsys, runtime_root, "sessions", "end", project["id"], session["id"])[0] == 0
    assert run_cli(capsys, runtime_root, "projects", "archive", project["id"])[0] == 0


def test_cli_module_run_updates_session_when_project_and_session_are_provided(runtime_root, capsys):
    exit_code, captured = run_cli(capsys, runtime_root, "projects", "create", "Projeto Modulo Sessao")
    project = json.loads(captured.out)
    exit_code, captured = run_cli(capsys, runtime_root, "sessions", "start", project["id"])
    session = json.loads(captured.out)

    exit_code, captured = run_cli(
        capsys,
        runtime_root,
        "modules",
        "run",
        "system_health",
        "--project",
        project["id"],
        "--session",
        session["id"],
    )

    assert exit_code == 0
    assert '"module_id": "system_health"' in captured.out
    _, captured = run_cli(capsys, runtime_root, "sessions", "list", project["id"])
    assert session["id"] in captured.out


def test_cli_module_run_and_report_generation(runtime_root, capsys):
    exit_code, captured = run_cli(
        capsys,
        runtime_root,
        "modules",
        "run",
        "asset_inventory",
        "--param",
        "assets=host-a,host-b",
        "--report",
    )

    assert exit_code == 0
    assert '"total_assets": 2' in captured.out
    assert "[OK] Report generated" in captured.out
    assert run_cli(capsys, runtime_root, "reports", "list")[0] == 0


def test_cli_reports_generate_json(runtime_root, capsys):
    exit_code, captured = run_cli(
        capsys,
        runtime_root,
        "reports",
        "generate",
        "--title",
        "Manual",
        "--format",
        "json",
        "--data",
        '{"status":"ok"}',
    )

    assert exit_code == 0
    assert json.loads(captured.out)["format"] == "json"


def test_cli_reports_generate_json_from_data_file(runtime_root, capsys):
    data_file = runtime_root / "examples" / "manual_report.json"
    data_file.write_text('{"status":"ok"}', encoding="utf-8")

    exit_code, captured = run_cli(
        capsys,
        runtime_root,
        "reports",
        "generate",
        "--title",
        "Manual file",
        "--format",
        "json",
        "--data-file",
        str(data_file),
    )

    record = json.loads(captured.out)
    assert exit_code == 0
    assert record["format"] == "json"
    assert (runtime_root / record["path"]).exists()


def test_cli_reports_generate_missing_data_file_is_safe(runtime_root, capsys):
    exit_code, captured = run_cli(
        capsys,
        runtime_root,
        "reports",
        "generate",
        "--title",
        "Missing file",
        "--format",
        "json",
        "--data-file",
        str(runtime_root / "examples" / "missing.json"),
    )

    assert exit_code == 1
    assert "JSON file not found" in captured.err


def test_cli_reports_generate_html(runtime_root, capsys):
    exit_code, captured = run_cli(
        capsys,
        runtime_root,
        "reports",
        "generate",
        "--title",
        "Manual HTML",
        "--format",
        "html",
        "--data",
        '{"status":"ok"}',
    )

    record = json.loads(captured.out)
    assert exit_code == 0
    assert record["format"] == "html"
    assert (runtime_root / record["path"]).suffix == ".html"


def test_cli_help_command_shows_navigation(runtime_root, capsys):
    exit_code, captured = run_cli(capsys, runtime_root, "help")

    assert exit_code == 0
    assert "DATASPECTRE // HELP" in captured.out
    assert "modules list" in captured.out
    assert "scan nmap" in captured.out
    assert "scan nuclei" in captured.out
    assert "scan smart" in captured.out
    assert "baseline compare" in captured.out
    assert "setup check" in captured.out
    assert "setup wizard" in captured.out
    assert "maintenance clean-temp" in captured.out


def test_cli_setup_check_generates_setup_reports(runtime_root, capsys):
    exit_code, captured = run_cli(capsys, runtime_root, "setup", "check")

    assert exit_code == 0
    assert "ENVIRONMENT CHECK" in captured.out
    assert (runtime_root / "reports" / "setup" / "setup_report.txt").exists()
    assert (runtime_root / "reports" / "setup" / "setup_report.json").exists()


def test_cli_setup_tools_shows_nmap_and_nuclei(runtime_root, capsys):
    exit_code, captured = run_cli(capsys, runtime_root, "setup", "tools")

    assert exit_code == 0
    assert "Nmap" in captured.out
    assert "Nuclei" in captured.out


def test_cli_setup_wizard_check_mode(runtime_root, capsys):
    exit_code, captured = run_cli(capsys, runtime_root, "setup", "wizard")

    assert exit_code == 0
    assert "Instalador assistido" in captured.out
    assert "Nenhuma instalacao foi executada" in captured.out


def test_cli_modules_list_shows_nmap_and_nuclei(runtime_root, capsys):
    exit_code, captured = run_cli(capsys, runtime_root, "modules", "list")

    assert exit_code == 0
    assert "nmap_scan" in captured.out
    assert "nuclei_scan" in captured.out
    assert "MODULOS CARREGADOS" in captured.out


def test_cli_scan_nmap_requires_authorization(runtime_root, capsys):
    exit_code, captured = run_cli(capsys, runtime_root, "scan", "nmap", "127.0.0.1")

    assert exit_code == 0
    assert "RESULTADO // nmap_scan" in captured.out
    assert "cancelled" in captured.out
    assert "Execucao bloqueada" in captured.out


def test_cli_scan_nuclei_requires_authorization(runtime_root, capsys):
    exit_code, captured = run_cli(capsys, runtime_root, "scan", "nuclei", "http://localhost")

    assert exit_code == 0
    assert "RESULTADO // nuclei_scan" in captured.out
    assert "cancelled" in captured.out
    assert "Execucao bloqueada" in captured.out


def test_cli_scan_nuclei_accepts_target_file_in_simulation(runtime_root, capsys, monkeypatch):
    targets_file = runtime_root / "examples" / "nuclei-targets.txt"
    targets_file.write_text(
        "# authorized local targets\nhttp://localhost\nhttp://127.0.0.1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "services.scanner_service.ScannerService.is_installed",
        lambda self, binary: False,
    )

    exit_code, captured = run_cli(
        capsys,
        runtime_root,
        "scan",
        "nuclei",
        "--target-file",
        str(targets_file),
        "--authorize",
        "--simulate",
    )

    assert exit_code == 0
    assert "Resultado simulado" in captured.out
    assert "simulated" in captured.out
    assert (runtime_root / "reports" / "nuclei").exists()


def test_cli_scan_smart_requires_authorization(runtime_root, capsys):
    exit_code, captured = run_cli(capsys, runtime_root, "scan", "smart", "127.0.0.1")

    assert exit_code == 0
    assert "SMART SCAN" in captured.out
    assert "cancelled" in captured.out
    assert "Execucao bloqueada" in captured.out


def test_cli_baseline_create_and_compare(runtime_root, capsys):
    payload = {
        "correlation": {
            "hosts": [
                {
                    "host": "127.0.0.1",
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
            ],
            "findings": [],
        }
    }
    data_file = runtime_root / "examples" / "baseline_payload.json"
    data_file.write_text(json.dumps(payload), encoding="utf-8")

    exit_code, captured = run_cli(capsys, runtime_root, "baseline", "create", "lab", "--data", str(data_file))
    assert exit_code == 0
    assert '"name": "lab"' in captured.out

    payload["correlation"]["hosts"][0]["ports"].append(
        {"port": "443", "protocol": "tcp", "state": "open", "service": "https", "version": "nginx 1.25"}
    )
    data_file.write_text(json.dumps(payload), encoding="utf-8")
    exit_code, captured = run_cli(capsys, runtime_root, "baseline", "compare", "lab", "--data", str(data_file))

    assert exit_code == 0
    assert "BASELINE // COMPARE" in captured.out
    assert "changed" in captured.out


def test_cli_baseline_accepts_utf8_bom_json(runtime_root, capsys):
    data_file = runtime_root / "examples" / "baseline_bom.json"
    data_file.write_text(
        '\ufeff{"correlation":{"hosts":[],"findings":[]}}',
        encoding="utf-8",
    )

    exit_code, captured = run_cli(capsys, runtime_root, "baseline", "create", "bom", "--data", str(data_file))

    assert exit_code == 0
    assert '"name": "bom"' in captured.out


def test_cli_maintenance_clean_temp_preview_and_confirm(runtime_root, capsys):
    cache_file = runtime_root / "cache" / "discard.tmp"
    cache_file.write_text("temporary", encoding="utf-8")
    report_file = runtime_root / "reports" / "keep.txt"
    report_file.write_text("important", encoding="utf-8")

    exit_code, captured = run_cli(capsys, runtime_root, "maintenance", "clean-temp")

    assert exit_code == 0
    assert "Preview only" in captured.out
    assert cache_file.exists()
    assert report_file.exists()

    exit_code, captured = run_cli(capsys, runtime_root, "maintenance", "clean-temp", "--yes")

    assert exit_code == 0
    assert "Temporary files cleaned safely" in captured.out
    assert not cache_file.exists()
    assert report_file.exists()


def test_cli_module_report_format_override(runtime_root, capsys):
    exit_code, captured = run_cli(
        capsys,
        runtime_root,
        "modules",
        "run",
        "system_health",
        "--report",
        "--report-format",
        "txt",
    )

    assert exit_code == 0
    assert ".txt" in captured.out


def test_cli_plugins_and_logs(runtime_root, capsys):
    assert run_cli(capsys, runtime_root, "plugins", "list")[0] == 0
    exit_code, captured = run_cli(capsys, runtime_root, "logs", "audit", "--limit", "5")

    assert exit_code == 0
    assert "application.initialized" in captured.out or "shutdown completed" in captured.out


def test_cli_invalid_module_returns_error(runtime_root, capsys):
    exit_code, captured = run_cli(capsys, runtime_root, "modules", "run", "missing")

    assert exit_code == 1
    assert "[ERROR]" in captured.err


def test_cli_unknown_command_branch_prints_help(runtime_root, capsys, monkeypatch):
    class FakeParser:
        def __init__(self):
            self.help_printed = False

        def parse_args(self, argv):
            return SimpleNamespace(root=str(runtime_root), command="unknown")

        def print_help(self):
            self.help_printed = True
            print("help text")

    fake_parser = FakeParser()
    monkeypatch.setattr(cli_app, "build_parser", lambda: fake_parser)

    exit_code = cli_app.main(["unknown"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert fake_parser.help_printed is True
    assert "help text" in captured.out


def test_cli_invalid_param_returns_error(runtime_root, capsys):
    exit_code, captured = run_cli(
        capsys,
        runtime_root,
        "modules",
        "run",
        "asset_inventory",
        "--param",
        "invalid",
    )

    assert exit_code == 1
    assert "key=value" in captured.err


def test_cli_permission_failure_is_safe(runtime_root, capsys):
    run_cli(capsys, runtime_root, "config", "set", "security.active_profile", '"viewer"')

    exit_code, captured = run_cli(capsys, runtime_root, "projects", "create", "Nao Pode")

    assert exit_code == 1
    assert "cannot perform" in captured.err


def test_cli_uses_environment_root(runtime_root, capsys, monkeypatch):
    monkeypatch.setenv("SENTINELSCAN_ROOT", str(runtime_root))

    exit_code = main(["status"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert str(runtime_root) in captured.out


def test_cli_interactive_smoke_covers_menu_paths(runtime_root, capsys, monkeypatch):
    # modules, help, cleanup preview/cancel, invalid option, exit
    choices = iter(["10", "11", "12", "nao", "x", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(choices))

    exit_code = main(["--root", str(runtime_root), "interactive"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "DataSpectre Terminal iniciado" in captured.out
    assert "Opcao invalida" in captured.out
    assert "SESSION // FINAL REPORT" in captured.out
    assert "DATASPECTRE // HELP" in captured.out
    assert "asset_inventory" in captured.out
    assert "nmap_scan" in captured.out
    assert "nuclei_scan" in captured.out
    assert "SISTEMA:" in captured.out


def test_cli_interactive_menu_hides_removed_osint_workflow(runtime_root, capsys, monkeypatch):
    choices = iter(["0"])
    monkeypatch.setattr("builtins.input", lambda _: next(choices))

    exit_code = main(["--root", str(runtime_root), "interactive"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "OSINT" not in captured.out
    assert "Historico de operacoes" in captured.out
    assert "SESSION // FINAL REPORT" in captured.out


def test_cli_interactive_nmap_explains_authorized_target_and_simulates(runtime_root, capsys, monkeypatch):
    choices = iter(["1", "127.0.0.1", "", "", "sim", "sim", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(choices))
    monkeypatch.setattr(
        "services.scanner_service.ScannerService.is_installed",
        lambda self, binary: False,
    )

    exit_code = main(["--root", str(runtime_root), "interactive"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Alvo aceito: IP" in captured.out
    assert "Status: simulated" in captured.out


def test_cli_interactive_settings_submenu_can_return(runtime_root, capsys, monkeypatch):
    choices = iter(["9", "1", "0", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(choices))

    exit_code = main(["--root", str(runtime_root), "interactive"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Configuracoes" in captured.out
    assert '"app"' in captured.out


def test_cli_interactive_settings_environment_check(runtime_root, capsys, monkeypatch):
    choices = iter(["9", "2", "0", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(choices))

    exit_code = main(["--root", str(runtime_root), "interactive"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "ENVIRONMENT CHECK" in captured.out
    assert (runtime_root / "reports" / "setup" / "setup_report.json").exists()


def test_cli_interactive_report_center_lists_and_returns(runtime_root, capsys, monkeypatch):
    choices = iter(["6", "2", "Relatorio funcional", "{}", "0", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(choices))

    exit_code = main(["--root", str(runtime_root), "interactive"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Central de relatorios" in captured.out
    assert '"format": "json"' in captured.out


def test_cli_interactive_system_health(runtime_root, capsys, monkeypatch):
    choices = iter(["5", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(choices))

    exit_code = main(["--root", str(runtime_root), "interactive"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"module_id": "system_health"' in captured.out

def test_cli_parse_helpers():
    assert _parse_value("true") is True
    assert _parse_value("plain") == "plain"
    assert _parse_params(["a=1", "b=true"]) == {"a": 1, "b": True}
    assert _parse_json('{"a":1}') == {"a": 1}

    with pytest.raises(ValidationError):
        _parse_params(["bad"])
    with pytest.raises(ValidationError):
        _parse_json("[1,2]")


def test_cli_reads_target_files_safely(runtime_root):
    targets_file = runtime_root / "examples" / "targets.txt"
    targets_file.write_text("\ufeff# comentario\nhttp://localhost\n\nhttp://127.0.0.1\n", encoding="utf-8")

    assert _read_lines_file(str(targets_file)) == ["http://localhost", "http://127.0.0.1"]

    empty_file = runtime_root / "examples" / "empty-targets.txt"
    empty_file.write_text("# vazio\n\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="empty"):
        _read_lines_file(str(empty_file))
    with pytest.raises(ValidationError, match="not found"):
        _read_lines_file(str(runtime_root / "examples" / "missing-targets.txt"))


def test_resolve_root_defaults_to_project_root(monkeypatch):
    monkeypatch.delenv("DATASPECTRE_ROOT", raising=False)
    monkeypatch.delenv("SENTINELSCAN_ROOT", raising=False)

    assert _resolve_root(None).resolve() == Path(cli_app.__file__).resolve().parents[1]
