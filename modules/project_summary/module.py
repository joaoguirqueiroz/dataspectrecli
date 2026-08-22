"""Project summary module implementation."""

from __future__ import annotations

from typing import Any

from core.exceptions import ValidationError
from core.module import BaseModule, ModuleExecutionContext, ModuleMetadata, ModuleResult


class ProjectSummaryModule(BaseModule):
    metadata = ModuleMetadata(
        id="project_summary",
        name="Project Summary",
        version="1.0.0",
        author="DataSpectre",
        description="Summarizes projects, sessions, and report counts.",
        category="projects",
    )

    def validate(self, parameters: dict[str, Any]) -> None:
        if parameters.get("project_id") is not None and not str(parameters["project_id"]).strip():
            raise ValidationError("'project_id' cannot be empty.")

    def execute(self, context: ModuleExecutionContext) -> ModuleResult:
        project_id = context.parameters.get("project_id") or context.project_id
        service = context.application.project_service
        if project_id:
            data = service.stats(str(project_id))
        else:
            projects = service.list_projects(include_archived=True)
            data = {
                "total_projects": len(projects),
                "active_projects": len([project for project in projects if project.status == "active"]),
                "archived_projects": len([project for project in projects if project.status == "archived"]),
            }
        return self.result(
            success=True,
            status="completed",
            data=data,
            messages=["Project summary generated successfully."],
        )


MODULE_CLASS = ProjectSummaryModule

