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
        method_name = func.__name__
        
        task = args[0] if args else kwargs.get('task')
        
        if not task:
            return func(self, *args, **kwargs)
        
        hooks = self.task_hooks
        context = self.context
        
        for hook in hooks:
            if hasattr(hook, method_name):
                hook_method = getattr(hook, method_name)
                
                if not hook.should_execute(task):
                    continue
                    
                hook._current_context = context
                
                try:
                    hook_method(*args, **kwargs)
                except Exception as e:
                    if hasattr(hook, 'exception_handlers') and hook.exception_handlers:
                        for exc_class, handler_name in hook.exception_handlers.items():
                            if isinstance(e, exc_class):
                                if hasattr(hook, handler_name):
                                    handler = getattr(hook, handler_name)
                                    handler(e, task, args)
                                    break
                        else:
                            raise
                    else:
                        raise
        
        return func(self, *args, **kwargs)
    
    return wrapper
