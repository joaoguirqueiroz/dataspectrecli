from __future__ import annotations

from types import SimpleNamespace

from services.setup_service import (
    STATUS_MANUAL,
    STATUS_MISSING,
    STATUS_OK,
    SetupService,
)


def completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_setup_service_full_check_generates_reports(runtime_root):
    calls = []

    def fake_runner(command, **kwargs):
        calls.append((command, kwargs))
        if command[:3] == ["python", "-m", "pip"]:
            return completed("pip 25.0")
        if command[0].endswith("python") and command[2:] == ["pip", "--version"]:
            return completed("pip 25.0")
        if command[0].endswith("python") and command[2:] == ["pip", "check"]:
            return completed("No broken requirements found.")
        if command == ["git", "--version"]:
            return completed("git version 2.45.0")
        if command == ["nmap", "--version"]:
            return completed("Nmap version 7.95")
        if command == ["nuclei", "-version"]:
            return completed("nuclei v3.3.0")
        if command[1:] == ["dataspectre.py", "--version"]:
            return completed("sentinelscan 1.0.0")
        return completed()

    def fake_which(binary):
        return f"/usr/bin/{binary}" if binary in {"apt", "git", "nmap", "nuclei"} else None

    (runtime_root / "tests").mkdir(exist_ok=True)
    (runtime_root / "dataspectre.py").write_text("print('dataspectre')\n", encoding="utf-8")
    (runtime_root / "main.py").write_text("print('sentinelscan')\n", encoding="utf-8")
    (runtime_root / "README.md").write_text("# SentinelScan\n", encoding="utf-8")
    (runtime_root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (runtime_root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (runtime_root / "pyproject.toml").write_text("[project]\nname = 'dataspectre-cli'\n", encoding="utf-8")
    (runtime_root / "requirements.txt").write_text("-r requirements/base.txt\n", encoding="utf-8")
    service = SetupService(runtime_root, runner=fake_runner, which=fake_which)
    report = service.run_checks()

    assert report.overall_status == STATUS_OK
    assert any(check.name == "Nmap" and check.status == STATUS_OK for check in report.checks)
    assert any(check.name == "Nuclei" and check.status == STATUS_OK for check in report.checks)
    assert (runtime_root / "reports" / "setup" / "setup_report.txt").exists()
    assert (runtime_root / "reports" / "setup" / "setup_report.json").exists()
    assert all(call[1].get("shell") is False for call in calls)


def test_setup_service_reports_missing_scanner_tools(runtime_root):
    def fake_runner(command, **kwargs):
        if command[0].endswith("python") and command[2:] == ["pip", "--version"]:
            return completed("pip 25.0")
        if command[0].endswith("python") and command[2:] == ["pip", "check"]:
            return completed("No broken requirements found.")
        if command == ["git", "--version"]:
            return completed("git version 2.45.0")
        if command[1:] == ["dataspectre.py", "--version"]:
            return completed("sentinelscan 1.0.0")
        return completed()

    def fake_which(binary):
        return f"/usr/bin/{binary}" if binary in {"apt", "git"} else None

    report = SetupService(runtime_root, runner=fake_runner, which=fake_which).run_tool_checks()

    assert report.overall_status == STATUS_MANUAL
    assert any(check.name == "Nmap" and check.status == STATUS_MISSING for check in report.checks)
    assert any(check.name == "Nuclei" and check.status == STATUS_MISSING for check in report.checks)


def test_setup_service_detects_package_managers(runtime_root):
    service = SetupService(runtime_root, which=lambda binary: f"/bin/{binary}" if binary == "dnf" else None)

    assert service.detect_package_manager() == "dnf"


def test_setup_service_builds_safe_install_commands(runtime_root):
    commands = []

    def fake_runner(command, **kwargs):
        commands.append((command, kwargs))
        return completed("ok")

    service = SetupService(
        runtime_root,
        runner=fake_runner,
        which=lambda binary: f"/bin/{binary}" if binary in {"apt", "go"} else None,
    )

    nmap_results = service.install_nmap()
    nuclei_results = service.install_nuclei()

    assert [result.command for result in nmap_results] == [
        ["sudo", "apt", "update"],
        ["sudo", "apt", "install", "-y", "nmap"],
    ]
    assert nuclei_results[0].command == [
        "go",
        "install",
        "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
    ]
    assert all(kwargs.get("shell") is False for _, kwargs in commands)


def test_setup_service_marks_python_dependencies_missing(runtime_root):
    (runtime_root / "requirements.txt").write_text("package-that-does-not-exist-xyz>=1\n", encoding="utf-8")
    service = SetupService(runtime_root, runner=lambda command, **kwargs: completed(), which=lambda binary: None)

    check = service.check_python_dependencies()

    assert check.status == STATUS_MANUAL
    assert "package-that-does-not-exist-xyz" in check.detail


def test_setup_service_checks_nuclei_templates_with_mock(runtime_root):
    service = SetupService(
        runtime_root,
        runner=lambda command, **kwargs: completed("templates loaded"),
        which=lambda binary: "/usr/bin/nuclei" if binary == "nuclei" else None,
    )

    check = service.check_nuclei_templates()

    assert check.status == STATUS_OK
    assert check.version == "templates loaded"
