"""Discovery, validation, and execution for modules."""

from __future__ import annotations

import importlib.util
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from core.events import EventBus
from core.exceptions import ModuleError, ValidationError
from core.module import BaseModule, ModuleExecutionContext, ModuleMetadata, ModuleResult, ModuleState
from core.validators import validate_slug

if TYPE_CHECKING:
    from app.context import ApplicationContext


@dataclass
class ModuleRegistryEntry:
    module: BaseModule
    state: ModuleState
    loaded_from: Path
    loaded_at: float
    last_error: str | None = None


class ModuleManager:
    """Controls the lifecycle of internal modules."""

    def __init__(self, context: "ApplicationContext", event_bus: EventBus) -> None:
        self.context = context
        self.event_bus = event_bus
        self._registry: dict[str, ModuleRegistryEntry] = {}

    @property
    def registry(self) -> dict[str, ModuleRegistryEntry]:
        return dict(self._registry)

    def discover(self, modules_dir: Path) -> list[ModuleRegistryEntry]:
        if not modules_dir.exists():
            return []
        discovered: list[ModuleRegistryEntry] = []
        for module_dir in sorted(path for path in modules_dir.iterdir() if path.is_dir()):
            module_file = module_dir / "module.py"
            if not module_file.exists():
                continue
            try:
                loaded = self._load_python_module(module_file)
                module_class = getattr(loaded, "MODULE_CLASS", None)
                if module_class is None:
                    raise ModuleError("MODULE_CLASS is missing.")
                module = module_class()
                entry = self.register(module, module_file)
                discovered.append(entry)
            except Exception as exc:  # noqa: BLE001 - discovery isolates module faults.
                self.event_bus.publish(
                    "module.discovery_failed",
                    "module_manager",
                    {"path": str(module_file), "error": str(exc)},
                )
                self._log_warning(f"Module discovery failed for {module_file}: {exc}")
        return discovered

    def register(self, module: BaseModule, loaded_from: Path) -> ModuleRegistryEntry:
        self._validate_module(module)
        module_id = module.metadata.id
        if module_id in self._registry:
            raise ModuleError(f"Module '{module_id}' is already registered.")
        entry = ModuleRegistryEntry(
            module=module,
            state=ModuleState.LOADED,
            loaded_from=loaded_from,
            loaded_at=time.time(),
        )
        self._registry[module_id] = entry
        self.event_bus.publish(
            "module.loaded",
            "module_manager",
            {"module_id": module_id, "name": module.metadata.name},
        )
        return entry

    def initialize_all(self) -> None:
        for module_id in sorted(self._registry):
            entry = self._registry[module_id]
            try:
                entry.module.initialize(self.context)
                entry.state = ModuleState.READY
                self.event_bus.publish(
                    "module.initialized",
                    "module_manager",
                    {"module_id": module_id},
                )
            except Exception as exc:  # noqa: BLE001
                entry.state = ModuleState.ERROR
                entry.last_error = str(exc)
                self._log_warning(f"Module '{module_id}' initialization failed: {exc}")

    def list_modules(self) -> list[dict[str, str]]:
        rows = []
        for module_id, entry in sorted(self._registry.items()):
            metadata = entry.module.metadata
            rows.append(
                {
                    "id": module_id,
                    "name": metadata.name,
                    "category": metadata.category,
                    "version": metadata.version,
                    "state": entry.state.value,
                    "description": metadata.description,
                }
            )
        return rows

    def get(self, module_id: str) -> BaseModule:
        try:
            return self._registry[module_id].module
        except KeyError as exc:
            raise ModuleError(f"Module '{module_id}' is not registered.") from exc

    def execute(self, module_id: str, execution_context: ModuleExecutionContext) -> ModuleResult:
        if module_id not in self._registry:
            raise ModuleError(f"Module '{module_id}' is not registered.")
        entry = self._registry[module_id]
        module = entry.module
        entry.state = ModuleState.RUNNING
        self.event_bus.publish(
            "module.execution_started",
            "module_manager",
            {"module_id": module_id, "parameters": execution_context.parameters},
        )
        try:
            module.validate(execution_context.parameters)
            result = module.execute(execution_context)
            entry.state = ModuleState.COMPLETED if result.success else ModuleState.ERROR
            self.event_bus.publish(
                "module.execution_finished",
                "module_manager",
                {"module_id": module_id, "success": result.success},
            )
            return result
        except Exception as exc:  # noqa: BLE001
            entry.state = ModuleState.ERROR
            entry.last_error = str(exc)
            self.event_bus.publish(
                "module.execution_failed",
                "module_manager",
                {"module_id": module_id, "error": str(exc)},
            )
            self._log_error(f"Module '{module_id}' failed: {exc}")
            return ModuleResult(
                module_id=module_id,
                success=False,
                status="error",
                messages=[str(exc)],
                data={"error": str(exc)},
            ).finish()

    def shutdown_all(self) -> None:
        for module_id, entry in self._registry.items():
            previous_state = entry.state
            try:
                entry.module.shutdown()
                if previous_state != ModuleState.ERROR:
                    entry.state = ModuleState.FINALIZED
                    self.event_bus.publish(
                        "module.finalized",
                        "module_manager",
                        {"module_id": module_id},
                    )
            except Exception as exc:  # noqa: BLE001
                entry.state = ModuleState.ERROR
                entry.last_error = str(exc)
                self._log_warning(f"Module '{module_id}' shutdown failed: {exc}")

    def _validate_module(self, module: BaseModule) -> None:
        metadata = getattr(module, "metadata", None)
        if not isinstance(metadata, ModuleMetadata):
            raise ModuleError("Module metadata must be a ModuleMetadata instance.")
        validate_slug(metadata.id, "module id")
        required_values = [
            metadata.name,
            metadata.version,
            metadata.author,
            metadata.description,
            metadata.category,
        ]
        if any(not value for value in required_values):
            raise ValidationError(f"Module '{metadata.id}' has incomplete metadata.")

    def _load_python_module(self, module_file: Path) -> ModuleType:
        module_name = f"dataspectre_dynamic_module_{module_file.parent.name}"
        spec = importlib.util.spec_from_file_location(module_name, module_file)
        if spec is None or spec.loader is None:
            raise ModuleError(f"Cannot load module file '{module_file}'.")
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        return loaded

    def _log_warning(self, message: str) -> None:
        if self.context.log_service:
            self.context.log_service.record_event(
                component="module_manager", level="WARNING", message=message
            )

    def _log_error(self, message: str) -> None:
        if self.context.log_service:
            self.context.log_service.record_event(
                component="module_manager", level="ERROR", message=message
            )
