from __future__ import annotations

import json

import pytest

from core.exceptions import ReportError
from services.report_service import ReportRecord, ReportService


def test_report_service_generates_markdown(runtime_root, context):
    record = context.report_service.generate_report(
        "Markdown Report",
        {"success": True, "status": "ok", "data": {"items": 2}},
    )

    path = runtime_root / record.path
    assert path.exists()
    assert "# Markdown Report" in path.read_text(encoding="utf-8")
    assert record.format == "markdown"


def test_report_service_generates_json(runtime_root, context):
    record = context.report_service.generate_report(
        "JSON Report",
        {"success": True, "status": "ok", "data": {"items": 2}},
        report_format="json",
    )

    payload = json.loads((runtime_root / record.path).read_text(encoding="utf-8"))
    assert payload["metadata"]["title"] == "JSON Report"
    assert payload["executive_summary"]["items"] == 1


@pytest.mark.parametrize(
    ("report_format", "expected_suffix", "expected_text"),
    [
        ("txt", ".txt", "RESUMO EXECUTIVO"),
        ("csv", ".csv", "executive_summary"),
        ("html", ".html", "<h1>"),
    ],
)
def test_report_service_generates_export_formats(
    runtime_root, context, report_format, expected_suffix, expected_text
):
    record = context.report_service.generate_report(
        f"{report_format} Report",
        {"success": True, "status": "ok", "data": {"items": 2}},
        report_format=report_format,
    )

    path = runtime_root / record.path
    assert path.suffix == expected_suffix
    assert expected_text in path.read_text(encoding="utf-8")


def test_report_service_organizes_reports_by_project_date_and_session(runtime_root, context):
    project = context.project_service.create_project("Relatorios Organizados")
    session = context.session_service.start_session(project.id)

    record = context.report_service.generate_report(
        "Organizado",
        {"success": True, "status": "ok", "data": {}},
        project_id=project.id,
        session_id=session.id,
        report_format="html",
    )

    path = runtime_root / record.path
    assert project.id in record.path
    assert session.id in record.path
    assert path.exists()


def test_report_service_organizes_tool_reports(runtime_root, context):
    record = context.report_service.generate_report(
        "Nmap",
        {"success": True, "status": "ok", "data": {}},
        report_format="json",
        tool="nmap",
    )

    assert "nmap" in record.path
    assert record.path.startswith("reports\\nmap\\") or record.path.startswith("reports/nmap/")
    assert "nmap_" in record.path
    assert (runtime_root / record.path).exists()


def test_report_service_rejects_unsupported_format(context):
    with pytest.raises(ReportError):
        context.report_service.generate_report("Bad", {}, report_format="pdf")


def test_report_service_lists_persisted_reports(context):
    first = context.report_service.generate_report("A", {"data": {}})
    second = context.report_service.generate_report("B", {"data": {}})

    report_ids = [report.id for report in context.report_service.list_reports()]

    assert first.id in report_ids
    assert second.id in report_ids


def test_report_record_to_dict():
    record = ReportRecord(id="r1", title="Title", format="json", path="reports/r1.json")

    assert record.to_dict()["id"] == "r1"


def test_report_service_can_be_constructed_directly(runtime_root):
    service = ReportService(runtime_root, runtime_root / "custom_reports")

    record = service.generate_report("Direct", {"success": True, "data": {}})

    assert (runtime_root / record.path).exists()
