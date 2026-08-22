"""Asset inventory module implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.exceptions import ValidationError
from core.module import BaseModule, ModuleExecutionContext, ModuleMetadata, ModuleResult


class AssetInventoryModule(BaseModule):
    metadata = ModuleMetadata(
        id="asset_inventory",
        name="Asset Inventory",
        version="1.0.0",
        author="DataSpectre",
        description="Normalizes authorized asset inventory input.",
        category="inventory",
    )

    def validate(self, parameters: dict[str, Any]) -> None:
        if "assets" not in parameters and "input_file" not in parameters:
            raise ValidationError("Provide 'assets' or 'input_file'.")

    def execute(self, context: ModuleExecutionContext) -> ModuleResult:
        assets = self._load_assets(context.parameters, context.application.root_path)
        normalized = [self._normalize_asset(asset, index) for index, asset in enumerate(assets, start=1)]
        grouped: dict[str, int] = {}
        for asset in normalized:
            grouped[asset["type"]] = grouped.get(asset["type"], 0) + 1
        return self.result(
            success=True,
            status="completed",
            data={
                "total_assets": len(normalized),
                "assets": normalized,
                "by_type": grouped,
                "source": context.parameters.get("source", "manual"),
            },
            messages=["Asset inventory normalized successfully."],
        )

    def _load_assets(self, parameters: dict[str, Any], root_path: Path) -> list[Any]:
        if parameters.get("input_file"):
            path = Path(str(parameters["input_file"]))
            if not path.is_absolute():
                path = root_path / path
            if not path.exists():
                raise ValidationError(f"Input file '{path}' was not found.")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                if "assets" not in payload:
                    raise ValidationError("Input file object must include an 'assets' list.")
                payload = payload["assets"]
            if not isinstance(payload, list):
                raise ValidationError("Input file must contain a list or {'assets': [...]} object.")
            return payload
        assets = parameters.get("assets")
        if isinstance(assets, str):
            return [item.strip() for item in assets.split(",") if item.strip()]
        if isinstance(assets, list):
            return assets
        raise ValidationError("'assets' must be a list or comma-separated string.")

    def _normalize_asset(self, asset: Any, index: int) -> dict[str, Any]:
        if isinstance(asset, str):
            value = asset.strip()
            if not value:
                raise ValidationError("Asset values cannot be empty.")
            return {
                "id": f"asset-{index:03d}",
                "name": value,
                "address": value,
                "type": "host",
                "tags": [],
            }
        if not isinstance(asset, dict):
            raise ValidationError("Each asset must be a string or object.")
        name = str(asset.get("name") or asset.get("host") or asset.get("address") or "").strip()
        if not name:
            raise ValidationError("Asset object must include name, host, or address.")
        tags = asset.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        if not isinstance(tags, list):
            raise ValidationError("Asset tags must be a list or string.")
        return {
            "id": str(asset.get("id") or f"asset-{index:03d}"),
            "name": name,
            "address": str(asset.get("address") or asset.get("host") or name),
            "type": str(asset.get("type") or "host"),
            "tags": tags,
            "owner": asset.get("owner"),
        }


MODULE_CLASS = AssetInventoryModule
