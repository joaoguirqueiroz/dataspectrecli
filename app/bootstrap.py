"""Application bootstrap and dependency wiring."""

from __future__ import annotations

import sys
from pathlib import Path

from app.context import ApplicationContext
from core.constants import APP_NAME, APP_VERSION, MIN_PYTHON_VERSION, REQUIRED_DIRECTORIES, RUNTIME_DIRECTORIES
from core.events import EventBus
from core.exceptions import BootstrapError
from core.module_manager import ModuleManager
from core.plugin_manager import PluginManager
from core.resources import ResourceMonitor
from core.security import PermissionManager
from services.audit_service import AuditService
from services.baseline_service import BaselineService
from services.cleanup_service import CleanupService
from services.config_service import ConfigService
from services.history_service import HistoryService
from services.log_service import LogService
from services.project_service import ProjectService
from services.report_service import ReportService
from services.scanner_service import ScannerService
from services.session_service import SessionService
from services.setup_service import SetupService
from services.smart_scan_service import SmartScanService
from services.storage import ensure_dir


class Bootstrapper:
    """Prepares the runtime according to the official startup flow."""

    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path.resolve()

    def bootstrap(self) -> ApplicationContext:
        self._verify_python()
        self._ensure_repository_directories()

        context = ApplicationContext(root_path=self.root_path)
        event_bus = EventBus()
        context.event_bus = event_bus

        config_service = ConfigService(self.root_path)
        settings = config_service.load()
        config_service.ensure_directories()

        log_service = LogService(self.root_path)
        log_service.configure(settings)
        audit_service = AuditService(log_service)

        context.settings = settings
        context.config_service = config_service
        context.log_service = log_service
        context.audit_service = audit_service
        context.permission_manager = PermissionManager(
            settings.get("security", {}).get("active_profile", "administrator")
        )
        context.resource_monitor = ResourceMonitor(self.root_path)

        project_service = ProjectService(
            root_path=self.root_path,
            workdir=config_service.resolve_path("workdir"),
            audit=audit_service,
        )
        session_service = SessionService(self.root_path, project_service, audit_service)
        report_service = ReportService(
            root_path=self.root_path,
            reports_dir=config_service.resolve_path("reports"),
            audit=audit_service,
        )
        history_service = HistoryService(self.root_path / "data" / "history")
        cleanup_service = CleanupService(
            root_path=self.root_path,
            cache_dir=config_service.resolve_path("cache"),
            audit=audit_service,
        )
        scanner_service = ScannerService(root_path=self.root_path, settings=settings)
        smart_scan_service = SmartScanService(settings=settings)
        baseline_service = BaselineService(self.root_path)
        setup_service = SetupService(root_path=self.root_path)

        context.project_service = project_service
        context.session_service = session_service
        context.report_service = report_service
        context.history_service = history_service
        context.cleanup_service = cleanup_service
        context.scanner_service = scanner_service
        context.smart_scan_service = smart_scan_service
        context.baseline_service = baseline_service
        context.setup_service = setup_service

        module_manager = ModuleManager(context, event_bus)
        plugin_manager = PluginManager(context, event_bus)
        context.module_manager = module_manager
        context.plugin_manager = plugin_manager

        event_bus.subscribe("*", self._audit_event_bridge(context))
        module_manager.discover(self.root_path / "modules")
        module_manager.initialize_all()
        plugin_manager.discover(self.root_path / "plugins")
        plugin_manager.initialize_all()

        log_service.record_event(
            component="bootstrap",
            level="INFO",
            message=f"{APP_NAME} {APP_VERSION} initialized.",
            details={
                "modules": len(module_manager.registry),
                "plugins": len(plugin_manager.registry),
            },
        )
        history_service.append(
            "bootstrap",
            "initialized",
            {"modules": len(module_manager.registry), "plugins": len(plugin_manager.registry)},
        )
        event_bus.publish("application.initialized", "bootstrap", {"version": APP_VERSION})
        return context

    def _verify_python(self) -> None:
        if sys.version_info < MIN_PYTHON_VERSION:
            minimum = ".".join(str(part) for part in MIN_PYTHON_VERSION)
            raise BootstrapError(f"Python {minimum}+ is required.")

    def _ensure_repository_directories(self) -> None:
        for directory in REQUIRED_DIRECTORIES:
            ensure_dir(self.root_path / directory)
        for directory in RUNTIME_DIRECTORIES:
            ensure_dir(self.root_path / directory)

    def _audit_event_bridge(self, context: ApplicationContext):
        def handle(event) -> None:
            if context.log_service and event.name.startswith(
                ("module.", "plugin.", "application.")
            ):
                context.log_service.record_event(
                    component=event.component,
                    level="INFO",
                    message=event.name,
                    category="event",
                    details=event.payload,
                )

        return handle
