from __future__ import annotations

import pytest

from core.exceptions import ProjectError, SessionError


def test_session_start_get_list_and_close(context):
    project = context.project_service.create_project("Sessao")

    session = context.session_service.start_session(project.id, {"ui": {"theme": "dark"}})
    fetched = context.session_service.get_session(project.id, session.id)
    listed = context.session_service.list_sessions(project.id)
    closed = context.session_service.end_session(project.id, session.id)

    assert fetched.id == session.id
    assert listed[0].id == session.id
    assert closed.state == "finished"
    assert closed.ended_at is not None


def test_session_append_event_persists(context):
    project = context.project_service.create_project("Eventos")
    session = context.session_service.start_session(project.id)

    updated = context.session_service.append_event(
        project.id,
        session.id,
        {"type": "module_execution", "module_id": "system_health"},
    )

    assert updated.events[-1]["type"] == "module_execution"
    assert "timestamp" in updated.events[-1]


def test_session_end_is_idempotent(context):
    project = context.project_service.create_project("Idempotente")
    session = context.session_service.start_session(project.id)

    first = context.session_service.end_session(project.id, session.id)
    second = context.session_service.end_session(project.id, session.id, "error")

    assert second.ended_at == first.ended_at
    assert second.state == "finished"


def test_session_missing_session_raises(context):
    project = context.project_service.create_project("Missing Session")

    with pytest.raises(SessionError):
        context.session_service.get_session(project.id, "session-missing")


def test_session_missing_project_raises(context):
    with pytest.raises(ProjectError):
        context.session_service.start_session("missing-project")

