"""Reference plugin used for validation and documentation."""

from __future__ import annotations

from core.plugin import BasePlugin, PluginContext, PluginMetadata


class ExamplePlugin(BasePlugin):
    metadata = PluginMetadata(
        id="example_plugin",
        name="Example Plugin",
        version="1.0.0",
        author="DataSpectre",
        description="Reference plugin demonstrating the extension lifecycle.",
        category="reference",
        components=["lifecycle-demo"],
    )

    def initialize(self, context: PluginContext) -> None:
        if context.application.history_service:
            context.application.history_service.append(
                "plugin",
                "example_plugin.initialized",
                {"plugin_id": self.metadata.id},
            )

    def shutdown(self) -> None:
        return None


PLUGIN_CLASS = ExamplePlugin

