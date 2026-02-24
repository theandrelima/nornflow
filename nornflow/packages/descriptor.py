from pydantic import BaseModel, ConfigDict, field_validator

from nornflow.packages.constants import VALID_RESOURCE_TYPES


class PackageDescriptor(BaseModel):
    """Validates and represents a single entry in the `packages` setting.

    Attributes:
        name: Python import path for the NornFlow-compatible package.
        include: Resource types to import. None means all types are imported.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    include: list[str] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Package name cannot be empty")
        return v.strip()

    @field_validator("include")
    @classmethod
    def validate_include(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None

        if not v:
            raise ValueError("If 'include' is specified, it must be a non-empty list")

        invalid = [r for r in v if r not in VALID_RESOURCE_TYPES]
        if invalid:
            raise ValueError(
                f"Invalid resource type(s): {sorted(invalid)}. "
                f"Valid types: {sorted(VALID_RESOURCE_TYPES)}"
            )

        return v

    def should_import(self, resource_type: str) -> bool:
        """Whether this descriptor requests importing the given resource type.

        Args:
            resource_type: A resource type string (e.g. "tasks", "hooks").

        Returns:
            True if include is None (import all) or resource_type is listed.
        """
        if not self.include:
            return True
        return resource_type in self.include

    def explicitly_includes(self, resource_type: str) -> bool:
        """Whether include explicitly names the resource type (not just "import all").

        Args:
            resource_type: A resource type string (e.g. "tasks", "hooks").

        Returns:
            True only if include is a non-None list that contains resource_type.
        """
        if not self.include:
            return False
        return resource_type in self.include
