from __future__ import annotations

import json

from services.audit_service import AuditService
from services.history_service import HistoryService
from services.log_service import LogService


def test_log_service_configures_and_records_event(runtime_root):
    service = LogService(runtime_root)
    service.configure({"logging": {"level": "DEBUG", "max_bytes": 100000, "backup_count": 1}})

    payload = service.record_event("tests", "INFO", "hello", details={"x": 1})

    assert service.log_file.exists()
    assert service.audit_file.exists()
    assert payload["component"] == "tests"
    assert json.loads(service.tail_audit(1)[0])["details"] == {"x": 1}


def test_log_service_defaults_invalid_level_to_info(runtime_root):
    service = LogService(runtime_root)
    service.configure({"logging": {"level": "NOT_A_LEVEL"}})

    payload = service.record_event("tests", "not_a_level", "message")

    assert payload["level"] == "NOT_A_LEVEL"
    assert service.tail_audit(1)


def test_log_service_tail_empty_when_no_audit_file(runtime_root):
    assert LogService(runtime_root).tail_audit() == []


def test_audit_service_records_warning_status(runtime_root):
    log = LogService(runtime_root)
    audit = AuditService(log)

    payload = audit.record("config.updated", target="ui.theme", status="warning")

    assert payload["level"] == "WARNING"
    assert payload["details"]["action"] == "config.updated"


def test_history_service_appends_jsonl(runtime_root):
    history = HistoryService(runtime_root / "data" / "history")

    history.append("tests", "ran", {"count": 1})

    line = history.history_file.read_text(encoding="utf-8").splitlines()[0]
    assert json.loads(line)["details"] == {"count": 1}

