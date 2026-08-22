from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.events import EventBus
from core.exceptions import ModuleError, ValidationError
from core.module import BaseModule, ModuleExecutionContext, ModuleMetadata
from core.module_manager import ModuleManager
from modules.asset_inventory.module import AssetInventoryModule
from modules.project_summary.module import ProjectSummaryModule
from modules.system_health.module import SystemHealthModule


class PassingModule(BaseModule):
    metadata = ModuleMetadata(
        id="passing_module",
        name="Passing Module",
        version="1.0.0",
        author="Tester",
        description="Passes",
        category="tests",
    )

    def execute(self, context):
        return self.result(True, "completed", {"ok": True})


class FailingModule(PassingModule):
    metadata = ModuleMetadata(
        id="failing_module",
        name="Failing Module",
        version="1.0.0",
        author="Tester",
        description="Fails",
        category="tests",
    )

    def execute(self, context):
        raise RuntimeError("controlled failure")


class InitFailModule(PassingModule):
    metadata = ModuleMetadata(
        id="init_fail_module",
        name="Init Fail",
        version="1.0.0",
        author="Tester",
        description="Init fails",
        category="tests",
    )

    def initialize(self, context):
        raise RuntimeError("init failed")


class ShutdownFailModule(PassingModule):
    metadata = ModuleMetadata(
        id="shutdown_fail_module",
        name="Shutdown Fail",
        version="1.0.0",
        author="Tester",
        description="Shutdown fails",
        category="tests",
    )

    def shutdown(self):
        raise RuntimeError("shutdown failed")


class InvalidMetadataModule(BaseModule):
    metadata = "not metadata"


class IncompleteMetadataModule(BaseModule):
    metadata = ModuleMetadata(
        id="incomplete_module",
        name="",
        version="1.0.0",
        author="Tester",
        description="Missing name",
        category="tests",
    )


def test_builtin_modules_are_discovered(context):
    module_ids = {module["id"] for module in context.module_manager.list_modules()}

    assert {"asset_inventory", "system_health", "project_summary"} <= module_ids


def test_module_manager_empty_directory_returns_empty(context, tmp_path):
    manager = ModuleManager(context, EventBus())

    assert manager.discover(tmp_path / "missing") == []


def test_module_manager_registers_and_executes_simulated_module(context, tmp_path):
    manager = ModuleManager(context, EventBus())
    manager.register(PassingModule(), tmp_path / "passing.py")

    result = manager.execute(
        "passing_module",
        ModuleExecutionContext(application=context, parameters={}),
    )

    assert result.success is True
    assert result.data == {"ok": True}


def test_module_manager_duplicate_registration_raises(context, tmp_path):
    manager = ModuleManager(context, EventBus())
    manager.register(PassingModule(), tmp_path / "passing.py")

    with pytest.raises(ModuleError):
        manager.register(PassingModule(), tmp_path / "passing2.py")


def test_module_manager_rejects_invalid_metadata(context, tmp_path):
    manager = ModuleManager(context, EventBus())

    with pytest.raises(ModuleError):
        manager.register(InvalidMetadataModule(), tmp_path / "invalid.py")


def test_module_manager_rejects_incomplete_metadata(context, tmp_path):
    manager = ModuleManager(context, EventBus())

    with pytest.raises(ValidationError):
        manager.register(IncompleteMetadataModule(), tmp_path / "incomplete.py")


def test_module_manager_get_missing_raises(context):
    with pytest.raises(ModuleError):
        context.module_manager.get("missing")


def test_module_manager_execution_failure_is_controlled(context, tmp_path):
    manager = ModuleManager(context, EventBus())
    manager.register(FailingModule(), tmp_path / "failing.py")

    result = manager.execute("failing_module", ModuleExecutionContext(application=context))

    assert result.success is False
    assert "controlled failure" in result.messages[0]


def test_module_manager_initialization_and_shutdown_failures_are_isolated(context, tmp_path):
    manager = ModuleManager(context, EventBus())
    init_entry = manager.register(InitFailModule(), tmp_path / "init.py")
    shutdown_entry = manager.register(ShutdownFailModule(), tmp_path / "shutdown.py")

    manager.initialize_all()
    manager.shutdown_all()

    assert init_entry.state.value == "error"
    assert init_entry.last_error == "init failed"
    assert shutdown_entry.state.value == "error"
    assert shutdown_entry.last_error == "shutdown failed"


