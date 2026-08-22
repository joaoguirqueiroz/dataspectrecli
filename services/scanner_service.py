"""Safe wrappers for authorized Nmap and Nuclei execution."""

from __future__ import annotations

import ipaddress
import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree

from core.exceptions import ValidationError
from services.storage import ensure_dir


AUTHORIZED_USE_NOTICE = (
    "Confirme que voce possui autorizacao para analisar este alvo. "
    "Use esta ferramenta apenas em ambientes proprios, laboratorios, redes internas "
    "ou ativos autorizados."
)

AUTHORIZATION_BLOCK_MESSAGE = (
    "Execucao bloqueada. Use --authorize somente se voce possui autorizacao "
    "para analisar este alvo."
)

ETHICAL_NOTICE = (
    "Use esta ferramenta apenas em redes, sistemas, sites e APIs proprios, autorizados "
    "ou ambientes de laboratorio. O uso contra terceiros sem autorizacao e proibido."
)

DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[A-Za-z]{2,63}$"
)
PORTS_PATTERN = re.compile(r"^[0-9,-]{1,128}$")


class ScannerError(Exception):
    """Base class for scanner service failures."""


class ScannerToolUnavailable(ScannerError):
    """Raised when the requested external scanner is not installed."""


class ScannerExecutionError(ScannerError):
    """Raised when a scanner process exits unsuccessfully."""


class ScannerTimeoutError(ScannerError):
    """Raised when a scanner process times out."""


class ScannerParseError(ScannerError):
    """Raised when scanner output cannot be parsed."""


