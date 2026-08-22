"""Smart scan planning, Nmap/Nuclei correlation, and risk scoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


WEB_SERVICE_HINTS = {
    "http",
    "https",
    "http-alt",
    "http-proxy",
    "ssl/http",
    "http-waf",
    "http-title",
    "nginx",
    "apache",
    "iis",
    "tomcat",
    "jetty",
    "gunicorn",
    "node",
}

DEFAULT_WEB_PORTS = {
    80: "http",
    81: "http",
    443: "https",
    8000: "http",
    8008: "http",
    8080: "http",
    8081: "http",
    8443: "https",
    8888: "http",
    9000: "http",
    9443: "https",
}

SEVERITY_WEIGHTS = {
    "critical": 90,
    "high": 75,
    "medium": 50,
    "low": 25,
    "info": 10,
    "informational": 10,
    "unknown": 5,
}


@dataclass(frozen=True)
class SmartEndpoint:
    host: str
    ip: str
    hostname: str
    port: int
    protocol: str
    service: str
    scheme: str
    url: str
    version: str = ""
    confidence: str = "medium"
    source: str = "nmap"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SmartScanService:
    """Selects meaningful web endpoints and correlates scanner outputs."""

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        self.settings = settings or {}
        configured_ports = (
            self.settings.get("scanners", {})
            .get("smart", {})
            .get("web_ports", [])
        )
        self.extra_web_ports = {int(port) for port in configured_ports if str(port).isdigit()}

    def select_web_endpoints(self, hosts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
        endpoints: list[SmartEndpoint] = []
        decisions: list[str] = []
        seen: set[tuple[str, int, str]] = set()
        for host in hosts:
            host_ip = str(host.get("ip") or host.get("host") or "")
            hostname = self._primary_hostname(host)
            target = hostname or host_ip
            for port in host.get("ports", []):
                if port.get("state") != "open":
                    decisions.append(
                        f"Ignorado {target}:{port.get('port')} porque a porta nao esta aberta."
                    )
                    continue
                try:
                    port_number = int(port.get("port"))
                except (TypeError, ValueError):
                    decisions.append(f"Ignorado {target}:{port.get('port')} por porta invalida.")
                    continue
                service = str(port.get("service") or "").lower()
                if not self._is_web_candidate(port_number, service):
                    decisions.append(
                        f"Ignorado {target}:{port_number}/{service or 'unknown'} porque nao parece web."
                    )
                    continue
                scheme = self._scheme(port_number, service)
                key = (target, port_number, scheme)
                if key in seen:
                    continue
                seen.add(key)
                endpoint = SmartEndpoint(
                    host=target,
                    ip=host_ip,
                    hostname=hostname,
                    port=port_number,
                    protocol=str(port.get("protocol") or "tcp"),
                    service=service or "unknown",
                    scheme=scheme,
                    url=f"{scheme}://{target}:{port_number}",
                    version=str(port.get("version") or ""),
                    confidence="high" if service in WEB_SERVICE_HINTS else "medium",
                )
                endpoints.append(endpoint)
                decisions.append(f"Selecionado {endpoint.url} para Nuclei a partir de Nmap.")
        return [endpoint.to_dict() for endpoint in endpoints], decisions

    def correlate(
        self,
        hosts: list[dict[str, Any]],
        nuclei_findings: list[dict[str, Any]],
        endpoints: list[dict[str, Any]] | None = None,
        decisions: list[str] | None = None,
    ) -> dict[str, Any]:
        selected_endpoints, generated_decisions = (
            (endpoints, decisions or []) if endpoints is not None else self.select_web_endpoints(hosts)
        )
        selected_endpoints = selected_endpoints or []
        decisions = list(decisions or generated_decisions)
        findings = [
            self._correlated_finding(finding, selected_endpoints)
            for finding in nuclei_findings
        ]
        findings.sort(key=lambda item: item["risk_score"], reverse=True)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hosts": hosts,
            "web_endpoints": selected_endpoints,
            "findings": findings,
            "decisions": decisions,
            "summary": self._summary(hosts, selected_endpoints, findings),
        }

    def _correlated_finding(
        self, finding: dict[str, Any], endpoints: list[dict[str, Any]]
    ) -> dict[str, Any]:
        endpoint_text = str(finding.get("endpoint") or finding.get("target") or "")
        matched = self._match_endpoint(endpoint_text, endpoints)
        severity = str(finding.get("severity") or "unknown").lower()
        score = self._risk_score(severity, matched, finding)
        target = matched.get("url") if matched else endpoint_text
        return {
            "title": finding.get("name") or finding.get("template") or "Nuclei finding",
            "target": target,
            "host": matched.get("host") if matched else self._host_from_url(endpoint_text),
            "port": matched.get("port") if matched else self._port_from_url(endpoint_text),
            "service": matched.get("service") if matched else "unknown",
            "technology": matched.get("version") if matched else "",
            "template": finding.get("template") or "",
            "severity": severity,
            "risk": self._risk_label(score),
            "risk_score": score,
            "confidence": "high" if matched else "medium",
            "evidence": finding.get("description") or finding.get("endpoint") or endpoint_text,
            "recommendation": self._recommendation(severity, matched),
            "origin": "nmap+nuclei" if matched else "nuclei",
            "timestamp": finding.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        }

    def _summary(
        self,
        hosts: list[dict[str, Any]],
        endpoints: list[dict[str, Any]],
        findings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        severities: dict[str, int] = {}
        risks: dict[str, int] = {}
        open_ports = 0
        for host in hosts:
            open_ports += len([port for port in host.get("ports", []) if port.get("state") == "open"])
        for finding in findings:
            severity = str(finding.get("severity") or "unknown")
            risk = str(finding.get("risk") or "Informativo")
            severities[severity] = severities.get(severity, 0) + 1
            risks[risk] = risks.get(risk, 0) + 1
        return {
            "hosts": len(hosts),
            "open_ports": open_ports,
            "web_endpoints": len(endpoints),
            "findings": len(findings),
            "severities": severities,
            "risks": risks,
        }

    def _is_web_candidate(self, port: int, service: str) -> bool:
        return port in DEFAULT_WEB_PORTS or port in self.extra_web_ports or any(
            hint in service for hint in WEB_SERVICE_HINTS
        )

    def _scheme(self, port: int, service: str) -> str:
        if port in {443, 8443, 9443} or "https" in service or "ssl" in service or "tls" in service:
            return "https"
        return "http"

    def _primary_hostname(self, host: dict[str, Any]) -> str:
        hostnames = host.get("hostnames") or []
        if isinstance(hostnames, list) and hostnames:
            first = hostnames[0]
            if isinstance(first, dict):
                return str(first.get("name") or "")
            return str(first)
        return str(host.get("hostname") or "")

    def _match_endpoint(self, endpoint_text: str, endpoints: list[dict[str, Any]]) -> dict[str, Any]:
        parsed_host = self._host_from_url(endpoint_text)
        parsed_port = self._port_from_url(endpoint_text)
        for endpoint in endpoints:
            candidates = {str(endpoint.get("host")), str(endpoint.get("ip")), str(endpoint.get("hostname"))}
            if parsed_host in candidates and (parsed_port is None or parsed_port == endpoint.get("port")):
                return endpoint
            if str(endpoint.get("url")) and str(endpoint.get("url")) in endpoint_text:
                return endpoint
        return {}

    def _host_from_url(self, value: str) -> str:
        if not value:
            return ""
        parsed = urlparse(value if "://" in value else f"//{value}")
        return parsed.hostname or ""

    def _port_from_url(self, value: str) -> int | None:
        if not value:
            return None
        parsed = urlparse(value if "://" in value else f"//{value}")
        if parsed.port:
            return parsed.port
        if parsed.scheme == "https":
            return 443
        if parsed.scheme == "http":
            return 80
        return None

    def _risk_score(self, severity: str, endpoint: dict[str, Any], finding: dict[str, Any]) -> int:
        score = SEVERITY_WEIGHTS.get(severity, SEVERITY_WEIGHTS["unknown"])
        if endpoint:
            score += 8
        if endpoint.get("version"):
            score += 5
        if finding.get("description"):
            score += 4
        if endpoint.get("port") in {80, 443, 8080, 8443}:
            score += 3
        return min(score, 100)

    def _risk_label(self, score: int) -> str:
        if score >= 90:
            return "Critico"
        if score >= 70:
            return "Alto"
        if score >= 40:
            return "Medio"
        if score >= 20:
            return "Baixo"
        return "Informativo"

    def _recommendation(self, severity: str, endpoint: dict[str, Any]) -> str:
        service = endpoint.get("service") if endpoint else "servico"
        if severity in {"critical", "high"}:
            return f"Priorize validacao manual, reduza exposicao do {service} e aplique correcao do fornecedor."
        if severity == "medium":
            return f"Planeje remediacao, revise configuracao do {service} e confirme o achado manualmente."
        if severity == "low":
            return f"Revise endurecimento do {service} e registre excecao se o risco for aceito."
        return "Use como informacao de inventario e mantenha monitoramento de mudancas."
