"""Centralized configuration management."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from core.constants import DEFAULT_CONFIG_FILE, RUNTIME_CONFIG_FILE
from core.exceptions import ConfigurationError
from core.validators import ensure_relative_path
from services.storage import ensure_dir, read_json, write_json


FALLBACK_CONFIG: dict[str, Any] = {
    "app": {"language": "pt-BR", "timezone": "America/Fortaleza"},
    "ui": {"theme": "dark", "table_style": "compact", "progress": True},
    "paths": {
        "workdir": "data/projects",
        "reports": "reports",
        "logs": "logs",
        "cache": "cache",
        "backups": "backups",
    },
    "logging": {
        "level": "INFO",
        "max_bytes": 1048576,
        "backup_count": 5,
        "retention_days": 30,
    },
    "reports": {"default_format": "markdown", "template": "technical"},
    "security": {"active_profile": "administrator"},
    "performance": {"max_tasks": 4, "cache_enabled": True},
    "scanners": {
        "defaults": {
            "profile": "basic",
            "timeout": 60,
            "concurrency": 5,
            "rate_limit": 25,
            "max_targets": 25,
        },
        "smart": {
            "default_profile": "basic",
            "large_target_threshold": 10,
            "web_ports": [80, 443, 8080, 8443],
        },
        "nmap": {
            "default_profile": "basic",
            "allowed_nse_profiles": ["default-safe", "discovery", "version", "safe", "custom-authorized"],
            "allowed_nse_scripts": ["default", "discovery", "version", "safe", "http-title", "http-headers"],
        },
        "nuclei": {
            "default_profile": "basic",
            "severities": ["info", "low", "medium", "high", "critical"],
            "tags": ["tech", "exposure", "misconfig"],
            "templates": [],
            "template_dirs": [],
        },
    },
    "baseline": {
        "enabled": True,
        "alert_new_open_ports": True,
        "alert_new_high_findings": True,
    },
    "alerts": {"terminal": True, "report": True, "history": True},
    "modules": {},
    "plugins": {},
}


class ConfigService:
    """Loads, validates, persists, and exposes application settings."""

    VALID_THEMES = {"dark", "light", "high-contrast"}
    VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    VALID_REPORT_FORMATS = {"markdown", "txt", "json", "csv", "html"}

    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path
        self.default_config_path = root_path / DEFAULT_CONFIG_FILE
        self.yaml_config_path = root_path / "config" / "dataspectre.yaml"
        self.legacy_yaml_config_path = root_path / "config" / "sentinelscan.yaml"
        self.runtime_config_path = root_path / RUNTIME_CONFIG_FILE
        self.settings: dict[str, Any] = {}
        self.last_warning: str | None = None

    def load(self) -> dict[str, Any]:
        self.last_warning = None
        try:
            default_config = read_json(self.default_config_path, default=None)
        except json.JSONDecodeError:
            default_config = None
        if default_config is None:
            default_config = deepcopy(FALLBACK_CONFIG)
        yaml_config = self._read_yaml_config()
        if yaml_config:
            default_config = self._deep_merge(deepcopy(default_config), yaml_config)
        try:
            runtime_config = read_json(self.runtime_config_path, default={})
        except json.JSONDecodeError:
            runtime_config = {}
        merged = self._deep_merge(deepcopy(default_config), runtime_config)
        self.settings = self.validate(merged)
        if self.last_warning:
            self.settings.setdefault("runtime", {})["yaml_warning"] = self.last_warning
        return deepcopy(self.settings)

    def validate(self, settings: dict[str, Any]) -> dict[str, Any]:
        config = self._deep_merge(deepcopy(FALLBACK_CONFIG), settings)
        theme = config["ui"].get("theme")
        if theme not in self.VALID_THEMES:
            config["ui"]["theme"] = FALLBACK_CONFIG["ui"]["theme"]
        log_level = str(config["logging"].get("level", "INFO")).upper()
        if log_level not in self.VALID_LOG_LEVELS:
            log_level = "INFO"
        config["logging"]["level"] = log_level
        report_format = config["reports"].get("default_format")
        if report_format not in self.VALID_REPORT_FORMATS:
            config["reports"]["default_format"] = "markdown"
        scanner_defaults = config.setdefault("scanners", {}).setdefault("defaults", {})
        scanner_defaults["profile"] = str(scanner_defaults.get("profile") or "basic")
        scanner_defaults["timeout"] = self._positive_int(
            scanner_defaults.get("timeout"), FALLBACK_CONFIG["scanners"]["defaults"]["timeout"]
        )
        scanner_defaults["concurrency"] = self._positive_int(
            scanner_defaults.get("concurrency"),
            FALLBACK_CONFIG["scanners"]["defaults"]["concurrency"],
        )
        scanner_defaults["rate_limit"] = self._positive_int(
            scanner_defaults.get("rate_limit"),
            FALLBACK_CONFIG["scanners"]["defaults"]["rate_limit"],
        )
        scanner_defaults["max_targets"] = self._positive_int(
            scanner_defaults.get("max_targets"),
            FALLBACK_CONFIG["scanners"]["defaults"]["max_targets"],
        )
        smart = config.setdefault("scanners", {}).setdefault("smart", {})
        smart["default_profile"] = str(smart.get("default_profile") or "basic")
        smart["large_target_threshold"] = self._positive_int(
            smart.get("large_target_threshold"),
            FALLBACK_CONFIG["scanners"]["smart"]["large_target_threshold"],
        )
        smart["web_ports"] = self._int_list(
            smart.get("web_ports"),
            FALLBACK_CONFIG["scanners"]["smart"]["web_ports"],
        )
        nuclei = config.setdefault("scanners", {}).setdefault("nuclei", {})
        nuclei["severities"] = self._str_list(
            nuclei.get("severities"), FALLBACK_CONFIG["scanners"]["nuclei"]["severities"]
        )
        nuclei["tags"] = self._str_list(
            nuclei.get("tags"), FALLBACK_CONFIG["scanners"]["nuclei"]["tags"]
        )
        nuclei["templates"] = self._str_list(nuclei.get("templates"), [])
        nuclei["template_dirs"] = self._str_list(nuclei.get("template_dirs"), [])
        nmap = config.setdefault("scanners", {}).setdefault("nmap", {})
        nmap["allowed_nse_profiles"] = self._str_list(
            nmap.get("allowed_nse_profiles"),
            FALLBACK_CONFIG["scanners"]["nmap"]["allowed_nse_profiles"],
        )
        nmap["allowed_nse_scripts"] = self._str_list(
            nmap.get("allowed_nse_scripts"),
            FALLBACK_CONFIG["scanners"]["nmap"]["allowed_nse_scripts"],
        )
        for key, value in config.get("paths", {}).items():
            ensure_relative_path(str(value), f"paths.{key}")
        return config

    def save(self) -> None:
        if not self.settings:
            raise ConfigurationError("Configuration has not been loaded.")
        write_json(self.runtime_config_path, self.settings)

    def reset(self) -> dict[str, Any]:
        self.settings = self.validate(deepcopy(FALLBACK_CONFIG))
        write_json(self.runtime_config_path, self.settings)
        return deepcopy(self.settings)

    def get(self, key: str | None = None, default: Any | None = None) -> Any:
        if not self.settings:
            self.load()
        if key is None:
            return deepcopy(self.settings)
        current: Any = self.settings
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return deepcopy(current)

    def set(self, key: str, value: Any) -> dict[str, Any]:
        if not key:
            raise ConfigurationError("Configuration key cannot be empty.")
        if not self.settings:
            self.load()
        current = self.settings
        parts = key.split(".")
        for part in parts[:-1]:
            node = current.setdefault(part, {})
            if not isinstance(node, dict):
                raise ConfigurationError(f"Cannot set nested key below '{part}'.")
            current = node
        current[parts[-1]] = value
        self.settings = self.validate(self.settings)
        self.save()
        return deepcopy(self.settings)

    def resolve_path(self, path_key: str) -> Path:
        path_value = self.get(f"paths.{path_key}")
        if path_value is None:
            raise ConfigurationError(f"Path configuration '{path_key}' does not exist.")
        return self.root_path / ensure_relative_path(str(path_value), f"paths.{path_key}")

    def ensure_directories(self) -> None:
        for value in self.get("paths", default={}).values():
            ensure_dir(self.root_path / ensure_relative_path(str(value), "paths"))
        ensure_dir(self.runtime_config_path.parent)

    def _deep_merge(self, base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
        for key, value in overlay.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    def _read_yaml_config(self) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        # Load the legacy file first when present so DataSpectre settings can override it.
        for source_path in (self.legacy_yaml_config_path, self.yaml_config_path):
            if not source_path.exists():
                continue
            try:
                payload = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                self.last_warning = f"YAML configuration ignored ({source_path.name}): {exc}"
                continue
            if not isinstance(payload, dict):
                self.last_warning = f"YAML configuration ignored ({source_path.name}): root must be a mapping."
                continue
            merged = self._deep_merge(merged, payload)
        return merged

    def _positive_int(self, value: Any, fallback: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return fallback
        return parsed if parsed > 0 else fallback

    def _str_list(self, value: Any, fallback: list[str]) -> list[str]:
        if value is None:
            return list(fallback)
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return list(fallback)

    def _int_list(self, value: Any, fallback: list[int]) -> list[int]:
        values = value if isinstance(value, list) else fallback
        parsed: list[int] = []
        for item in values:
            try:
                number = int(item)
            except (TypeError, ValueError):
                continue
            if 1 <= number <= 65535:
                parsed.append(number)
        return parsed or list(fallback)
