from __future__ import annotations

import json

import pytest

from core.exceptions import ProjectError, ValidationError


def test_project_creation_persists_catalog_and_directories(context, runtime_root):
    project = context.project_service.create_project("Projeto Teste", "Descricao", "qa")

    project_path = runtime_root / project.path
    assert project_path.exists()
    assert (project_path / "sessions").exists()
    assert (project_path / "project.json").exists()
    assert project.owner == "qa"


def test_project_list_filters_archived(context):
    active = context.project_service.create_project("Ativo")
    archived = context.project_service.create_project("Arquivado")
    context.project_service.archive_project(archived.id)

    active_ids = {project.id for project in context.project_service.list_projects()}
    all_ids = {project.id for project in context.project_service.list_projects(include_archived=True)}

    assert active.id in active_ids
    assert archived.id not in active_ids
    assert archived.id in all_ids


def test_project_show_missing_raises(context):
    with pytest.raises(ProjectError):
        context.project_service.get_project("missing")


def test_project_empty_name_raises(context):
    with pytest.raises(ValidationError):
        context.project_service.create_project(" ")


def test_project_update_activity_writes_history(context, runtime_root):
    project = context.project_service.create_project("Historico")

    context.project_service.update_activity(project.id, {"event": "checked"})

    history_path = runtime_root / project.path / "history" / "activity.jsonl"
    payload = json.loads(history_path.read_text(encoding="utf-8").splitlines()[-1])
    assert payload["details"] == {"event": "checked"}


def test_project_stats_counts_sessions_and_reports(context):
    project = context.project_service.create_project("Stats")
    session = context.session_service.start_session(project.id)
    context.report_service.generate_report(
        "Stats Report",
        {"success": True, "data": {"items": 1}},
        project_id=project.id,
        session_id=session.id,
    )

    stats = context.project_service.stats(project.id)

    assert stats["sessions"] == 1
    assert stats["reports"] == 1

