import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from nornflow.constants import (
    FailureStrategy,
    NORNFLOW_DEFAULT_FILTERS_DIR,
    NORNFLOW_DEFAULT_HOOKS_DIR,
    NORNFLOW_DEFAULT_TASKS_DIR,
    NORNFLOW_DEFAULT_VARS_DIR,
    NORNFLOW_DEFAULT_WORKFLOWS_DIR,
)
from nornflow.exceptions import SettingsError


class NornFlowSettings(BaseSettings):
    """
    NornFlow settings management using Pydantic.

    Settings are loaded with the following priority (highest to lowest):
    1. Environment variables (prefixed with NORNFLOW_SETTINGS_)
    2. Values from settings YAML file
    3. Default values defined in the model

    Note the careful terminology:
    - "Settings" refers to NornFlow's own configuration
    - "Configuration/Config" is reserved for Nornir's configuration

    Environment variable examples:
    - NORNFLOW_SETTINGS_VARS_DIR=/custom/vars
    - NORNFLOW_SETTINGS_LOCAL_TASKS_DIRS=["tasks", "custom_tasks"]
    - NORNFLOW_SETTINGS_FAILURE_STRATEGY=fail-fast
    """

    model_config = SettingsConfigDict(
        env_prefix="NORNFLOW_SETTINGS_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="allow",
    )

    nornir_config_file: str = Field(description="Path to Nornir configuration file (required)")

    local_tasks_dirs: list[str] = Field(
        default=[NORNFLOW_DEFAULT_TASKS_DIR], description="List of directories containing Nornir tasks"
    )
    local_workflows_dirs: list[str] = Field(
        default=[NORNFLOW_DEFAULT_WORKFLOWS_DIR],
        description="List of directories containing workflow definitions",
    )
    local_filters_dirs: list[str] = Field(
        default=[NORNFLOW_DEFAULT_FILTERS_DIR],
        description="List of directories containing custom filter functions",
    )
    local_hooks_dirs: list[str] = Field(
        default=[NORNFLOW_DEFAULT_HOOKS_DIR], description="List of directories containing custom hook classes"
    )
    imported_packages: list[str] = Field(
        default_factory=list, description="List of Python packages to import for additional resources"
    )
    processors: list[dict[str, Any]] = Field(
        default_factory=list, description="List of processor configurations with class and args"
    )
    vars_dir: str = Field(
        default=NORNFLOW_DEFAULT_VARS_DIR, description="Directory containing variable files"
    )
    failure_strategy: FailureStrategy = Field(
        default=FailureStrategy.SKIP_FAILED, description="Strategy for handling task failures"
    )
    dry_run: bool = Field(default=False, description="Whether to run in dry-run mode")

    _base_dir: Path | None = None
    _settings_file: str | None = None

    @field_validator("processors", mode="before")
    @classmethod
    def validate_processors(cls, v: Any) -> list[dict[str, Any]]:
        """Validate and normalize processor configurations."""
        if not v:
            return []

        if not isinstance(v, list):
            raise TypeError("processors must be a list")

        validated = []
        for item in v:
            if isinstance(item, str):
                validated.append({"class": item, "args": {}})
            elif isinstance(item, dict):
                if "class" not in item:
                    raise ValueError("Each processor dict must have a 'class' key")
                validated.append({"class": item["class"], "args": item.get("args", {})})
            else:
                raise TypeError(f"Invalid processor type: {type(item).__name__}")

        return validated

    @field_validator("failure_strategy", mode="before")
    @classmethod
    def validate_failure_strategy(cls, v: Any) -> FailureStrategy:
        """Convert string to FailureStrategy enum."""
        if isinstance(v, str):
            try:
                return FailureStrategy(v)
            except ValueError:
                normalized = v.lower().replace("_", "-")
                try:
                    return FailureStrategy(normalized)
                except ValueError as e:
                    raise ValueError(
                        f"Invalid failure strategy: {v}. "
                        f"Must be one of: {', '.join(s.value for s in FailureStrategy)}"
                    ) from e
        return v

    @model_validator(mode="after")
    def resolve_relative_paths(self) -> "NornFlowSettings":
        """Resolve relative paths to absolute paths based on base directory."""
        if not self._base_dir:
            return self

        for field_name in [
            "local_tasks_dirs",
            "local_workflows_dirs",
            "local_filters_dirs",
            "local_hooks_dirs",
        ]:
            dirs = getattr(self, field_name)
            if dirs:
                resolved = []
                for dir_path in dirs:
                    path = Path(dir_path)
                    if not path.is_absolute():
                        resolved.append(str(self._base_dir / path))
                    else:
                        resolved.append(str(path))
                setattr(self, field_name, resolved)

        vars_path = Path(self.vars_dir)
        if not vars_path.is_absolute():
            self.vars_dir = str(self._base_dir / vars_path)

        if self.nornir_config_file:
            config_path = Path(self.nornir_config_file)
            if not config_path.is_absolute():
                self.nornir_config_file = str(self._base_dir / config_path)

        return self

    @classmethod
    def load(
        cls, 
        settings_file: str | None = None, 
        base_dir: Path | None = None, 
        **overrides: Any
    ) -> "NornFlowSettings":
        """
        Load settings from a YAML file with automatic resolution and overrides.

        This is the recommended way to create NornFlowSettings instances. It handles:
        - Settings file discovery (explicit path, env var, or default)
        - YAML loading and validation
        - Path resolution relative to settings file location
        - Programmatic value overrides

        Settings file resolution priority (highest to lowest):
        1. Explicit settings_file parameter (caller's direct intent)
        2. NORNFLOW_SETTINGS environment variable (session default)
        3. Default "nornflow.yaml" in current directory

        Args:
            settings_file: Path to settings YAML file. If None, checks NORNFLOW_SETTINGS 
                          env var, then defaults to "nornflow.yaml" in current directory.
            base_dir: Base directory for resolving relative paths. If None, uses the 
                     directory containing the resolved settings file.
            **overrides: Additional settings to override YAML values. Useful for 
                        programmatic configuration. Example: dry_run=True

        Returns:
            NornFlowSettings instance with all paths resolved.

        Raises:
            SettingsError: If settings file not found or contains invalid data.

        Examples:
            # Use default resolution (checks env var, then nornflow.yaml)
            settings = NornFlowSettings.load()

            # Explicit file path (highest priority)
            settings = NornFlowSettings.load("configs/prod-settings.yaml")

            # Override specific values programmatically
            settings = NornFlowSettings.load(dry_run=True, failure_strategy="fail-fast")

            # Combine file + overrides
            settings = NornFlowSettings.load(
                "configs/base.yaml",
                processors=[{"class": "custom.Processor"}]
            )
        """
        resolved_file = (
            settings_file or 
            os.getenv("NORNFLOW_SETTINGS") or 
            "nornflow.yaml"
        )

        settings_path = Path(resolved_file).resolve()

        if not settings_path.exists():
            raise SettingsError(f"Settings file not found: {resolved_file}")

        if not base_dir:
            base_dir = settings_path.parent

        try:
            with settings_path.open() as f:
                yaml_data = yaml.safe_load(f) or {}
        except Exception as e:
            raise SettingsError(f"Failed to load settings from {resolved_file}: {e}") from e

        if not isinstance(yaml_data, dict):
            raise SettingsError(
                f"Settings file must contain a YAML dictionary, got {type(yaml_data).__name__}"
            )

        settings_data = {**yaml_data, **overrides}

        instance = cls(**settings_data)
        instance._base_dir = base_dir
        instance._settings_file = str(settings_path)

        return instance.resolve_relative_paths()

    @property
    def as_dict(self) -> dict[str, Any]:
        """Get settings as a dictionary."""
        return self.model_dump(exclude={"_base_dir", "_settings_file"})

    @property
    def base_dir(self) -> Path:
        """Get the base directory for resolving relative paths."""
        if not self._base_dir:
            if self._settings_file:
                self._base_dir = Path(self._settings_file).parent
            else:
                self._base_dir = Path.cwd()
        return self._base_dir

    @property
    def loaded_settings(self) -> dict[str, Any]:
        """Backward compatibility property for accessing settings as dict."""
        return self.as_dict

    def __getattr__(self, name: str) -> Any:
        """
        Provide backward compatibility for accessing undefined settings.
        Returns None for non-existent attributes instead of raising AttributeError.
        """
        if hasattr(self, "__pydantic_extra__"):
            return self.__pydantic_extra__.get(name, None)
        return None

    def __str__(self) -> str:
        """Return a string representation of the NornFlowSettings instance."""
        return str(self.as_dict)
