"""Plugin discovery and lifecycle management."""

from __future__ import annotations

import importlib.util
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

from core.constants import APP_VERSION
from core.events import EventBus
from core.exceptions import PluginError
from core.plugin import BasePlugin, PluginContext, PluginMetadata, PluginState
from core.validators import validate_slug
from services.storage import read_json

if TYPE_CHECKING:
    from app.context import ApplicationContext


@dataclass
class PluginRegistryEntry:
    metadata: PluginMetadata
    state: PluginState
    path: Path
    loaded_at: float
    plugin: BasePlugin | None = None
    enabled: bool = True
    last_error: str | None = None


class PluginManager:
    """Controls optional extension discovery, validation, and lifecycle."""

    def __init__(self, context: "ApplicationContext", event_bus: EventBus) -> None:
        self.context = context
        self.event_bus = event_bus
        self._registry: dict[str, PluginRegistryEntry] = {}

    @property
    def registry(self) -> dict[str, PluginRegistryEntry]:
        return dict(self._registry)

    def discover(self, plugins_dir: Path) -> list[PluginRegistryEntry]:
        if not plugins_dir.exists():
            return []
        entries: list[PluginRegistryEntry] = []
        for plugin_dir in sorted(path for path in plugins_dir.iterdir() if path.is_dir()):
            manifest = plugin_dir / "plugin.json"
            if not manifest.exists():
                continue
            try:
                entries.append(self._load_manifest(plugin_dir, manifest))
            except Exception as exc:  # noqa: BLE001
                self.event_bus.publish(
                    "plugin.discovery_failed",
                    "plugin_manager",
                    {"path": str(plugin_dir), "error": str(exc)},
                )
                self._log_warning(f"Plugin discovery failed for {plugin_dir}: {exc}")
        return entries

    def initialize_all(self) -> None:
        for plugin_id, entry in sorted(self._registry.items()):
            if not entry.enabled:
                entry.state = PluginState.DISABLED
                continue
            if entry.plugin is None:
                entry.state = PluginState.LOADED
                continue
            try:
                entry.plugin.initialize(
                    PluginContext(
                        application=self.context,
                        metadata=entry.metadata,
                        settings=self._plugin_settings(plugin_id),
                    )
                )
                entry.state = PluginState.INITIALIZED
                self.event_bus.publish(
                    "plugin.initialized",
                    "plugin_manager",
                    {"plugin_id": plugin_id},
                )
            except Exception as exc:  # noqa: BLE001
                entry.state = PluginState.ERROR
                entry.last_error = str(exc)
                self._log_warning(f"Plugin '{plugin_id}' initialization failed: {exc}")

    def list_plugins(self) -> list[dict[str, Any]]:
        rows = []
        for plugin_id, entry in sorted(self._registry.items()):
            rows.append(
                {
                    "id": plugin_id,
                    "name": entry.metadata.name,
                    "category": entry.metadata.category,
                    "version": entry.metadata.version,
                    "enabled": entry.enabled,
                    "state": entry.state.value,
                    "description": entry.metadata.description,
                }
            )
        return rows

    def shutdown_all(self) -> None:
        for plugin_id, entry in self._registry.items():
            if entry.plugin is None or entry.state != PluginState.INITIALIZED:
                continue
            try:
                entry.plugin.shutdown()
                entry.state = PluginState.FINALIZED
                self.event_bus.publish(
                    "plugin.finalized",
                    "plugin_manager",
                    {"plugin_id": plugin_id},
                )
            except Exception as exc:  # noqa: BLE001
                entry.state = PluginState.ERROR
                entry.last_error = str(exc)
                self._log_warning(f"Plugin '{plugin_id}' shutdown failed: {exc}")

    def _load_manifest(self, plugin_dir: Path, manifest: Path) -> PluginRegistryEntry:
        payload = read_json(manifest, default={})
        metadata_payload = payload.get("metadata", payload)
        metadata = PluginMetadata(
            id=metadata_payload["id"],
            name=metadata_payload["name"],
            version=metadata_payload["version"],
            author=metadata_payload["author"],
            description=metadata_payload["description"],
            category=metadata_payload["category"],
            min_app_version=metadata_payload.get("min_app_version", "1.0.0"),
            dependencies=list(metadata_payload.get("dependencies", [])),
            components=list(metadata_payload.get("components", [])),
        )
        validate_slug(metadata.id, "plugin id")
        if self._version_tuple(metadata.min_app_version) > self._version_tuple(APP_VERSION):
            raise PluginError(
                f"Plugin '{metadata.id}' requires application version "
                f"{metadata.min_app_version}+."
            )
        if metadata.id in self._registry:
            raise PluginError(f"Plugin '{metadata.id}' is already registered.")
        enabled = bool(payload.get("enabled", True))
        missing_dependencies = [
            dependency for dependency in metadata.dependencies if dependency not in self._registry
        ]
        if missing_dependencies:
            raise PluginError(
                f"Plugin '{metadata.id}' has missing dependencies: "
                f"{', '.join(missing_dependencies)}."
            )
        plugin_instance = None if not enabled else self._instantiate_plugin(plugin_dir, payload, metadata)
        entry = PluginRegistryEntry(
            metadata=metadata,
            state=PluginState.DISCOVERED,
            path=plugin_dir,
            loaded_at=time.time(),
            plugin=plugin_instance,
            enabled=enabled,
        )
        self._registry[metadata.id] = entry
        self.event_bus.publish(
            "plugin.loaded",
            "plugin_manager",
            {"plugin_id": metadata.id, "enabled": enabled},
        )
        return entry

    def _instantiate_plugin(
        self, plugin_dir: Path, payload: dict[str, Any], metadata: PluginMetadata
    ) -> BasePlugin | None:
        entrypoint = payload.get("entrypoint")
        if not entrypoint:
            return None
        plugin_file = plugin_dir / entrypoint
        if not plugin_file.exists():
            raise PluginError(f"Plugin entrypoint '{entrypoint}' not found.")
        loaded = self._load_python_module(plugin_file, metadata.id)
        class_name = payload.get("class_name", "PLUGIN_CLASS")
        plugin_class = getattr(loaded, class_name, None)
        if plugin_class is None and class_name != "PLUGIN_CLASS":
            plugin_class = getattr(loaded, "PLUGIN_CLASS", None)
        if plugin_class is None:
            raise PluginError(f"Plugin class '{class_name}' not found.")
        plugin = plugin_class()
        if not isinstance(plugin, BasePlugin):
            raise PluginError("Plugin class must inherit from BasePlugin.")
        if not isinstance(getattr(plugin, "metadata", None), PluginMetadata):
            raise PluginError("Plugin metadata must be a PluginMetadata instance.")
        if plugin.metadata.id != metadata.id:
            raise PluginError(
                f"Plugin metadata id '{plugin.metadata.id}' does not match "
                f"manifest id '{metadata.id}'."
            )
        return plugin

    def _load_python_module(self, module_file: Path, plugin_id: str) -> ModuleType:
        module_name = f"dataspectre_dynamic_plugin_{plugin_id}"
        spec = importlib.util.spec_from_file_location(module_name, module_file)
        if spec is None or spec.loader is None:
            raise PluginError(f"Cannot load plugin file '{module_file}'.")
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        return loaded

    def _plugin_settings(self, plugin_id: str) -> dict[str, Any]:
        if not self.context.config_service:
            return {}
        return self.context.config_service.get(f"plugins.{plugin_id}", default={})

    def _log_warning(self, message: str) -> None:
        if self.context.log_service:
            self.context.log_service.record_event(
                component="plugin_manager", level="WARNING", message=message
            )

    def _version_tuple(self, version: str) -> tuple[int, ...]:
        parts = []
        for part in version.split("."):
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(0)
        return tuple(parts)
