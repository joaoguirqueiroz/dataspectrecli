from __future__ import annotations

import pytest

from cli.app import main
from core.exceptions import (
    BootstrapError,
    ConfigurationError,
    ModuleError,
    PermissionDeniedError,
    PluginError,
    ProjectError,
    ReportError,
    SentinelScanError,
    SessionError,
    ValidationError,
)


@pytest.mark.parametrize(
    "error_class",
    [
        BootstrapError,
        ConfigurationError,
        ValidationError,
        PermissionDeniedError,
        ModuleError,
        PluginError,
        ProjectError,
        SessionError,
        ReportError,
    ],
)
def test_domain_errors_share_base_class(error_class):
    assert issubclass(error_class, SentinelScanError)


def test_cli_catches_expected_errors(runtime_root, capsys):
    exit_code = main(["--root", str(runtime_root), "projects", "show", "missing"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "[ERROR]" in captured.err

