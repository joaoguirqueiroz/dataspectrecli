"""Public plugin interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.context import ApplicationContext


class PluginState(str, Enum):
    DISCOVERED = "discovered"
    DISABLED = "disabled"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ERROR = "error"
    FINALIZED = "finalized"


@dataclass(frozen=True)
class PluginMetadata:
    id: str
    name: str
    version: str
    author: str
    description: str
    category: str
    min_app_version: str = "1.0.0"
    dependencies: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)


@dataclass
class PluginContext:
    application: "ApplicationContext"
    metadata: PluginMetadata
    settings: dict[str, Any] = field(default_factory=dict)


class BasePlugin:
    """Base class for optional extensions."""

    metadata: PluginMetadata

    def initialize(self, context: PluginContext) -> None:
        return None

    def shutdown(self) -> None:
        return None

