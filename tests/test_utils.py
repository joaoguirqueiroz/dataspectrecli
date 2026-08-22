from __future__ import annotations

import json
import os

import pytest

from cli.messages import error, success, warning
from cli.interface import TerminalRenderer
from cli.tables import format_table
from services.history_service import HistoryService
from services.storage import append_jsonl, ensure_dir, read_json, write_json


def test_storage_helpers_write_read_and_append(tmp_path):
    directory = ensure_dir(tmp_path / "nested")
    json_path = directory / "payload.json"
    jsonl_path = directory / "events.jsonl"

    write_json(json_path, {"b": 2, "a": 1})
    append_jsonl(jsonl_path, {"event": "ok"})

    assert read_json(json_path) == {"a": 1, "b": 2}
    assert json.loads(jsonl_path.read_text(encoding="utf-8").strip()) == {"event": "ok"}
    assert read_json(directory / "missing.json", default={"fallback": True}) == {"fallback": True}


def test_write_json_cleans_temp_file_when_replace_fails(tmp_path, monkeypatch):
    directory = ensure_dir(tmp_path / "nested")

    def fail_replace(source, destination):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError):
        write_json(directory / "payload.json", {"a": 1})

    assert not list(directory.glob(".payload.json.*.tmp"))


def test_format_table_empty_and_populated():
    assert format_table([], ["id"]) == "Nenhum registro encontrado."

    table = format_table([{"id": "a", "name": "Alpha"}], ["id", "name"])

    assert "id" in table
    assert "Alpha" in table
    assert "-+-" in table


def test_format_table_stacks_records_in_narrow_terminals():
    table = format_table(
        [{"id": "asset-1", "name": "Servidor de laboratório", "status": "ativo", "owner": "equipe"}],
        ["id", "name", "status", "owner"],
        max_width=24,
    )

    assert "id: asset-1" in table
    assert "name:" in table
    assert "status:" in table
    assert "owner:" in table


def test_cli_message_helpers():
    assert success("done") == "[OK] done"
    assert warning("check") == "[WARN] check"
    assert error("bad") == "[ERROR] bad"


def test_terminal_renderer_modules_empty_message(capsys):
    TerminalRenderer().print_modules([])
    captured = capsys.readouterr()

    assert "Nenhum modulo carregado" in captured.out


def test_dashboard_banner_uses_brand_name_and_inline_metrics():
    renderer = TerminalRenderer(width=118)
    banner = renderer.dashboard_banner(
        {
            "application": "DataSpectre CLI",
            "version": "2.0.2",
            "modules": 6,
            "plugins": 1,
            "projects": 0,
            "health": {"os": "Linux", "python_version": "3.13", "local_ip": "10.0.2.15"},
        }
    )

    assert "DATASPECTRECLI" in banner
    assert ".:'##/" not in banner
    assert "[ SISTEMA: Linux ] [ PYTHON: 3.13 ]" in banner
    assert "[ MODULOS: 6 ] [ PLUGINS: 1 ] [ PROJETOS: 0 ] [ IP LOCAL: 10.0.2.15 ]" in banner


def test_history_service_records_result_error_and_function(tmp_path):
    service = HistoryService(tmp_path / "history")

    service.record_action(
        "cli.modules.run",
        result="error",
        details={"module_id": "missing"},
        error="Module missing",
    )

    record = service.read_recent(1)[0]
    assert record["function"] == "cli.modules.run"
    assert record["result"] == "error"
    assert record["error"] == "Module missing"
    assert record["details"]["module_id"] == "missing"
