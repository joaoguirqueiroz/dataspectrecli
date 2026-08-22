"""System health module implementation."""

from __future__ import annotations

from core.module import BaseModule, ModuleExecutionContext, ModuleMetadata, ModuleResult


class SystemHealthModule(BaseModule):
    metadata = ModuleMetadata(
        id="system_health",
        name="System Health",
        version="1.0.0",
        author="DataSpectre",
        description="Reports application runtime health indicators.",
        category="monitoring",
    )

    def execute(self, context: ModuleExecutionContext) -> ModuleResult:
        app = context.application
        snapshot = app.resource_monitor.snapshot(
            {
                "modules": len(app.module_manager.registry),
                "plugins": len(app.plugin_manager.registry),
                "projects": len(app.project_service.list_projects()),
                "log_configured": bool(app.log_service.configured),
            }
        )
        return self.result(
            success=True,
            status="completed",
            data=snapshot,
            messages=["Runtime health collected successfully."],
        )


MODULE_CLASS = SystemHealthModule

