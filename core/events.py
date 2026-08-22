"""Internal event bus used to decouple components."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, DefaultDict


EventHandler = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    """Structured internal event."""

    name: str
    component: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class EventBus:
    """Small synchronous event bus for internal communication."""

    def __init__(self) -> None:
        self._handlers: DefaultDict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._handlers[event_name].append(handler)

    def publish(
        self, name: str, component: str, payload: dict[str, Any] | None = None
    ) -> Event:
        event = Event(name=name, component=component, payload=payload or {})
        self._history.append(event)
        for handler in list(self._handlers.get(name, [])):
            handler(event)
        for handler in list(self._handlers.get("*", [])):
            handler(event)
        return event

    def history(self, limit: int | None = None) -> list[Event]:
        if limit is None:
            return list(self._history)
        return list(self._history[-limit:])

