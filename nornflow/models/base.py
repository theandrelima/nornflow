from typing import Any, ClassVar

from pydantic_serdes.models import PydanticSerdesBaseModel

from nornflow.models.validators import run_universal_field_validation


class NornFlowBaseModel(PydanticSerdesBaseModel):
    """
    Base model for all NornFlow models with strict field validation and universal field validation.
    """

    model_config: ClassVar[dict[str, str]] = {"extra": "forbid"}
    _exclude_from_universal_validations: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def create(cls, model_dict: dict[str, Any], *args: Any, **kwargs: Any) -> "NornFlowBaseModel":
        """
        Create model instance with universal field validation.
        """
        new_instance = super().create(model_dict, *args, **kwargs)
        run_universal_field_validation(new_instance)
        return new_instance
