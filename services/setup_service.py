"""Environment setup checks and assisted installer support."""

from __future__ import annotations

import importlib.metadata
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from core.constants import (
    APP_VERSION,
    MIN_PYTHON_VERSION,
    REQUIRED_DIRECTORIES,
)
from services.storage import ensure_dir, write_json


STATUS_OK = "OK"
STATUS_MISSING = "Ausente"
STATUS_ERROR = "Erro"
STATUS_MANUAL = "Precisa de acao manual"


@dataclass
class SetupCheck:
    """One environment validation item."""

    name: str
    status: str
    version: str = "-"
    detail: str = ""
    action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SetupCommandResult:
    """Result from a safe installer command."""

    command: list[str]
    return_code: int
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SetupReport:
    """Complete setup verification report."""

    generated_at: str
    root_path: str
    version: str
    operating_system: str
    package_manager: str | None
    overall_status: str
    checks: list[SetupCheck] = field(default_factory=list)
    report_paths: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["checks"] = [check.to_dict() for check in self.checks]
        return payload


Runner = Callable[..., Any]
Which = Callable[[str], str | None]


class SetupService:
    """Checks local prerequisites and writes setup reports."""

    REQUIRED_FILES = (
        "main.py",
        "README.md",
        "CHANGELOG.md",
        "LICENSE",
        "pyproject.toml",
        "requirements.txt",
        "config/default_config.json",
    )

    def __init__(
        self,
        root_path: Path,
        runner: Runner | None = None,
        which: Which | None = None,
    ) -> None:
        self.root_path = root_path.resolve()
        self.runner = runner or subprocess.run
        self.which = which or shutil.which
        self.report_dir = self.root_path / "reports" / "setup"

    def run_checks(
        self,
        include_tools: bool = True,
        include_templates: bool = False,
        write_report_files: bool = True,
    ) -> SetupReport:
        checks = [
            self.check_operating_system(),
            self.check_package_manager(),
            self.check_python(),
            self.check_pip(),
            self.check_git(),
            self.check_requirements_file(),
            self.check_python_dependencies(),
            self.check_permissions(),
            self.check_directory_structure(),
            self.check_required_files(),
            self.check_application_entrypoint(),
        ]
        if include_tools:
            checks.extend([self.check_nmap(), self.check_nuclei()])
        if include_templates:
            checks.append(self.check_nuclei_templates())
        report = self._build_report(checks)
        if write_report_files:
            self.write_report(report)
        return report

    def run_tool_checks(
        self,
        include_templates: bool = False,
        write_report_files: bool = True,
    ) -> SetupReport:
        checks = [
            self.check_operating_system(),
            self.check_package_manager(),
            self.check_nmap(),
            self.check_nuclei(),
        ]
        if include_templates:
            checks.append(self.check_nuclei_templates())
        report = self._build_report(checks)
        if write_report_files:
            self.write_report(report)
        return report

    def check_operating_system(self) -> SetupCheck:
        return SetupCheck(
            name="Sistema operacional",
            status=STATUS_OK,
            version=platform.platform(),
            detail="Ambiente detectado.",
        )

    def check_package_manager(self) -> SetupCheck:
        manager = self.detect_package_manager()
        if manager:
            return SetupCheck(
                name="Gerenciador de pacotes",
                status=STATUS_OK,
                version=manager,
                detail="Gerenciador detectado para instalacoes assistidas.",
            )
        return SetupCheck(
            name="Gerenciador de pacotes",
            status=STATUS_MANUAL,
            detail="apt, dnf, pacman ou yay nao foram encontrados.",
            action="Instale Nmap/Nuclei manualmente conforme sua distribuicao.",
        )

    def check_python(self) -> SetupCheck:
        version = platform.python_version()
        if sys.version_info >= MIN_PYTHON_VERSION:
            return SetupCheck("Python", STATUS_OK, version, "Versao minima atendida.")
        minimum = ".".join(str(part) for part in MIN_PYTHON_VERSION)
        return SetupCheck(
            "Python",
            STATUS_ERROR,
            version,
            f"Python {minimum}+ e obrigatorio.",
            f"Instale Python {minimum}+.",
        )

    def check_pip(self) -> SetupCheck:
        return self._command_check(
            "pip",
            [sys.executable, "-m", "pip", "--version"],
            missing_action="Instale pip ou execute python -m ensurepip --upgrade.",
        )

    def check_git(self) -> SetupCheck:
        return self._binary_check("Git", "git", ["git", "--version"], "Instale Git.")

    def check_nmap(self) -> SetupCheck:
        return self._binary_check(
            "Nmap",
            "nmap",
            ["nmap", "--version"],
            "Instale com sudo apt install -y nmap, sudo dnf install -y nmap ou sudo pacman -S nmap.",
        )

    def check_nuclei(self) -> SetupCheck:
        return self._binary_check(
            "Nuclei",
            "nuclei",
            ["nuclei", "-version"],
            "Instale com go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest.",
        )

    def check_nuclei_templates(self) -> SetupCheck:
        if not self.which("nuclei"):
            return SetupCheck(
                "Templates Nuclei",
                STATUS_MANUAL,
                detail="Nuclei nao instalado. Nao foi possivel verificar templates.",
                action="Instale Nuclei e execute nuclei -update-templates se desejar atualizar templates.",
            )
        return self._command_check(
            "Templates Nuclei",
            ["nuclei", "-tl"],
            missing_action="Verifique templates manualmente com nuclei -tl.",
        )

    def check_requirements_file(self) -> SetupCheck:
        path = self.root_path / "requirements.txt"
        if path.exists():
            return SetupCheck("requirements.txt", STATUS_OK, "presente", "Arquivo encontrado.")
        return SetupCheck(
            "requirements.txt",
            STATUS_ERROR,
            detail="Arquivo requirements.txt nao encontrado.",
            action="Restaure o arquivo requirements.txt na raiz do projeto.",
        )

    def check_python_dependencies(self) -> SetupCheck:
        missing: list[str] = []
        for package in self._runtime_requirement_names():
            try:
                importlib.metadata.distribution(package)
            except importlib.metadata.PackageNotFoundError:
                missing.append(package)
        if missing:
            return SetupCheck(
                "Dependencias Python",
                STATUS_MANUAL,
                detail=f"Pacotes ausentes: {', '.join(sorted(missing))}.",
                action="Execute python -m pip install -r requirements.txt.",
            )
        pip_check = self._run([sys.executable, "-m", "pip", "check"], timeout=20)
        if pip_check.return_code != 0:
            return SetupCheck(
                "Dependencias Python",
                STATUS_MANUAL,
                detail=(pip_check.stdout or pip_check.stderr or "pip check encontrou problemas.").strip(),
                action="Execute python -m pip install -r requirements.txt.",
            )
        return SetupCheck(
            "Dependencias Python",
            STATUS_OK,
            "instaladas",
            "Pacotes obrigatorios encontrados e pip check sem conflitos.",
        )

    def check_permissions(self) -> SetupCheck:
        try:
            ensure_dir(self.report_dir)
            probe = self.report_dir / ".write-test.tmp"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError as exc:
            return SetupCheck(
                "Permissoes basicas",
                STATUS_ERROR,
                detail=f"Falha de escrita em reports/setup: {exc}",
                action="Ajuste permissoes da pasta do projeto.",
            )
        return SetupCheck(
            "Permissoes basicas",
            STATUS_OK,
            "gravacao",
            "Foi possivel criar arquivo temporario seguro em reports/setup.",
        )

    def check_directory_structure(self) -> SetupCheck:
        missing = [str(directory) for directory in REQUIRED_DIRECTORIES if not (self.root_path / directory).exists()]
        if missing:
            return SetupCheck(
                "Estrutura de pastas",
                STATUS_ERROR,
                detail=f"Pastas ausentes: {', '.join(missing)}.",
                action="Restaure a estrutura oficial do projeto.",
            )
        return SetupCheck("Estrutura de pastas", STATUS_OK, "completa", "Pastas obrigatorias encontradas.")

    def check_required_files(self) -> SetupCheck:
        missing = [path for path in self.REQUIRED_FILES if not (self.root_path / path).exists()]
        if missing:
            return SetupCheck(
                "Arquivos obrigatorios",
                STATUS_ERROR,
                detail=f"Arquivos ausentes: {', '.join(missing)}.",
                action="Restaure os arquivos obrigatorios do projeto.",
            )
        return SetupCheck("Arquivos obrigatorios", STATUS_OK, "presentes", "Arquivos essenciais encontrados.")

    def check_application_entrypoint(self) -> SetupCheck:
        if not (self.root_path / "main.py").exists():
            return SetupCheck(
                "Execucao da aplicacao",
                STATUS_ERROR,
                detail="main.py nao encontrado.",
                action="Restaure o ponto de entrada main.py.",
            )
        result = self._run([sys.executable, "main.py", "--version"], timeout=20, cwd=self.root_path)
        if result.return_code == 0:
            version = (result.stdout or "").strip() or "ok"
            return SetupCheck("Execucao da aplicacao", STATUS_OK, version, "Entrada principal responde.")
        return SetupCheck(
            "Execucao da aplicacao",
            STATUS_ERROR,
            detail=(result.stderr or result.stdout or "Falha ao executar main.py --version.").strip(),
            action="Revise imports e dependencias antes de abrir a CLI.",
        )

    def detect_package_manager(self) -> str | None:
        for manager in ("apt", "dnf", "pacman", "yay"):
            if self.which(manager):
                return manager
        return None

    def install_python_dependencies(self) -> SetupCommandResult:
        return self._run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            timeout=300,
            cwd=self.root_path,
        )

    def install_nmap(self, package_manager: str | None = None) -> list[SetupCommandResult]:
        manager = package_manager or self.detect_package_manager()
        if manager == "apt":
            return [
                self._run(["sudo", "apt", "update"], timeout=300),
                self._run(["sudo", "apt", "install", "-y", "nmap"], timeout=300),
            ]
        if manager == "dnf":
            return [self._run(["sudo", "dnf", "install", "-y", "nmap"], timeout=300)]
        if manager == "pacman":
            return [self._run(["sudo", "pacman", "-S", "nmap"], timeout=300)]
        if manager == "yay":
            return [self._run(["yay", "-S", "nmap"], timeout=300)]
        return [
            SetupCommandResult(
                command=[],
                return_code=1,
                stderr="Nenhum gerenciador de pacotes confiavel detectado.",
            )
        ]

    def install_nuclei(self) -> list[SetupCommandResult]:
        if self.which("go"):
            return [
                self._run(
                    ["go", "install", "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"],
                    timeout=600,
                )
            ]
        return [
            SetupCommandResult(
                command=[],
                return_code=1,
                stderr=(
                    "Go nao encontrado. Instale Nuclei manualmente ou instale Go e execute "
                    "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest."
                ),
            )
        ]

    def write_report(self, report: SetupReport) -> SetupReport:
        ensure_dir(self.report_dir)
        text_path = self.report_dir / "setup_report.txt"
        json_path = self.report_dir / "setup_report.json"
        text_path.write_text(self._render_text(report), encoding="utf-8")
        report.report_paths = {
            "txt": str(text_path.relative_to(self.root_path)),
            "json": str(json_path.relative_to(self.root_path)),
        }
        write_json(json_path, report.to_dict())
        return report

    def _build_report(self, checks: list[SetupCheck]) -> SetupReport:
        return SetupReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            root_path=str(self.root_path),
            version=APP_VERSION,
            operating_system=platform.platform(),
            package_manager=self.detect_package_manager(),
            overall_status=self._overall_status(checks),
            checks=checks,
        )

    def _overall_status(self, checks: list[SetupCheck]) -> str:
        statuses = {check.status for check in checks}
        if STATUS_ERROR in statuses:
            return STATUS_ERROR
        if STATUS_MISSING in statuses or STATUS_MANUAL in statuses:
            return STATUS_MANUAL
        return STATUS_OK

    def _binary_check(
        self,
        name: str,
        binary: str,
        command: list[str],
        missing_action: str,
    ) -> SetupCheck:
        if not self.which(binary):
            return SetupCheck(name, STATUS_MISSING, detail=f"{binary} nao encontrado no PATH.", action=missing_action)
        return self._command_check(name, command, missing_action)

    def _command_check(
        self,
        name: str,
        command: list[str],
        missing_action: str,
    ) -> SetupCheck:
        result = self._run(command, timeout=20)
        output = (result.stdout or result.stderr or "").strip()
        version = output.splitlines()[0] if output else "-"
        if result.return_code == 0:
            return SetupCheck(name, STATUS_OK, version, "Comando de verificacao executado com sucesso.")
        return SetupCheck(
            name,
            STATUS_ERROR,
            version,
            output or f"Comando retornou codigo {result.return_code}.",
            missing_action,
        )

    def _run(self, command: list[str], timeout: int = 20, cwd: Path | None = None) -> SetupCommandResult:
        try:
            completed = self.runner(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(cwd) if cwd else None,
                shell=False,
            )
        except FileNotFoundError as exc:
            return SetupCommandResult(command=command, return_code=127, stderr=str(exc))
        except subprocess.TimeoutExpired as exc:
            return SetupCommandResult(command=command, return_code=124, stderr=str(exc))
        return SetupCommandResult(
            command=list(command),
            return_code=int(getattr(completed, "returncode", 1)),
            stdout=str(getattr(completed, "stdout", "") or ""),
            stderr=str(getattr(completed, "stderr", "") or ""),
        )

    def _runtime_requirement_names(self) -> list[str]:
        return self._read_requirement_names(self.root_path / "requirements.txt")

    def _read_requirement_names(self, path: Path, seen: set[Path] | None = None) -> list[str]:
        seen = seen or set()
        resolved = path.resolve()
        if resolved in seen or not path.exists():
            return []
        seen.add(resolved)
        names: list[str] = []
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("-r "):
                nested = path.parent / line.split(maxsplit=1)[1]
                names.extend(self._read_requirement_names(nested, seen))
                continue
            if line.startswith("-"):
                continue
            package = line.split(";", 1)[0].strip()
            for separator in ("==", ">=", "<=", "~=", "!=", ">", "<"):
                package = package.split(separator, 1)[0].strip()
            package = package.split("[", 1)[0].strip()
            if package:
                names.append(package)
        return names

    def _render_text(self, report: SetupReport) -> str:
        lines = [
            "DataSpectre CLI - Setup Report",
            "======================================",
            "",
            f"Gerado em: {report.generated_at}",
            f"Versao: {report.version}",
            f"Root: {report.root_path}",
            f"Sistema: {report.operating_system}",
            f"Gerenciador de pacotes: {report.package_manager or 'nao detectado'}",
            f"Status final: {report.overall_status}",
            "",
            "Verificacoes",
            "------------",
        ]
        for check in report.checks:
            lines.extend(
                [
                    f"- {check.name}: {check.status}",
                    f"  Versao: {check.version}",
                    f"  Detalhe: {check.detail or '-'}",
                    f"  Acao: {check.action or '-'}",
                ]
            )
        lines.append("")
        return "\n".join(lines)
