import sys
from typing import Any

from nornflow.exceptions import TaskError
from nornflow.utils import check_for_jinja2_recursive


def run_post_creation_task_validation(task: "TaskModel") -> None:
    """
    Run post-creation validation by calling field-specific validators.

    For each field defined in the TaskModel, attempts to find and call a corresponding
    validator function named '{field_name}_validator' in this module.

    Validator functions must return a tuple: (bool, str)
    - If first element is True, validation passes (second element ignored)
    - If first element is False, validation fails and second element is used as error message

    Args:
        task: The TaskModel instance to validate

    Raises:
        TaskError: If any field validation fails
    """
    # Get only the fields defined in TaskModel class, not inherited ones
    task_model_fields = set(task.model_fields.keys())

    # Get reference to this validators module
    current_module = sys.modules[__name__]

    for field_name in task_model_fields:
        validator_name = f"{field_name}_validator"

        # Check if validator function exists in this module
        if hasattr(current_module, validator_name):
            validator_func = getattr(current_module, validator_name)

            try:
                # Call the validator with the complete TaskModel object
                result = validator_func(task)

                # Validator must return a tuple (bool, str)
                if not isinstance(result, tuple) or len(result) != 2:  # noqa: PLR2004
                    raise TaskError(
                        f"Task '{task.name}' validation failed for field '{field_name}': "
                        f"Validator '{validator_name}' must return a tuple (bool, str), "
                        f"got {type(result).__name__}"
                    )

                is_valid, error_message = result

                # If validator returns False, raise exception with provided message
                if is_valid is False:
                    error_msg = f"Task '{task.name}' validation failed for field '{field_name}'"
                    if error_message:
                        error_msg += f": {error_message}"
                    raise TaskError(error_msg)

            except Exception as e:
                # If validator raises an exception, wrap it in TaskError
                if isinstance(e, TaskError):
                    raise
                raise TaskError(
                    f"Task '{task.name}' validation failed for field '{field_name}': "
                    f"Validator error: {e!s}"
                ) from e


def run_universal_field_validation(instance: "NornFlowBaseModel") -> None:
    """
    Run universal field validators that apply to all fields unless excluded.

    Uses dynamic discovery to find and call functions with naming pattern
    'universal_{whatever}_validator' in this module. These validators run on all
    fields except those listed in the model's _exclude_from_universal_validations.

    Universal validator functions must return a tuple: (bool, str)
    - If first element is True, validation passes (second element ignored)
    - If first element is False, validation fails and second element is used as error message

    Args:
        instance: The model instance to validate

    Raises:
        TaskError: If any universal validation fails
    """
    # Get all field names for this model
    all_fields = set(instance.model_fields.keys())

    # Get excluded fields for this specific model class
    excluded_fields = set(getattr(instance.__class__, "_exclude_from_universal_validations", set()))

    # Fields to validate = all fields - excluded fields
    fields_to_validate = all_fields - excluded_fields

    # Get reference to this validators module
    current_module = sys.modules[__name__]

    # Find all universal validators in this module using naming convention
    universal_validators = [
        name for name in dir(current_module) if name.startswith("universal_") and name.endswith("_validator")
    ]

    # Run each universal validator on each field
    for validator_name in universal_validators:
        validator_func = getattr(current_module, validator_name)

        for field_name in fields_to_validate:
            field_value = getattr(instance, field_name, None)

            try:
                result = validator_func(instance, field_name, field_value)

                # Validator must return a tuple (bool, str)
                if not isinstance(result, tuple) or len(result) != 2:  # noqa: PLR2004
                    task_name = getattr(instance, "name", "unknown")
                    raise TaskError(
                        f"Validation failed for '{task_name}' field '{field_name}': "
                        f"Universal validator '{validator_name}' must return a tuple (bool, str), "
                        f"got {type(result).__name__}"
                    )

                is_valid, error_message = result

                if is_valid is False:
                    task_name = getattr(instance, "name", "unknown")
                    error_msg = f"Validation failed for '{task_name}' field '{field_name}'"
                    if error_message:
                        error_msg += f": {error_message}"
                    raise TaskError(error_msg)

            except Exception as e:
                if isinstance(e, TaskError):
                    raise
                task_name = getattr(instance, "name", "unknown")
                raise TaskError(
                    f"Validation failed for '{task_name}' field '{field_name}': "
                    f"Universal validator '{validator_name}' error: {e!s}"
                ) from e


# Universal validators (new pattern) - naming convention: universal_{name}_validator
def universal_jinja2_validator(
    instance: "NornFlowBaseModel", field_name: str, field_value: Any
) -> tuple[bool, str]:
    """
    Universal validator to prevent Jinja2 code in fields.

    This validator is automatically discovered and applied to all fields
    unless excluded via _exclude_from_universal_validations.

    Args:
        instance: The model instance being validated
        field_name: Name of the field being validated
        field_value: Value of the field being validated

    Returns:
        tuple[bool, str]: (is_valid, error_message)
    """
    try:
        check_for_jinja2_recursive(field_value, f"{instance.__class__.__name__}.{field_name}")
        return (True, "")
    except ValueError as e:
        return (False, str(e))