def test_module_discovery_handles_missing_module_class(context, tmp_path):
    module_dir = tmp_path / "modules" / "bad_module"
    module_dir.mkdir(parents=True)
    (module_dir / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    manager = ModuleManager(context, EventBus())

    assert manager.discover(tmp_path / "modules") == []


def test_module_discovery_handles_import_error(context, tmp_path):
    module_dir = tmp_path / "modules" / "broken_import"
    module_dir.mkdir(parents=True)
    (module_dir / "module.py").write_text("raise ImportError('boom')\n", encoding="utf-8")
    manager = ModuleManager(context, EventBus())

    assert manager.discover(tmp_path / "modules") == []


def test_module_loader_reports_missing_spec(context, tmp_path, monkeypatch):
    manager = ModuleManager(context, EventBus())
    monkeypatch.setattr("core.module_manager.importlib.util.spec_from_file_location", lambda *args, **kwargs: None)

    with pytest.raises(ModuleError):
        manager._load_python_module(tmp_path / "missing.py")


def test_asset_inventory_accepts_string_and_file_inputs(context, asset_file):
    module = AssetInventoryModule()
    string_result = module.execute(
        ModuleExecutionContext(application=context, parameters={"assets": "a,b"})
    )
    file_result = module.execute(
        ModuleExecutionContext(
            application=context,
            parameters={"input_file": str(asset_file.relative_to(context.root_path))},
        )
    )

    assert string_result.data["total_assets"] == 2
    assert file_result.data["by_type"] == {"host": 1, "network": 1}


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"assets": 123},
        {"input_file": "missing.json"},
        {"assets": [{"address": ""}]},
        {"assets": [" "]},
        {"assets": [42]},
        {"assets": [{"name": "host", "tags": {"bad": "shape"}}]},
    ],
)
def test_asset_inventory_invalid_inputs_fail_safely(context, parameters):
    module = AssetInventoryModule()

    if "assets" not in parameters and "input_file" not in parameters:
        with pytest.raises(ValidationError):
            module.validate(parameters)
        return
    with pytest.raises((ValidationError, json.JSONDecodeError)):
        module.execute(ModuleExecutionContext(application=context, parameters=parameters))


def test_asset_inventory_invalid_json_is_returned_as_module_error(context, tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{bad", encoding="utf-8")

    result = context.module_manager.execute(
        "asset_inventory",
        ModuleExecutionContext(application=context, parameters={"input_file": str(bad_file)}),
    )

    assert result.success is False
    assert result.status == "error"


def test_asset_inventory_file_object_must_contain_assets_list(context, tmp_path):
    bad_file = tmp_path / "bad_assets.json"
    bad_file.write_text('{"items": []}', encoding="utf-8")

    with pytest.raises(ValidationError, match="assets"):
        AssetInventoryModule().execute(
            ModuleExecutionContext(application=context, parameters={"input_file": str(bad_file)})
        )


def test_asset_inventory_file_payload_must_be_list(context, tmp_path):
    bad_file = tmp_path / "bad_assets.json"
    bad_file.write_text('{"assets": {"host": "x"}}', encoding="utf-8")

    with pytest.raises(ValidationError, match="list"):
        AssetInventoryModule().execute(
            ModuleExecutionContext(application=context, parameters={"input_file": str(bad_file)})
        )


def test_asset_inventory_converts_string_tag_to_list(context):
    result = AssetInventoryModule().execute(
        ModuleExecutionContext(
            application=context,
            parameters={"assets": [{"name": "host", "tags": "critical"}]},
        )
    )

    assert result.data["assets"][0]["tags"] == ["critical"]


def test_system_health_module_reports_runtime(context):
    result = SystemHealthModule().execute(ModuleExecutionContext(application=context))

    assert result.success is True
    assert result.data["modules"] >= 3
    assert result.data["log_configured"] is True


def test_project_summary_module_reports_global_and_project_stats(context):
    project = context.project_service.create_project("Resumo")

    global_result = ProjectSummaryModule().execute(ModuleExecutionContext(application=context))
    project_result = ProjectSummaryModule().execute(
        ModuleExecutionContext(application=context, parameters={"project_id": project.id})
    )

    assert global_result.data["total_projects"] >= 1
    assert project_result.data["project_id"] == project.id


def test_project_summary_rejects_empty_project_id():
    with pytest.raises(ValidationError):
        ProjectSummaryModule().validate({"project_id": " "})