@dataclass(frozen=True)
class ScannerCommand:
    tool: str
    args: list[str]
    profile: str
    timeout: int
    output_files: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScannerExecution:
    tool: str
    profile: str
    command: list[str]
    return_code: int
    output_files: dict[str, str]
    parsed: dict[str, Any] = field(default_factory=dict)
    simulated: bool = False
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ScannerService:
    """Validates targets, builds safe commands, executes tools, and parses output."""

    NMAP_PROFILE_ALIASES = {
        "quick": "quick",
        "rapido": "quick",
        "rapida": "quick",
        "varredura-rapida": "quick",
        "basic": "basic",
        "basico": "basic",
        "services": "services",
        "servicos": "services",
        "deteccao-servicos": "services",
        "scripts": "scripts",
        "scripts-padrao": "scripts",
        "scripts_padrao": "scripts",
        "servicos-scripts": "services-scripts",
        "servicos_scripts": "services-scripts",
        "services-scripts": "services-scripts",
        "services_scripts": "services-scripts",
        "ports": "ports",
        "portas": "ports",
        "portas-especificas": "ports",
        "custom": "custom",
        "personalizado": "custom",
    }
    NMAP_PROFILE_INFO = {
        "quick": {
            "name": "Varredura rapida",
            "description": "Executa uma varredura rapida nas portas mais comuns usando nmap -T4 -F.",
            "when_to_use": "Use para uma primeira triagem autorizada e rapida.",
            "base_command": "nmap -T4 -F TARGET",
        },
        "basic": {
            "name": "Servicos e scripts",
            "description": "Identifica servicos/versoes e executa scripts padrao usando nmap -sV -sC.",
            "when_to_use": "Use como perfil padrao para inventario autorizado equilibrado.",
            "base_command": "nmap -sV -sC TARGET",
        },
        "services": {
            "name": "Deteccao de servicos",
            "description": "Identifica quais servicos e versoes estao nas portas abertas usando nmap -sV.",
            "when_to_use": "Use quando precisar de inventario de servicos sem scripts NSE.",
            "base_command": "nmap -sV TARGET",
        },
        "scripts": {
            "name": "Scripts padrao",
            "description": "Executa scripts padrao seguros do Nmap usando nmap -sC.",
            "when_to_use": "Use apos confirmar que scripts padrao estao dentro do escopo autorizado.",
            "base_command": "nmap -sC TARGET",
        },
        "services-scripts": {
            "name": "Servicos e scripts",
            "description": "Combina deteccao de servicos e scripts padrao usando nmap -sV -sC.",
            "when_to_use": "Use para uma visao mais completa de servicos autorizados.",
            "base_command": "nmap -sV -sC TARGET",
        },
        "ports": {
            "name": "Portas especificas",
            "description": "Analisa apenas as portas informadas usando nmap -p PORTAS.",
            "when_to_use": "Use quando o escopo autoriza somente portas especificas.",
            "base_command": "nmap -p PORTAS TARGET",
        },
        "custom": {
            "name": "Perfil personalizado",
            "description": "Executa somente flags personalizadas permitidas pela politica local.",
            "when_to_use": "Use apenas com confirmacao extra e escopo documentado.",
            "base_command": "nmap FLAGS_PERMITIDAS TARGET",
        },
    }
    NMAP_CUSTOM_FLAGS = {"-sV", "-sC", "--version-light", "-Pn", "-F", "-T4"}
    NMAP_NSE_PROFILE_SCRIPTS = {
        "default-safe": ["default", "safe"],
        "discovery": ["discovery"],
        "version": ["version"],
        "safe": ["safe"],
    }

    NUCLEI_PROFILE_ALIASES = {
        "basic": "basic",
        "basico": "basic",
        "analise-basica": "basic",
        "technologies": "technologies",
        "tecnologias": "technologies",
        "exposure": "exposure",
        "exposicao": "exposure",
        "low-medium": "low-medium",
        "baixa-media": "low-medium",
        "medium-high": "medium-high",
        "media-alta": "medium-high",
        "medias-altas": "medium-high",
        "high": "high",
        "alta": "high",
        "altas": "high",
        "critical": "critical",
        "critica": "critical",
        "criticas": "critical",
        "template": "template",
        "template-especifico": "template",
        "template_especifico": "template",
        "custom": "custom",
        "personalizado": "custom",
    }
    NUCLEI_PROFILE_INFO = {
        "basic": {
            "name": "Analise basica",
            "description": "Executa o Nuclei contra o alvo informado usando nuclei -u TARGET.",
            "when_to_use": "Use para uma validacao inicial autorizada.",
            "base_command": "nuclei -u TARGET",
        },
        "technologies": {
            "name": "Tecnologias detectadas",
            "description": "Usa templates com tag tech para identificar tecnologias.",
            "when_to_use": "Use para complementar inventario web autorizado.",
            "base_command": "nuclei -u TARGET -tags tech",
        },
        "exposure": {
            "name": "Exposicoes comuns",
            "description": "Procura exposicoes e configuracoes comuns com tags controladas.",
            "when_to_use": "Use para revisar exposicoes conhecidas em ativos proprios.",
            "base_command": "nuclei -u TARGET -tags exposure,misconfig",
        },
        "low-medium": {
            "name": "Vulnerabilidades baixas e medias",
            "description": "Filtra achados de severidade baixa e media.",
            "when_to_use": "Use para revisao de melhoria continua.",
            "base_command": "nuclei -u TARGET -severity low,medium",
        },
        "medium-high": {
            "name": "Vulnerabilidades medias e altas",
            "description": "Filtra achados de severidade media e alta.",
            "when_to_use": "Use para priorizar riscos relevantes sem criticos.",
            "base_command": "nuclei -u TARGET -severity medium,high",
        },
        "high": {
            "name": "Vulnerabilidades altas",
            "description": "Procura apenas achados classificados como severidade alta.",
            "when_to_use": "Use com confirmacao extra em escopo autorizado.",
            "base_command": "nuclei -u TARGET -severity high",
        },
        "critical": {
            "name": "Vulnerabilidades criticas",
            "description": "Procura apenas achados classificados como severidade critica.",
            "when_to_use": "Use com confirmacao extra e janela autorizada.",
            "base_command": "nuclei -u TARGET -severity critical",
        },
        "template": {
            "name": "Usar template especifico",
            "description": "Executa um template ou caminho de templates informado com -t.",
            "when_to_use": "Use para validar um controle especifico autorizado.",
            "base_command": "nuclei -u TARGET -t CAMINHO_DO_TEMPLATE",
        },
        "custom": {
            "name": "Perfil personalizado",
            "description": "Executa templates, tags e severidades explicitamente definidos.",
            "when_to_use": "Use apenas com confirmacao extra e escopo documentado.",
            "base_command": "nuclei -u TARGET OPCOES_PERMITIDAS",
        },
    }
    NUCLEI_SEVERITIES = {"info", "low", "medium", "high", "critical"}

    def __init__(self, root_path: Path, settings: dict[str, Any] | None = None) -> None:
        self.root_path = root_path.resolve()
        self.settings = settings or {}

    def is_installed(self, binary: str) -> bool:
        return shutil.which(binary) is not None

    def default_limits(self) -> dict[str, int]:
        defaults = self.settings.get("scanners", {}).get("defaults", {})
        return {
            "timeout": self._positive_int(defaults.get("timeout"), 60, "timeout"),
            "concurrency": self._positive_int(defaults.get("concurrency"), 5, "concurrency"),
            "rate_limit": self._positive_int(defaults.get("rate_limit"), 25, "rate_limit"),
            "max_targets": self._positive_int(defaults.get("max_targets"), 25, "max_targets"),
        }

    def normalize_nmap_profile(self, value: str | None) -> str:
        return self._normalize_profile(value or "basic", self.NMAP_PROFILE_ALIASES, "Nmap profile")

    def normalize_nuclei_profile(self, value: str | None) -> str:
        return self._normalize_profile(value or "basic", self.NUCLEI_PROFILE_ALIASES, "Nuclei profile")

    def nmap_profile_info(self, profile: str | None) -> dict[str, str]:
        selected = self.normalize_nmap_profile(profile)
        return dict(self.NMAP_PROFILE_INFO[selected])

    def nuclei_profile_info(self, profile: str | None) -> dict[str, str]:
        selected = self.normalize_nuclei_profile(profile)
        return dict(self.NUCLEI_PROFILE_INFO[selected])

    def validate_nmap_target(self, target: str) -> str:
        clean = self._clean_value(target, "target")
        if self._is_valid_ip_or_domain(clean):
            return clean
        try:
            network = ipaddress.ip_network(clean, strict=False)
        except ValueError as exc:
            raise ValidationError(f"Invalid Nmap target '{target}'.") from exc
        if not (network.is_private or network.is_loopback or network.is_link_local):
            raise ValidationError("CIDR ranges must be private, loopback, or link-local.")
        if network.num_addresses > 4096:
            raise ValidationError("CIDR range is too large for the safe default policy.")
        return clean

    def validate_nuclei_target(self, target: str) -> str:
        clean = self._clean_value(target, "target")
        parsed = urlparse(clean if "://" in clean else f"//{clean}")
        host = parsed.hostname
        if not host:
            raise ValidationError(f"Invalid Nuclei target '{target}'.")
        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            raise ValidationError("Nuclei URLs must use http or https.")
        if not self._is_valid_ip_or_domain(host):
            raise ValidationError(f"Invalid Nuclei target '{target}'.")
        return clean

    def validate_nuclei_targets(self, targets: list[str], max_targets: int | None = None) -> list[str]:
        limit = max_targets or self.default_limits()["max_targets"]
        if not targets:
            raise ValidationError("At least one Nuclei target is required.")
        if len(targets) > limit:
            raise ValidationError(f"Target list exceeds configured maximum of {limit}.")
        return [self.validate_nuclei_target(target) for target in targets]

    def build_nmap_command(
        self,
        target: str,
        output_dir: Path,
        profile: str = "basic",
        ports: str | None = None,
        custom_flags: list[str] | None = None,
        nse_profile: str | None = None,
        nse_scripts: list[str] | None = None,
        timeout: int | None = None,
    ) -> ScannerCommand:
        selected_profile = self.normalize_nmap_profile(profile)
        selected_target = self.validate_nmap_target(target)
        selected_timeout = self._positive_int(timeout, self.default_limits()["timeout"], "timeout")
        output_paths = self.nmap_output_paths(output_dir)
        args = ["nmap"]
        if selected_profile == "quick":
            args.extend(["-T4", "-F"])
        elif selected_profile == "basic":
            args.extend(["-sV", "-sC"])
        elif selected_profile == "services":
            args.extend(["-sV"])
        elif selected_profile == "scripts":
            args.extend(["-sC"])
        elif selected_profile == "services-scripts":
            args.extend(["-sV", "-sC"])
        elif selected_profile == "ports":
            clean_ports = self.validate_ports(ports)
            args.extend(["-p", clean_ports])
        elif selected_profile == "custom":
            args.extend(self.validate_custom_nmap_flags(custom_flags or []))
            if ports:
                args.extend(["-p", self.validate_ports(ports)])
        script_args = self.build_nse_script_args(nse_profile, nse_scripts)
        args.extend(script_args)
        args.extend(["-oN", str(output_paths["txt"]), "-oX", str(output_paths["xml"])])
        args.append(selected_target)
        return ScannerCommand(
            "nmap",
            args,
            selected_profile,
            selected_timeout,
            {key: str(path) for key, path in output_paths.items()},
        )

    def build_nuclei_command(
        self,
        targets: list[str],
        output_dir: Path,
        profile: str = "basic",
        templates: list[str] | None = None,
        template_dirs: list[str] | None = None,
        tags: list[str] | None = None,
        severities: list[str] | None = None,
        timeout: int | None = None,
        concurrency: int | None = None,
        rate_limit: int | None = None,
        max_targets: int | None = None,
    ) -> ScannerCommand:
        limits = self.default_limits()
        selected_profile = self.normalize_nuclei_profile(profile)
        selected_timeout = self._positive_int(timeout, limits["timeout"], "timeout")
        selected_concurrency = self._bounded_int(
            concurrency, limits["concurrency"], "concurrency", maximum=100
        )
        selected_rate = self._bounded_int(rate_limit, limits["rate_limit"], "rate_limit", maximum=500)
        selected_targets = self.validate_nuclei_targets(targets, max_targets or limits["max_targets"])
        output_path = self.nuclei_output_path(output_dir)
        args = ["nuclei"]
        if selected_profile == "technologies":
            args.extend(["-tags", "tech"])
        elif selected_profile == "exposure":
            args.extend(["-tags", "exposure,misconfig"])
        elif selected_profile == "low-medium":
            args.extend(["-severity", "low,medium"])
        elif selected_profile == "medium-high":
            args.extend(["-severity", "medium,high"])
        elif selected_profile == "high":
            args.extend(["-severity", "high"])
        elif selected_profile == "critical":
            args.extend(["-severity", "critical"])
        elif selected_profile in {"template", "custom"}:
            args.extend(self.validate_nuclei_templates(templates or []))
        if template_dirs:
            args.extend(self.validate_nuclei_templates(template_dirs))
        clean_tags = self.validate_nuclei_tags(tags or [])
        if clean_tags:
            args.extend(["-tags", ",".join(clean_tags)])
        clean_severities = self.validate_nuclei_severities(severities or [])
        if clean_severities:
            args.extend(["-severity", ",".join(clean_severities)])
        if len(selected_targets) == 1:
            args.extend(["-u", selected_targets[0]])
        else:
            target_file = self._write_target_file(output_dir, selected_targets)
            args.extend(["-l", str(target_file)])
        args.extend(
            [
                "-jsonl",
                "-silent",
                "-timeout",
                str(selected_timeout),
                "-c",
                str(selected_concurrency),
                "-rate-limit",
                str(selected_rate),
                "-o",
                str(output_path),
            ]
        )
        return ScannerCommand(
            "nuclei",
            args,
            selected_profile,
            selected_timeout,
            {"jsonl": str(output_path)},
        )

    def run_nmap(self, command: ScannerCommand, output_dir: Path) -> ScannerExecution:
        if not self.is_installed("nmap"):
            raise ScannerToolUnavailable(
                "Nmap nao encontrado no sistema. Instale com sudo apt install -y nmap, "
                "sudo dnf install -y nmap ou sudo pacman -S nmap."
            )
        ensure_dir(output_dir)
        started_at = datetime.now(timezone.utc).isoformat()
        try:
            completed = subprocess.run(
                command.args,
                capture_output=True,
                text=True,
                timeout=command.timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ScannerTimeoutError(
                "A execucao demorou mais que o esperado e foi encerrada com seguranca."
            ) from exc
        output_paths = {key: Path(value) for key, value in command.output_files.items()}
        if not output_paths["txt"].exists():
            output_paths["txt"].write_text(completed.stdout or completed.stderr or "", encoding="utf-8")
        if not output_paths["xml"].exists() and completed.stdout.strip().startswith("<"):
            output_paths["xml"].write_text(completed.stdout, encoding="utf-8")
        if completed.returncode != 0:
            raise ScannerExecutionError(completed.stderr or "Nmap execution failed.")
        parsed = self.parse_nmap_xml(output_paths["xml"])
        return ScannerExecution(
            tool="nmap",
            profile=command.profile,
            command=command.args,
            return_code=completed.returncode,
            output_files={key: str(path) for key, path in output_paths.items()},
            parsed={"hosts": parsed},
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

    def run_nuclei(self, command: ScannerCommand, output_dir: Path) -> ScannerExecution:
        if not self.is_installed("nuclei"):
            raise ScannerToolUnavailable(
                "Nuclei nao encontrado no sistema. Consulte o README para instalar com Go "
                "ou pelo metodo recomendado da sua distribuicao."
            )
        ensure_dir(output_dir)
        started_at = datetime.now(timezone.utc).isoformat()
        try:
            completed = subprocess.run(
                command.args,
                capture_output=True,
                text=True,
                timeout=command.timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ScannerTimeoutError(
                "A execucao demorou mais que o esperado e foi encerrada com seguranca."
            ) from exc
        output_path = Path(command.output_files["jsonl"])
        if not output_path.exists():
            output_path.write_text(completed.stdout or "", encoding="utf-8")
        if completed.returncode != 0:
            raise ScannerExecutionError(completed.stderr or "Nuclei execution failed.")
        findings = self.parse_nuclei_jsonl(output_path)
        return ScannerExecution(
            tool="nuclei",
            profile=command.profile,
            command=command.args,
            return_code=completed.returncode,
            output_files={"jsonl": str(output_path)},
            parsed={"findings": findings},
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

    def simulate_nmap(self, command: ScannerCommand, output_dir: Path, target: str) -> ScannerExecution:
        ensure_dir(output_dir)
        output_paths = {key: Path(value) for key, value in command.output_files.items()}
        host = self.validate_nmap_target(target)
        xml = _simulated_nmap_xml(host)
        txt = (
            "Resultado simulado: estes dados sao ficticios e servem apenas para "
            "demonstracao da interface e dos relatorios.\n"
            f"Alvo: {host}\n"
            "Portas abertas simuladas: 80/tcp http, 443/tcp https\n"
        )
        output_paths["xml"].write_text(xml, encoding="utf-8")
        output_paths["txt"].write_text(txt, encoding="utf-8")
        parsed = self.parse_nmap_xml(xml)
        return ScannerExecution(
            tool="nmap",
            profile=command.profile,
            command=command.args,
            return_code=0,
            output_files={key: str(path) for key, path in output_paths.items()},
            parsed={"hosts": parsed},
            simulated=True,
        )

    def simulate_nuclei(
        self, command: ScannerCommand, output_dir: Path, targets: list[str]
    ) -> ScannerExecution:
        ensure_dir(output_dir)
        output_path = Path(command.output_files["jsonl"])
        selected_targets = self.validate_nuclei_targets(targets)
        lines = []
        for target in selected_targets:
            endpoint = target if target.startswith(("http://", "https://")) else f"http://{target}"
            lines.append(
                json.dumps(
                    {
                        "template-id": "simulated-authorized-demo",
                        "host": endpoint,
                        "matched-at": endpoint,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "info": {
                            "name": "Resultado simulado de demonstracao",
                            "severity": "info",
                            "description": (
                                "Resultado simulado: estes dados sao ficticios e servem apenas "
                                "para demonstracao da interface e dos relatorios."
                            ),
                        },
                    },
                    ensure_ascii=False,
                )
            )
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        findings = self.parse_nuclei_jsonl(output_path)
        return ScannerExecution(
            tool="nuclei",
            profile=command.profile,
            command=command.args,
            return_code=0,
            output_files={"jsonl": str(output_path)},
            parsed={"findings": findings},
            simulated=True,
        )

    def parse_nmap_xml(self, path_or_text: Path | str) -> list[dict[str, Any]]:
        text = Path(path_or_text).read_text(encoding="utf-8") if isinstance(path_or_text, Path) else path_or_text
        if not text.strip():
            raise ScannerParseError("Nmap XML output is empty.")
        try:
            root = ElementTree.fromstring(text)
        except ElementTree.ParseError as exc:
            raise ScannerParseError("Could not parse Nmap XML output.") from exc
        hosts: list[dict[str, Any]] = []
        for host in root.findall("host"):
            address_node = host.find("address")
            status_node = host.find("status")
            hostnames = [
                {"name": item.get("name", ""), "type": item.get("type", "")}
                for item in host.findall("./hostnames/hostname")
                if item.get("name")
            ]
            os_matches = [
                {
                    "name": item.get("name", ""),
                    "accuracy": item.get("accuracy", ""),
                }
                for item in host.findall("./os/osmatch")
                if item.get("name")
            ]
            host_payload = {
                "host": address_node.get("addr") if address_node is not None else "",
                "ip": address_node.get("addr") if address_node is not None else "",
                "hostnames": hostnames,
                "status": status_node.get("state") if status_node is not None else "unknown",
                "os": os_matches[0]["name"] if os_matches else "",
                "os_matches": os_matches,
                "ports": [],
            }
            for port in host.findall("./ports/port"):
                state_node = port.find("state")
                service_node = port.find("service")
                host_payload["ports"].append(
                    {
                        "port": port.get("portid"),
                        "protocol": port.get("protocol"),
                        "state": state_node.get("state") if state_node is not None else "unknown",
                        "service": service_node.get("name") if service_node is not None else "",
                        "version": _service_version(service_node),
                        "product": service_node.get("product") if service_node is not None else "",
                        "technologies": _service_technologies(service_node),
                    }
                )
            hosts.append(host_payload)
        return hosts

    def parse_nuclei_jsonl(self, path_or_text: Path | str) -> list[dict[str, Any]]:
        text = Path(path_or_text).read_text(encoding="utf-8") if isinstance(path_or_text, Path) else path_or_text
        if not text.strip():
            return []
        findings: list[dict[str, Any]] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ScannerParseError("Could not parse Nuclei JSONL output.") from exc
            info = payload.get("info", {}) if isinstance(payload.get("info"), dict) else {}
            findings.append(
                {
                    "target": payload.get("host") or payload.get("matched-at") or payload.get("url", ""),
                    "template": payload.get("template-id") or payload.get("template", ""),
                    "name": info.get("name") or payload.get("name", ""),
                    "severity": info.get("severity") or payload.get("severity", "unknown"),
                    "description": info.get("description", ""),
                    "endpoint": payload.get("matched-at") or payload.get("url", ""),
                    "timestamp": payload.get("timestamp", ""),
                }
            )
        return findings

    def nmap_output_paths(self, output_dir: Path) -> dict[str, Path]:
        ensure_dir(output_dir)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        return {"txt": output_dir / f"nmap_{stamp}.txt", "xml": output_dir / f"nmap_{stamp}.xml"}

    def nuclei_output_path(self, output_dir: Path) -> Path:
        ensure_dir(output_dir)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        return output_dir / f"nuclei_{stamp}.jsonl"

    def validate_ports(self, ports: str | None) -> str:
        clean = self._clean_value(ports or "", "ports")
        if not PORTS_PATTERN.match(clean):
            raise ValidationError("Ports must contain only numbers, commas, and ranges.")
        for chunk in clean.split(","):
            if "-" in chunk:
                start, end = chunk.split("-", 1)
                if int(start) < 1 or int(end) > 65535 or int(start) > int(end):
                    raise ValidationError("Port range is invalid.")
            elif int(chunk) < 1 or int(chunk) > 65535:
                raise ValidationError("Port value is invalid.")
        return clean

    def validate_custom_nmap_flags(self, flags: list[str]) -> list[str]:
        for flag in flags:
            if flag not in self.NMAP_CUSTOM_FLAGS:
                raise ValidationError(f"Custom Nmap flag '{flag}' is not allowed.")
        return list(flags)

    def build_nse_script_args(
        self, nse_profile: str | None = None, scripts: list[str] | None = None
    ) -> list[str]:
        if not nse_profile and not scripts:
            return []
        allowed_profiles = set(
            self.settings.get("scanners", {})
            .get("nmap", {})
            .get("allowed_nse_profiles", [])
        ) or {"default-safe", "discovery", "version", "safe", "custom-authorized"}
        allowed_scripts = set(
            self.settings.get("scanners", {})
            .get("nmap", {})
            .get("allowed_nse_scripts", [])
        ) or {"default", "discovery", "version", "safe", "http-title", "http-headers"}
        selected_scripts: list[str] = []
        if nse_profile:
            clean_profile = self._clean_value(nse_profile, "nse_profile")
            if clean_profile not in allowed_profiles:
                raise ValidationError(f"NSE profile '{clean_profile}' is not allowed.")
            if clean_profile == "custom-authorized":
                selected_scripts.extend(scripts or [])
            else:
                selected_scripts.extend(self.NMAP_NSE_PROFILE_SCRIPTS.get(clean_profile, []))
        selected_scripts.extend(scripts or [])
        if not selected_scripts:
            return []
        clean_scripts = []
        for script in selected_scripts:
            clean = self._clean_value(script, "nse_script")
            if clean not in allowed_scripts:
                raise ValidationError(f"NSE script '{clean}' is not allowed.")
            clean_scripts.append(clean)
        return ["--script", ",".join(sorted(set(clean_scripts)))]

    def validate_nuclei_templates(self, templates: list[str]) -> list[str]:
        args: list[str] = []
        for template in templates:
            clean = self._clean_value(template, "template")
            if any(char in clean for char in (";", "&", "|", "`", "$", "\n", "\r")):
                raise ValidationError("Template value contains unsafe characters.")
            args.extend(["-t", clean])
        return args

    def validate_nuclei_tags(self, tags: list[str]) -> list[str]:
        clean_tags: list[str] = []
        for tag in tags:
            clean = self._clean_value(tag, "tag").lower()
            if not re.fullmatch(r"[a-z0-9_,.-]{1,64}", clean):
                raise ValidationError(f"Nuclei tag '{tag}' is invalid.")
            clean_tags.extend([item for item in clean.split(",") if item])
        return sorted(set(clean_tags))

    def validate_nuclei_severities(self, severities: list[str]) -> list[str]:
        clean_severities: list[str] = []
        for severity in severities:
            clean = self._clean_value(severity, "severity").lower()
            values = [item for item in clean.split(",") if item]
            invalid = [item for item in values if item not in self.NUCLEI_SEVERITIES]
            if invalid:
                raise ValidationError(f"Nuclei severity '{invalid[0]}' is invalid.")
            clean_severities.extend(values)
        return sorted(set(clean_severities))

    def _write_target_file(self, output_dir: Path, targets: list[str]) -> Path:
        ensure_dir(output_dir)
        path = output_dir / "nuclei-targets.txt"
        path.write_text("\n".join(targets) + "\n", encoding="utf-8")
        return path

    def _is_valid_ip_or_domain(self, value: str) -> bool:
        if value == "localhost":
            return True
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return bool(DOMAIN_PATTERN.match(value))

    def _normalize_profile(self, value: str, aliases: dict[str, str], field_name: str) -> str:
        clean = self._clean_value(value, field_name).lower()
        if clean not in aliases:
            raise ValidationError(f"Unsupported {field_name}: {value}.")
        return aliases[clean]

    def _clean_value(self, value: str | None, field_name: str) -> str:
        if value is None or not str(value).strip():
            raise ValidationError(f"{field_name} cannot be empty.")
        clean = str(value).strip()
        if any(char in clean for char in (";", "&", "|", "`", "$", "\n", "\r")):
            raise ValidationError(f"{field_name} contains unsafe characters.")
        return clean

    def _positive_int(self, value: Any, fallback: int, field_name: str) -> int:
        if value is None:
            return fallback
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field_name} must be a positive integer.") from exc
        if parsed <= 0:
            raise ValidationError(f"{field_name} must be a positive integer.")
        return parsed or fallback

    def _bounded_int(self, value: Any, fallback: int, field_name: str, maximum: int) -> int:
        parsed = fallback if value is None else self._positive_int(value, fallback, field_name)
        if parsed > maximum:
            raise ValidationError(f"{field_name} cannot be greater than {maximum}.")
        return parsed


def _service_version(service_node: ElementTree.Element | None) -> str:
    if service_node is None:
        return ""
    parts = [
        service_node.get("product", ""),
        service_node.get("version", ""),
        service_node.get("extrainfo", ""),
    ]
    return " ".join(part for part in parts if part)


def _service_technologies(service_node: ElementTree.Element | None) -> list[str]:
    if service_node is None:
        return []
    values = [
        service_node.get("name", ""),
        service_node.get("product", ""),
        service_node.get("version", ""),
    ]
    return [value for value in values if value]


def _simulated_nmap_xml(host: str) -> str:
    return f"""<?xml version="1.0"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="{host}" addrtype="ipv4"/>
    <hostnames><hostname name="{host}" type="user"/></hostnames>
    <ports>
      <port protocol="tcp" portid="80">
        <state state="open"/>
        <service name="http" product="nginx" version="simulado"/>
      </port>
      <port protocol="tcp" portid="443">
        <state state="open"/>
        <service name="https" product="apache" version="simulado"/>
      </port>
    </ports>
  </host>
</nmaprun>
"""
