from __future__ import annotations

import json

import pytest

from app.application import SentinelScanApplication
from app.bootstrap import Bootstrapper
from app.lifecycle import managed_application
from core.exceptions import BootstrapError
from core.module import ModuleExecutionContext


def test_full_project_session_module_report_audit_flow(runtime_root):
    application = SentinelScanApplication(runtime_root)
    try:
        context = application.initialize()
        project = context.project_service.create_project("Fluxo Integrado")
        session = context.session_service.start_session(project.id)

        result = context.module_manager.execute(
            "asset_inventory",
            ModuleExecutionContext(
                application=context,
                parameters={"assets": [{"name": "host", "type": "server"}]},
                project_id=project.id,
                session_id=session.id,
            ),
        )
        context.session_service.append_event(
            project.id,
            session.id,
            {"type": "module_execution", "module_id": "asset_inventory", "success": result.success},
        )
        report = context.report_service.generate_report(
            "Fluxo Integrado",
            result.to_dict(),
            project_id=project.id,
            session_id=session.id,
        )
        context.session_service.end_session(project.id, session.id)

        assert result.success is True
        assert (runtime_root / report.path).exists()
        assert context.project_service.stats(project.id)["reports"] == 1
        assert context.log_service.tail_audit(5)
    finally:
        application.shutdown()


def test_application_session_summary_tracks_modules_reports_and_errors(runtime_root):
    application = SentinelScanApplication(runtime_root)
    try:
        context = application.initialize()
        context.module_manager.execute(
            "system_health",
            ModuleExecutionContext(application=context, parameters={}),
        )
        context.module_manager.execute(
            "asset_inventory",
            ModuleExecutionContext(application=context, parameters={"assets": {"bad": "shape"}}),
        )
        context.report_service.generate_report("Resumo", {"success": True, "data": {}})
        summary = application.session_summary()

        assert summary["modules_used"] == 2
        assert set(summary["module_ids"]) == {"asset_inventory", "system_health"}
        assert summary["reports_created"] == 1
        assert summary["errors_found"] >= 1
    finally:
        application.shutdown()


def test_managed_application_initializes_and_shutdowns(runtime_root):
    with managed_application(runtime_root) as context:
        assert context.module_manager.list_modules()

    audit_lines = (runtime_root / "logs" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert any("shutdown completed" in line for line in audit_lines)


def test_application_status_reuses_context(app):
    first_context = app.initialize()
    status = app.status()
    second_context = app.initialize()

    assert first_context is second_context
    assert status["modules"] >= 3


def test_application_shutdown_without_initialize_is_noop(runtime_root):
    application = SentinelScanApplication(runtime_root)

    application.shutdown()

    assert application.context is None


def test_bootstrap_creates_required_runtime_directories(runtime_root):
    context = Bootstrapper(runtime_root).bootstrap()

    assert context.root_path == runtime_root.resolve()
    for dirname in ("logs", "reports", "cache", "data", "backups"):
        assert (runtime_root / dirname).exists()


def test_bootstrap_rejects_old_python(runtime_root, monkeypatch):
    monkeypatch.setattr("app.bootstrap.sys.version_info", (3, 9, 0))

    with pytest.raises(BootstrapError):
        Bootstrapper(runtime_root)._verify_python()


def test_audit_log_contains_structured_json_after_bootstrap(runtime_root):
    context = Bootstrapper(runtime_root).bootstrap()
    context.log_service.record_event("tests", "INFO", "structured")

    lines = (runtime_root / "logs" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[-1])
    assert payload["message"] == "structured"
