from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from core.exceptions import ValidationError
from services.scanner_service import (
    ScannerParseError,
    ScannerService,
    ScannerTimeoutError,
    ScannerToolUnavailable,
)


NMAP_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="127.0.0.1" addrtype="ipv4"/>
    <hostnames><hostname name="localhost" type="user"/></hostnames>
    <os><osmatch name="Linux 6.x" accuracy="98"/></os>
    <ports>
      <port protocol="tcp" portid="80">
        <state state="open"/>
        <service name="http" product="nginx" version="1.25"/>
      </port>
    </ports>
  </host>
</nmaprun>
"""


NUCLEI_JSONL = (
    '{"template-id":"test-template","host":"http://localhost",'
    '"matched-at":"http://localhost/login","timestamp":"2026-07-06T10:00:00Z",'
    '"info":{"name":"Test Finding","severity":"medium","description":"Example"}}\n'
)


def test_scanner_service_validates_nmap_targets(runtime_root):
    service = ScannerService(runtime_root)

    assert service.validate_nmap_target("127.0.0.1") == "127.0.0.1"
    assert service.validate_nmap_target("localhost") == "localhost"
    assert service.validate_nmap_target("192.168.0.0/30") == "192.168.0.0/30"

    with pytest.raises(ValidationError):
        service.validate_nmap_target("bad target;rm -rf")
    with pytest.raises(ValidationError):
        service.validate_nmap_target("8.8.8.0/24")


def test_scanner_service_validates_nuclei_targets(runtime_root):
    service = ScannerService(runtime_root)

    assert service.validate_nuclei_target("https://example.com") == "https://example.com"
    assert service.validate_nuclei_target("127.0.0.1") == "127.0.0.1"

    with pytest.raises(ValidationError):
        service.validate_nuclei_target("ftp://example.com")
    with pytest.raises(ValidationError):
        service.validate_nuclei_targets(["https://example.com", "http://localhost"], max_targets=1)


def test_scanner_service_builds_safe_nmap_command(runtime_root):
    service = ScannerService(runtime_root)

    command = service.build_nmap_command(
        "127.0.0.1",
        runtime_root / "reports" / "nmap",
        profile="ports",
        ports="80,443",
    )

    assert command.args[0] == "nmap"
    assert "-p" in command.args
    assert "80,443" in command.args
    assert command.profile == "ports"
    assert command.output_files["xml"].endswith(".xml")
    assert "nmap_" in command.output_files["xml"]


@pytest.mark.parametrize(
    ("profile", "expected_flags"),
    [
        ("quick", ["-T4", "-F"]),
        ("servicos", ["-sV"]),
        ("scripts-padrao", ["-sC"]),
        ("servicos-scripts", ["-sV", "-sC"]),
    ],
)
def test_scanner_service_builds_real_nmap_profiles(runtime_root, profile, expected_flags):
    service = ScannerService(runtime_root)

    command = service.build_nmap_command(
        "127.0.0.1",
        runtime_root / "reports" / "nmap",
        profile=profile,
    )

    for flag in expected_flags:
        assert flag in command.args
    assert "-oN" in command.args
    assert "-oX" in command.args


def test_scanner_service_rejects_unsafe_nmap_custom_flag(runtime_root):
    service = ScannerService(runtime_root)

    with pytest.raises(ValidationError):
        service.build_nmap_command(
            "127.0.0.1",
            runtime_root / "reports" / "nmap",
            profile="custom",
            custom_flags=["--script"],
        )


def test_scanner_service_builds_safe_nuclei_command(runtime_root):
    service = ScannerService(runtime_root)

    command = service.build_nuclei_command(
        ["http://localhost"],
        runtime_root / "reports" / "nuclei",
        profile="low-medium",
        timeout=30,
        concurrency=2,
        rate_limit=10,
    )

    assert command.args[0] == "nuclei"
    assert "-jsonl" in command.args
    assert "-severity" in command.args
    assert "low,medium" in command.args
    assert command.output_files["jsonl"].endswith(".jsonl")
    assert "nuclei_" in command.output_files["jsonl"]


@pytest.mark.parametrize(
    ("profile", "expected_value"),
    [
        ("critical", "critical"),
        ("high", "high"),
        ("medium-high", "medium,high"),
    ],
)
def test_scanner_service_builds_real_nuclei_severity_profiles(runtime_root, profile, expected_value):
    service = ScannerService(runtime_root)

    command = service.build_nuclei_command(
        ["http://localhost"],
        runtime_root / "reports" / "nuclei",
        profile=profile,
    )

    assert "-severity" in command.args
    assert expected_value in command.args


def test_scanner_service_uses_nuclei_target_list_file(runtime_root):
    service = ScannerService(runtime_root)

    command = service.build_nuclei_command(
        ["http://localhost", "http://127.0.0.1"],
        runtime_root / "reports" / "nuclei",
    )

    assert "-l" in command.args
    assert "nuclei-targets.txt" in command.args[command.args.index("-l") + 1]


def test_scanner_service_parse_nmap_xml(runtime_root):
    service = ScannerService(runtime_root)

    hosts = service.parse_nmap_xml(NMAP_XML)

    assert hosts[0]["host"] == "127.0.0.1"
    assert hosts[0]["hostnames"][0]["name"] == "localhost"
    assert hosts[0]["os"] == "Linux 6.x"
    assert hosts[0]["ports"][0]["service"] == "http"
    assert hosts[0]["ports"][0]["version"] == "nginx 1.25"
    assert "nginx" in hosts[0]["ports"][0]["technologies"]


def test_scanner_service_builds_controlled_nse_args(runtime_root):
    service = ScannerService(runtime_root)

    command = service.build_nmap_command(
        "127.0.0.1",
        runtime_root / "reports" / "nmap",
        nse_profile="safe",
    )

    assert "--script" in command.args
    assert "safe" in command.args

    with pytest.raises(ValidationError):
        service.build_nmap_command(
            "127.0.0.1",
            runtime_root / "reports" / "nmap",
            nse_scripts=["vuln"],
        )


def test_scanner_service_builds_nuclei_tags_and_severities(runtime_root):
    service = ScannerService(runtime_root)

    command = service.build_nuclei_command(
        ["http://localhost"],
        runtime_root / "reports" / "nuclei",
        tags=["tech,exposure"],
        severities=["low", "medium"],
    )

    assert "-tags" in command.args
    assert "exposure,tech" in command.args
    assert "-severity" in command.args
    assert "low,medium" in command.args


def test_scanner_service_parse_nmap_xml_errors(runtime_root):
    service = ScannerService(runtime_root)

    with pytest.raises(ScannerParseError):
        service.parse_nmap_xml("")
    with pytest.raises(ScannerParseError):
        service.parse_nmap_xml("<broken")


def test_scanner_service_parse_nuclei_jsonl(runtime_root):
    service = ScannerService(runtime_root)

    findings = service.parse_nuclei_jsonl(NUCLEI_JSONL)

    assert findings[0]["target"] == "http://localhost"
    assert findings[0]["template"] == "test-template"
    assert findings[0]["severity"] == "medium"
    assert service.parse_nuclei_jsonl("") == []


def test_scanner_service_parse_nuclei_jsonl_errors(runtime_root):
    service = ScannerService(runtime_root)

    with pytest.raises(ScannerParseError):
        service.parse_nuclei_jsonl("{broken")


def test_scanner_service_run_nmap_uses_no_shell(runtime_root, monkeypatch):
    service = ScannerService(runtime_root)
    monkeypatch.setattr("services.scanner_service.shutil.which", lambda binary: f"/usr/bin/{binary}")

    def fake_run(args, capture_output, text, timeout, shell):
        assert shell is False
        xml_path = args[args.index("-oX") + 1]
        txt_path = args[args.index("-oN") + 1]
        from pathlib import Path

        Path(xml_path).write_text(NMAP_XML, encoding="utf-8")
        Path(txt_path).write_text("nmap text", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("services.scanner_service.subprocess.run", fake_run)
    command = service.build_nmap_command("127.0.0.1", runtime_root / "reports" / "nmap")

    execution = service.run_nmap(command, runtime_root / "reports" / "nmap")

    assert execution.parsed["hosts"][0]["host"] == "127.0.0.1"


def test_scanner_service_run_nuclei_uses_no_shell(runtime_root, monkeypatch):
    service = ScannerService(runtime_root)
    monkeypatch.setattr("services.scanner_service.shutil.which", lambda binary: f"/usr/bin/{binary}")

    def fake_run(args, capture_output, text, timeout, shell):
        assert shell is False
        output_path = args[args.index("-o") + 1]
        from pathlib import Path

        Path(output_path).write_text(NUCLEI_JSONL, encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("services.scanner_service.subprocess.run", fake_run)
    command = service.build_nuclei_command(["http://localhost"], runtime_root / "reports" / "nuclei")

    execution = service.run_nuclei(command, runtime_root / "reports" / "nuclei")

    assert execution.parsed["findings"][0]["name"] == "Test Finding"


def test_scanner_service_generates_marked_simulated_outputs(runtime_root):
    service = ScannerService(runtime_root)
    nmap_command = service.build_nmap_command("127.0.0.1", runtime_root / "reports" / "nmap")
    nuclei_command = service.build_nuclei_command(["http://localhost"], runtime_root / "reports" / "nuclei")

    nmap_execution = service.simulate_nmap(nmap_command, runtime_root / "reports" / "nmap", "127.0.0.1")
    nuclei_execution = service.simulate_nuclei(
        nuclei_command,
        runtime_root / "reports" / "nuclei",
        ["http://localhost"],
    )

    assert nmap_execution.simulated is True
    assert nuclei_execution.simulated is True
    assert "Resultado simulado" in (runtime_root / nmap_execution.output_files["txt"]).read_text(encoding="utf-8")
    assert nuclei_execution.parsed["findings"][0]["template"] == "simulated-authorized-demo"


def test_scanner_service_missing_tools_and_timeout(runtime_root, monkeypatch):
    service = ScannerService(runtime_root)
    command = service.build_nmap_command("127.0.0.1", runtime_root / "reports" / "nmap")

    monkeypatch.setattr("services.scanner_service.shutil.which", lambda binary: None)
    with pytest.raises(ScannerToolUnavailable):
        service.run_nmap(command, runtime_root / "reports" / "nmap")

    monkeypatch.setattr("services.scanner_service.shutil.which", lambda binary: f"/usr/bin/{binary}")

    def timeout_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="nmap", timeout=1)

    monkeypatch.setattr("services.scanner_service.subprocess.run", timeout_run)
    with pytest.raises(ScannerTimeoutError):
        service.run_nmap(command, runtime_root / "reports" / "nmap")
