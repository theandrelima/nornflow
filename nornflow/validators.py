from nornflow.exceptions import TaskValidationError


def run_post_creation_validation(task: "TaskModel") -> None:
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
        TaskValidationError: If any field validation fails
    """
    import sys
    
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
                if not isinstance(result, tuple) or len(result) != 2:
                    raise TaskValidationError(
                        task_name=task.name,
                        field_name=field_name,
                        reason=f"Validator '{validator_name}' must return a tuple (bool, str), got {type(result).__name__}"
                    )
                
                is_valid, error_message = result
                
                # If validator returns False, raise exception with provided message
                if is_valid is False:
                    raise TaskValidationError(
                        task_name=task.name,
                        field_name=field_name,
                        reason=error_message if error_message else None
                    )
                    
            except Exception as e:
                # If validator raises an exception, wrap it in TaskValidationError
                if isinstance(e, TaskValidationError):
                    raise
                else:
                    raise TaskValidationError(
                        task_name=task.name,
                        field_name=field_name,
                        reason=f"Validator error: {str(e)}"
                    ) from e


def set_to_validator(task: "TaskModel") -> tuple[bool, str]:
    """
    Validate that the TaskModel instance does not have a set_to set 
    for tasks that shouldn't have it.
    
    Args:
        task: The TaskModel instance to validate
        
    Returns:
        tuple[bool, str]: (is_valid, error_message)
            - If valid: (True, "")
            - If invalid: (False, "detailed error message")
    """
    invalid_tasks = {
        "set",
        "echo",
        "set_to",  # including for sanity. Shame on you if you create a set_to task with a set_to flag in it.
    }
    
    # Only validate if set_to is actually set
    if task.set_to is not None and task.name in invalid_tasks:
        return (
            False, 
            f"The 'set_to' keyword is not supported for NornFlow's built-in task '{task.name}'. "
            f"Use 'set_to' only with Nornir tasks that produce meaningful result objects."
        )
    
    return (True, "")
