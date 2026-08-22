"""Report generation and report catalog service."""

from __future__ import annotations

import json
import csv
import html
from io import StringIO
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.constants import APP_NAME, APP_VERSION
from core.exceptions import ReportError
from services.audit_service import AuditService
from services.storage import ensure_dir, read_json, write_json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ReportRecord:
    id: str
    title: str
    format: str
    path: str
    project_id: str | None = None
    session_id: str | None = None
    generated_at: str = field(default_factory=utc_now)
    template: str = "technical"
    version: str = APP_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReportService:
    """Turns module and project results into structured documents."""

    SUPPORTED_FORMATS = {"markdown", "txt", "json", "csv", "html"}
    EXTENSIONS = {
        "markdown": "md",
        "txt": "txt",
        "json": "json",
        "csv": "csv",
        "html": "html",
    }
    SIMPLE_TOOL_DIRS = {"nmap", "nuclei", "smart_scan", "smart-scan"}

    def __init__(
        self,
        root_path: Path,
        reports_dir: Path,
        audit: AuditService | None = None,
    ) -> None:
        self.root_path = root_path
        self.reports_dir = reports_dir
        self.audit = audit
        self.index_path = reports_dir / "reports_index.json"
        ensure_dir(reports_dir)

    def generate_report(
        self,
        title: str,
        results: dict[str, Any],
        project_id: str | None = None,
        session_id: str | None = None,
        report_format: str = "markdown",
        template: str = "technical",
        tool: str | None = None,
    ) -> ReportRecord:
        if report_format not in self.SUPPORTED_FORMATS:
            raise ReportError(f"Unsupported report format '{report_format}'.")
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        report_id = f"report-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
        report_dir = self._target_dir(project_id, session_id, tool)
        extension = self.EXTENSIONS[report_format]
        if tool in self.SIMPLE_TOOL_DIRS:
            report_name = f"{self._normalize_tool(tool)}_{stamp}.{extension}"
        else:
            report_name = f"{report_id}.{extension}"
        report_path = report_dir / report_name
        payload = self._payload(report_id, title, results, project_id, session_id, template, tool)
        if report_format == "markdown":
            report_path.write_text(self._render_markdown(payload), encoding="utf-8")
        elif report_format == "txt":
            report_path.write_text(self._render_text(payload), encoding="utf-8")
        elif report_format == "json":
            report_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        elif report_format == "csv":
            report_path.write_text(self._render_csv(payload), encoding="utf-8")
        elif report_format == "html":
            report_path.write_text(self._render_html(payload), encoding="utf-8")
        record = ReportRecord(
            id=report_id,
            title=title,
            format=report_format,
            path=str(report_path.relative_to(self.root_path)),
            project_id=project_id,
            session_id=session_id,
            template=template,
        )
        self._register(record)
        self._audit(
            "report.generated",
            report_id,
            {
                "project_id": project_id,
                "session_id": session_id,
                "format": report_format,
                "tool": tool,
            },
        )
        return record

    def list_reports(self) -> list[ReportRecord]:
        index = read_json(self.index_path, default=[]) or []
        return [ReportRecord(**payload) for payload in index]

    def tool_output_dir(
        self, project_id: str | None, session_id: str | None, tool: str
    ) -> Path:
        return self._target_dir(project_id, session_id, tool)

    def _target_dir(self, project_id: str | None, session_id: str | None, tool: str | None = None) -> Path:
        if tool in self.SIMPLE_TOOL_DIRS:
            return ensure_dir(self.reports_dir / self._normalize_tool(tool))
        date_path = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        session_path = session_id or "sessionless"
        root = self.reports_dir / (project_id or "global") / date_path / session_path
        if tool:
            root = root / tool
        return ensure_dir(root)

    def _normalize_tool(self, tool: str) -> str:
        return tool.replace("-", "_")

    def _payload(
        self,
        report_id: str,
        title: str,
        results: dict[str, Any],
        project_id: str | None,
        session_id: str | None,
        template: str,
        tool: str | None,
    ) -> dict[str, Any]:
        return {
            "metadata": {
                "id": report_id,
                "title": title,
                "application": APP_NAME,
                "version": APP_VERSION,
                "template": template,
                "generated_at": utc_now(),
                "project_id": project_id,
                "session_id": session_id,
                "tool": tool,
                "ethical_notice": "Use only on owned, authorized, or lab environments.",
                "developed_by": "DataSpectre",
            },
            "executive_summary": {
                "status": results.get("status", "completed"),
                "success": results.get("success", True),
                "items": len(results.get("data", {})) if isinstance(results.get("data"), dict) else 0,
            },
            "results": results,
        }

    def _render_markdown(self, payload: dict[str, Any]) -> str:
        metadata = payload["metadata"]
        summary = payload["executive_summary"]
        result_json = json.dumps(payload["results"], ensure_ascii=False, indent=2, sort_keys=True)
        return (
            f"# {metadata['title']}\n\n"
            f"## Metadados\n\n"
            f"- Aplicacao: {metadata['application']}\n"
            f"- Versao: {metadata['version']}\n"
            f"- Identificador: {metadata['id']}\n"
            f"- Projeto: {metadata.get('project_id') or 'global'}\n"
            f"- Sessao: {metadata.get('session_id') or 'nao vinculada'}\n"
            f"- Ferramenta: {metadata.get('tool') or 'geral'}\n"
            f"- Desenvolvido por: {metadata.get('developed_by')}\n"
            f"- Gerado em: {metadata['generated_at']}\n\n"
            f"## Aviso de Uso Autorizado\n\n"
            f"{metadata.get('ethical_notice')}\n\n"
            f"## Resumo Executivo\n\n"
            f"- Status: {summary['status']}\n"
            f"- Sucesso: {summary['success']}\n"
            f"- Itens principais: {summary['items']}\n\n"
            f"## Resultados\n\n"
            f"```json\n{result_json}\n```\n"
        )

    def _render_text(self, payload: dict[str, Any]) -> str:
        metadata = payload["metadata"]
        summary = payload["executive_summary"]
        result_json = json.dumps(payload["results"], ensure_ascii=False, indent=2, sort_keys=True)
        return (
            f"{metadata['title']}\n"
            f"{'=' * len(metadata['title'])}\n\n"
            "METADADOS\n"
            f"Aplicacao: {metadata['application']}\n"
            f"Versao: {metadata['version']}\n"
            f"Identificador: {metadata['id']}\n"
            f"Projeto: {metadata.get('project_id') or 'global'}\n"
            f"Sessao: {metadata.get('session_id') or 'nao vinculada'}\n"
            f"Ferramenta: {metadata.get('tool') or 'geral'}\n"
            f"Desenvolvido por: {metadata.get('developed_by')}\n"
            f"Gerado em: {metadata['generated_at']}\n\n"
            "AVISO DE USO AUTORIZADO\n"
            f"{metadata.get('ethical_notice')}\n\n"
            "RESUMO EXECUTIVO\n"
            f"Status: {summary['status']}\n"
            f"Sucesso: {summary['success']}\n"
            f"Itens principais: {summary['items']}\n\n"
            "RESULTADOS\n"
            f"{result_json}\n"
        )

    def _render_csv(self, payload: dict[str, Any]) -> str:
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["section", "key", "value"])
        for key, value in payload["metadata"].items():
            writer.writerow(["metadata", key, value])
        for key, value in payload["executive_summary"].items():
            writer.writerow(["executive_summary", key, value])
        writer.writerow(
            [
                "results",
                "payload",
                json.dumps(payload["results"], ensure_ascii=False, sort_keys=True),
            ]
        )
        return buffer.getvalue()

    def _render_html(self, payload: dict[str, Any]) -> str:
        metadata = payload["metadata"]
        summary = payload["executive_summary"]
        result_json = html.escape(
            json.dumps(payload["results"], ensure_ascii=False, indent=2, sort_keys=True)
        )
        metadata_rows = "\n".join(
            f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
            for key, value in metadata.items()
        )
        summary_rows = "\n".join(
            f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
            for key, value in summary.items()
        )
        return (
            "<!doctype html>\n"
            "<html lang=\"pt-BR\">\n"
            "<head>\n"
            "  <meta charset=\"utf-8\">\n"
            f"  <title>{html.escape(metadata['title'])}</title>\n"
            "  <style>"
            "body{font-family:Arial,sans-serif;margin:32px;color:#1f2933;}"
            "h1,h2{color:#102a43;}table{border-collapse:collapse;width:100%;margin-bottom:24px;}"
            "th,td{border:1px solid #bcccdc;padding:8px;text-align:left;}th{background:#f0f4f8;}"
            "pre{background:#f0f4f8;border:1px solid #bcccdc;padding:16px;overflow:auto;}"
            "  </style>\n"
            "</head>\n"
            "<body>\n"
            f"  <h1>{html.escape(metadata['title'])}</h1>\n"
            "  <h2>Metadados</h2>\n"
            f"  <table>{metadata_rows}</table>\n"
            "  <h2>Resumo Executivo</h2>\n"
            f"  <table>{summary_rows}</table>\n"
            "  <h2>Resultados</h2>\n"
            f"  <pre>{result_json}</pre>\n"
            "</body>\n"
            "</html>\n"
        )

    def _register(self, record: ReportRecord) -> None:
        index = read_json(self.index_path, default=[]) or []
        index.append(record.to_dict())
        write_json(self.index_path, index)

    def _audit(
        self, action: str, target: str, details: dict[str, Any] | None = None
    ) -> None:
        if self.audit:
            self.audit.record(action=action, target=target, details=details)
