from __future__ import annotations

from dataclasses import dataclass

from scripts import check_tools, setup_report, setup_wizard


@dataclass
class FakeReport:
    overall_status: str = "OK"

    def to_dict(self):
        return {
            "overall_status": self.overall_status,
            "operating_system": "Linux",
            "package_manager": "apt",
            "report_paths": {"txt": "reports/setup/setup_report.txt", "json": "reports/setup/setup_report.json"},
            "checks": [{"name": "Nmap", "status": "OK", "version": "7.95", "action": ""}],
        }


class FakeSetupService:
    def __init__(self, root_path):
        self.root_path = root_path

    def run_checks(self, include_templates=False):
        return FakeReport()

    def run_tool_checks(self, include_templates=False):
        return FakeReport()

    def install_python_dependencies(self):
        raise AssertionError("install should not run in check-only mode")


def test_check_tools_script_runs_with_fake_service(monkeypatch, runtime_root):
    monkeypatch.setattr(check_tools, "SetupService", FakeSetupService)

    payload = check_tools.run(runtime_root)

    assert payload["overall_status"] == "OK"
    assert payload["checks"][0]["name"] == "Nmap"


def test_setup_report_script_generates_payload_with_fake_service(monkeypatch, runtime_root):
    monkeypatch.setattr(setup_report, "SetupService", FakeSetupService)

    payload = setup_report.generate(runtime_root, tools_only=True)

    assert payload["report_paths"]["json"].endswith("setup_report.json")


def test_setup_wizard_check_only_does_not_install(monkeypatch, runtime_root, capsys):
    monkeypatch.setattr(setup_wizard, "SetupService", FakeSetupService)

    report = setup_wizard.run_wizard(runtime_root, ask_to_install=False)
    captured = capsys.readouterr()

    assert report.overall_status == "OK"
    assert "Nenhuma instalacao foi executada" in captured.out
