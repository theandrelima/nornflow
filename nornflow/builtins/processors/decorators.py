from functools import wraps
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from nornflow.hooks import Hook


def hook_delegator(func: Callable) -> Callable:
    """Decorator that automatically delegates to hooks based on the method name.
    
    This decorator extracts the method name from the decorated function
    and delegates to the corresponding hook methods.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Get the method name from the function being decorated
        method_name = func.__name__
        
        # Extract task from arguments
        task = args[0] if args else kwargs.get('task')
        
        if not task:
            return func(self, *args, **kwargs)
        
        hooks = self._get_hooks_for_task(task)
        
        for hook in hooks:
            if hasattr(hook, method_name):
                hook_method = getattr(hook, method_name)
                
                # Check if the hook should execute for this task (enforces run_once_per_task)
                if not hook.should_execute(task):
                    continue
                    
                try:
                    hook_method(*args, **kwargs)
                except Exception as e:
                    # Check for hook-specific exception handlers
                    if hasattr(hook, 'exception_handlers') and hook.exception_handlers:
                        for exc_class, handler_name in hook.exception_handlers.items():
                            if isinstance(e, exc_class):
                                # Call the handler method on the hook instance
                                if hasattr(hook, handler_name):
                                    handler = getattr(hook, handler_name)
                                    handler(e, task, args)
                                    # Handled, do not re-raise
                                    break
                        else:
                            # Exception not handled by hook, re-raise
                            raise
                    else:
                        # No exception handlers defined, re-raise
                        raise
        
        # Call the original method
        return func(self, *args, **kwargs)
    
    return wrapper