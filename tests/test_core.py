from __future__ import annotations

from pathlib import Path

import pytest

from core.events import EventBus
from core.exceptions import PermissionDeniedError, ValidationError
from core.module import BaseModule, ModuleExecutionContext, ModuleMetadata, ModuleResult
from core.plugin import BasePlugin, PluginContext, PluginMetadata
from core.resources import ResourceMonitor
from core.security import PermissionManager
from core.validators import (
    ensure_relative_path,
    ensure_within_root,
    slugify,
    validate_non_empty,
    validate_slug,
)


class DemoModule(BaseModule):
    metadata = ModuleMetadata(
        id="demo_module",
        name="Demo",
        version="1.0.0",
        author="Tester",
        description="Demo module",
        category="tests",
    )


def test_event_bus_dispatches_specific_and_wildcard_handlers():
    bus = EventBus()
    received = []
    wildcard = []
    bus.subscribe("demo.event", lambda event: received.append(event))
    bus.subscribe("*", lambda event: wildcard.append(event))

    event = bus.publish("demo.event", "test", {"ok": True})

    assert event.payload == {"ok": True}
    assert received == [event]
    assert wildcard == [event]
    assert bus.history() == [event]
    assert bus.history(limit=1) == [event]


def test_module_result_finish_and_to_dict():
    result = ModuleResult(module_id="demo", success=True, status="ok").finish()

    payload = result.to_dict()
    assert payload["module_id"] == "demo"
    assert payload["success"] is True
    assert payload["finished_at"] is not None


def test_base_module_result_uses_metadata():
    result = DemoModule().result(True, "completed", {"items": 1}, ["done"])

    assert result.module_id == "demo_module"
    assert result.data == {"items": 1}
    assert result.messages == ["done"]


def test_base_module_execute_must_be_implemented(context):
    with pytest.raises(NotImplementedError):
        DemoModule().execute(ModuleExecutionContext(application=context))


def test_base_plugin_default_lifecycle_methods(context):
    plugin = BasePlugin()
    metadata = PluginMetadata(
        id="base_plugin",
        name="Base",
        version="1.0.0",
        author="Tester",
        description="Base plugin",
        category="tests",
    )

    assert plugin.initialize(PluginContext(application=context, metadata=metadata)) is None
    assert plugin.shutdown() is None


def test_permission_manager_allows_and_denies_profiles():
    permissions = PermissionManager("viewer")

    assert permissions.can("logs:read").allowed is True
    assert permissions.can("config:write").allowed is False
    with pytest.raises(PermissionDeniedError):
        permissions.require("config:write")


def test_resource_monitor_snapshot_includes_extra(runtime_root):
    snapshot = ResourceMonitor(runtime_root).snapshot({"modules": 3})

    assert snapshot["modules"] == 3
    assert snapshot["root_path"] == str(runtime_root)
    assert snapshot["uptime_seconds"] >= 0


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Projeto João", "projeto-joao"),
        ("--", "item"),
        ("A  B", "a-b"),
    ],
)
def test_slugify_normalizes_common_inputs(value, expected):
    assert slugify(value) == expected


def test_validators_accept_and_reject_expected_values(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    child = root / "child"
    child.mkdir()

    assert validate_slug("abc-123") == "abc-123"
    assert validate_non_empty(" value ", "field") == "value"
    assert ensure_relative_path("data/projects", "path") == Path("data/projects")
    assert ensure_within_root(root, child) == child.resolve()

    with pytest.raises(ValidationError):
        validate_slug("Invalid Slug")
    with pytest.raises(ValidationError):
        validate_non_empty(" ", "field")
    with pytest.raises(ValidationError):
        ensure_relative_path("../outside", "path")
    with pytest.raises(ValidationError):
        ensure_within_root(root, tmp_path / "outside")
