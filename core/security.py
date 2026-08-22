"""Simple profile-based authorization layer."""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import PermissionDeniedError


ADMIN_PERMISSIONS = {
    "config:write",
    "projects:write",
    "sessions:write",
    "reports:write",
    "plugins:admin",
    "modules:run",
    "logs:read",
    "maintenance:clean",
}

PROFILE_PERMISSIONS = {
    "administrator": ADMIN_PERMISSIONS,
    "developer": ADMIN_PERMISSIONS - {"plugins:admin"},
    "operator": {
        "projects:write",
        "sessions:write",
        "reports:write",
        "modules:run",
        "logs:read",
        "maintenance:clean",
    },
    "viewer": {"logs:read"},
}


@dataclass(frozen=True)
class PermissionDecision:
    profile: str
    permission: str
    allowed: bool


class PermissionManager:
    """Centralized permission checks for administrative operations."""

    def __init__(self, active_profile: str = "administrator") -> None:
        self.active_profile = active_profile

    def can(self, permission: str, profile: str | None = None) -> PermissionDecision:
        selected_profile = profile or self.active_profile
        allowed = permission in PROFILE_PERMISSIONS.get(selected_profile, set())
        return PermissionDecision(
            profile=selected_profile, permission=permission, allowed=allowed
        )

    def require(self, permission: str, profile: str | None = None) -> None:
        decision = self.can(permission, profile)
        if not decision.allowed:
            raise PermissionDeniedError(
                f"Profile '{decision.profile}' cannot perform '{decision.permission}'."
            )
