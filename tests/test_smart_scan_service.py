from __future__ import annotations

from services.smart_scan_service import SmartScanService


HOSTS = [
    {
        "host": "192.168.1.10",
        "ip": "192.168.1.10",
        "hostnames": [{"name": "app.local", "type": "user"}],
        "status": "up",
        "os": "Linux",
        "ports": [
            {
                "port": "80",
                "protocol": "tcp",
                "state": "open",
                "service": "http",
                "version": "nginx 1.25",
            },
            {
                "port": "22",
                "protocol": "tcp",
                "state": "open",
                "service": "ssh",
                "version": "OpenSSH 9",
            },
            {
                "port": "443",
                "protocol": "tcp",
                "state": "closed",
                "service": "https",
            },
        ],
    }
]


def test_smart_scan_selects_only_web_open_endpoints():
    service = SmartScanService()

    endpoints, decisions = service.select_web_endpoints(HOSTS)

    assert len(endpoints) == 1
    assert endpoints[0]["url"] == "http://app.local:80"
    assert endpoints[0]["service"] == "http"
    assert any("Selecionado" in decision for decision in decisions)
    assert any("ssh" in decision for decision in decisions)


def test_smart_scan_correlates_nuclei_findings_and_prioritizes_risk():
    service = SmartScanService()
    findings = [
        {
            "target": "http://app.local",
            "endpoint": "http://app.local:80/login",
            "template": "exposure-test",
            "name": "Exposed Panel",
            "severity": "high",
            "description": "Admin panel exposed",
            "timestamp": "2026-07-06T10:00:00Z",
        }
    ]

    result = service.correlate(HOSTS, findings)

    assert result["summary"]["web_endpoints"] == 1
    assert result["summary"]["findings"] == 1
    assert result["findings"][0]["origin"] == "nmap+nuclei"
    assert result["findings"][0]["risk"] == "Critico"
    assert result["findings"][0]["risk_score"] >= 90
