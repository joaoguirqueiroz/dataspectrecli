from __future__ import annotations

import runpy

import pytest

from cli.app import main
from scripts import smoke_run


def test_entrypoint_module_exports_cli_main():
    import main as entrypoint

    assert entrypoint.main is main


def test_dataspectre_entrypoint_module_exports_cli_main():
    import dataspectre as entrypoint

    assert entrypoint.main is main


def test_smoke_status_modules_plugins_and_reports(runtime_root, capsys):
    assert main(["--root", str(runtime_root), "status"]) == 0
    assert main(["--root", str(runtime_root), "modules", "list"]) == 0
    assert main(["--root", str(runtime_root), "plugins", "list"]) == 0
    assert main(["--root", str(runtime_root), "reports", "list"]) == 0
    captured = capsys.readouterr()

    assert "DataSpectre CLI" in captured.out
    assert "asset_inventory" in captured.out
    assert "example_plugin" in captured.out


def test_smoke_run_script_accepts_runtime_root(runtime_root, capsys):
    exit_code = smoke_run.main(runtime_root)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "DataSpectre CLI" in captured.out


def test_main_entrypoint_exits_with_cli_status(runtime_root, monkeypatch):
    monkeypatch.setattr("sys.argv", ["main.py", "--root", str(runtime_root), "status"])

    with pytest.raises(SystemExit) as exc:
        runpy.run_path("main.py", run_name="__main__")

    assert exc.value.code == 0


def test_dataspectre_entrypoint_exits_with_cli_status(runtime_root, monkeypatch):
    monkeypatch.setattr("sys.argv", ["dataspectre.py", "--root", str(runtime_root), "status"])

    with pytest.raises(SystemExit) as exc:
        runpy.run_path("dataspectre.py", run_name="__main__")

    assert exc.value.code == 0


def test_cli_app_module_entrypoint_exits_with_status(runtime_root, monkeypatch):
    monkeypatch.setattr("sys.argv", ["cli/app.py", "--root", str(runtime_root), "status"])

    with pytest.raises(SystemExit) as exc:
        runpy.run_path("cli/app.py", run_name="__main__")

    assert exc.value.code == 0


def test_smoke_script_entrypoint_uses_environment_root(runtime_root, monkeypatch):
    monkeypatch.setattr("sys.argv", ["scripts/smoke_run.py"])
    monkeypatch.setenv("DATASPECTRE_ROOT", str(runtime_root))

    with pytest.raises(SystemExit) as exc:
        runpy.run_path("scripts/smoke_run.py", run_name="__main__")

    assert exc.value.code == 0
