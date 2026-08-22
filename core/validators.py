"""Shared validation helpers."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from core.exceptions import ValidationError


SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,80}$")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", ascii_value).strip("-_").lower()
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or "item"


def validate_slug(value: str, field_name: str = "identifier") -> str:
    if not SLUG_PATTERN.match(value):
        raise ValidationError(
            f"{field_name} must contain 2-81 lowercase letters, numbers, '-' or '_'."
        )
    return value


def validate_non_empty(value: str, field_name: str) -> str:
    if not value or not value.strip():
        raise ValidationError(f"{field_name} cannot be empty.")
    return value.strip()


def ensure_relative_path(path_value: str, field_name: str) -> Path:
    path = Path(path_value)
    if path.is_absolute() or ".." in path.parts:
        raise ValidationError(f"{field_name} must be a relative path inside the repo.")
    return path


def ensure_within_root(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    if resolved_root != resolved_candidate and resolved_root not in resolved_candidate.parents:
        raise ValidationError(f"Path '{candidate}' is outside the application root.")
    return resolved_candidate

