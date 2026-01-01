"""
Blueprint model for transient validation during workflow expansion.

This model is intentionally NOT a PydanticSerdesBaseModel subclass because:
1. Blueprints are temporary - used only during workflow loading/expansion
2. They don't need data store persistence or retrieval
3. They don't need hashability - they're validated and immediately discarded
4. Avoiding PydanticSerdes inheritance prevents circular import issues

Blueprint files are loaded, validated for structure, and their tasks are
extracted and expanded into the workflow. The BlueprintModel instance itself
is never stored or referenced after validation.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class BlueprintModel(BaseModel):
    """
    Model for blueprint files, ensuring valid structure for expansion.

    Blueprints define reusable task collections with optional descriptions.
    They are loaded and validated during workflow expansion.
    """

    model_config = ConfigDict(extra="forbid")

    description: str | None = None
    tasks: list[dict[str, Any]]
