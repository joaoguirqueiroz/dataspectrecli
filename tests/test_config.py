from __future__ import annotations

import json

import pytest

from core.exceptions import ConfigurationError, ValidationError
from services.config_service import ConfigService


def test_config_loads_defaults(runtime_root):
    service = ConfigService(runtime_root)

    settings = service.load()

    assert settings["app"]["language"] == "pt-BR"
    assert settings["ui"]["theme"] == "dark"


def test_config_set_persists_valid_value(runtime_root):
    service = ConfigService(runtime_root)
    service.load()

    service.set("ui.theme", "light")

    assert ConfigService(runtime_root).load()["ui"]["theme"] == "light"


def test_config_invalid_values_fall_back_to_safe_defaults(runtime_root):
    service = ConfigService(runtime_root)
    settings = service.validate(
        {
            "ui": {"theme": "purple"},
            "logging": {"level": "verbose"},
            "reports": {"default_format": "pdf"},
        }
    )

    assert settings["ui"]["theme"] == "dark"
    assert settings["logging"]["level"] == "INFO"
    assert settings["reports"]["default_format"] == "markdown"


@pytest.mark.parametrize("report_format", ["markdown", "txt", "json", "csv", "html"])
def test_config_accepts_supported_report_formats(runtime_root, report_format):
    service = ConfigService(runtime_root)

    settings = service.validate({"reports": {"default_format": report_format}})

    assert settings["reports"]["default_format"] == report_format


def test_config_scanner_limits_fall_back_to_safe_defaults(runtime_root):
    service = ConfigService(runtime_root)

    settings = service.validate(
        {
            "scanners": {
                "defaults": {
                    "timeout": 0,
                    "concurrency": -1,
                    "rate_limit": "bad",
                    "max_targets": None,
                }
            }
        }
    )

    assert settings["scanners"]["defaults"] == {
        "profile": "basic",
        "timeout": 60,
        "concurrency": 5,
        "rate_limit": 25,
        "max_targets": 25,
    }
    assert settings["scanners"]["smart"]["default_profile"] == "basic"


def test_config_loads_yaml_overlay(runtime_root):
    yaml_file = runtime_root / "config" / "dataspectre.yaml"
    yaml_file.write_text(
        "scanners:\n  defaults:\n    timeout: 45\n  smart:\n    large_target_threshold: 4\n",
        encoding="utf-8",
    )

    settings = ConfigService(runtime_root).load()

    assert settings["scanners"]["defaults"]["timeout"] == 45
    assert settings["scanners"]["smart"]["large_target_threshold"] == 4


def test_config_recovers_from_corrupted_yaml(runtime_root):
    yaml_file = runtime_root / "config" / "dataspectre.yaml"
    yaml_file.write_text("scanners: [broken", encoding="utf-8")

    settings = ConfigService(runtime_root).load()

    assert settings["scanners"]["defaults"]["timeout"] == 60
    assert "yaml_warning" in settings["runtime"]


def test_config_rejects_unsafe_paths(runtime_root):
    service = ConfigService(runtime_root)

    with pytest.raises(ValidationError):
        service.validate({"paths": {"workdir": "../outside"}})


def test_config_reset_restores_defaults(runtime_root):
    service = ConfigService(runtime_root)
    service.load()
    service.set("ui.theme", "light")

    reset = service.reset()

    assert reset["ui"]["theme"] == "dark"


def test_config_missing_path_key_raises(runtime_root):
    service = ConfigService(runtime_root)
    service.load()

    with pytest.raises(ConfigurationError):
        service.resolve_path("missing")


def test_config_cannot_set_nested_key_below_scalar(runtime_root):
    service = ConfigService(runtime_root)
    service.load()
    service.set("custom", "value")

    with pytest.raises(ConfigurationError):
        service.set("custom.child", True)


def test_config_empty_key_raises(runtime_root):
    with pytest.raises(ConfigurationError):
        ConfigService(runtime_root).set("", "value")


def test_config_save_before_load_raises(runtime_root):
    with pytest.raises(ConfigurationError):
        ConfigService(runtime_root).save()


def test_config_recovers_from_corrupted_runtime_file(runtime_root):
    runtime_file = runtime_root / "data" / "config" / "settings.json"
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text("{broken json", encoding="utf-8")

    settings = ConfigService(runtime_root).load()

    assert settings["ui"]["theme"] == "dark"


def test_config_recovers_from_corrupted_default_file(runtime_root):
    default_file = runtime_root / "config" / "default_config.json"
    default_file.write_text("{broken json", encoding="utf-8")

    settings = ConfigService(runtime_root).load()

    assert settings["ui"]["theme"] == "dark"


def test_config_merges_runtime_overlay(runtime_root):
    runtime_file = runtime_root / "data" / "config" / "settings.json"
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text(json.dumps({"ui": {"theme": "high-contrast"}}), encoding="utf-8")

    settings = ConfigService(runtime_root).load()

    assert settings["ui"]["theme"] == "high-contrast"
    assert settings["app"]["language"] == "pt-BR"


def test_config_get_and_set_lazy_load(runtime_root):
    service = ConfigService(runtime_root)

    assert service.get("ui.theme") == "dark"
    updated = ConfigService(runtime_root).set("ui.theme", "light")

    assert updated["ui"]["theme"] == "light"
