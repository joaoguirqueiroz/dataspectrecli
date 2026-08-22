from __future__ import annotations

from services.baseline_service import BaselineService


def scan_payload(version: str = "nginx 1.25", finding: bool = True):
    findings = []
    if finding:
        findings.append(
            {
                "target": "http://app.local:80",
                "template": "exposure-test",
                "severity": "high",
            }
        )
    return {
        "correlation": {
            "hosts": [
                {
                    "host": "192.168.1.10",
                    "ports": [
                        {
                            "port": "80",
                            "protocol": "tcp",
                            "state": "open",
                            "service": "http",
                            "version": version,
                        }
                    ],
                }
            ],
            "findings": findings,
        }
    }


def test_baseline_create_and_compare_unchanged(runtime_root):
    service = BaselineService(runtime_root)

    record = service.create_baseline("Lab Principal", scan_payload())
    result = service.compare("Lab Principal", scan_payload())

    assert record.name == "lab-principal"
    assert result["summary"]["status"] == "unchanged"
    assert result["persistent_findings"]


def test_baseline_compare_detects_new_service_and_version_change(runtime_root):
    service = BaselineService(runtime_root)
    service.create_baseline("lab", scan_payload("nginx 1.25", finding=False))
    current = scan_payload("nginx 1.26", finding=True)
    current["correlation"]["hosts"][0]["ports"].append(
        {
            "port": "443",
            "protocol": "tcp",
            "state": "open",
            "service": "https",
            "version": "nginx 1.26",
        }
    )

    result = service.compare("lab", current)

    assert result["summary"]["status"] == "changed"
    assert result["new_services"]
    assert result["new_findings"]
    assert result["version_changes"]
