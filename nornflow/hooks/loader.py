from typing import Any, TYPE_CHECKING

from nornflow.exceptions import AssetAmbiguityError, AssetNotFoundError
from nornflow.hooks.base import HOOKS_CATALOG
from nornflow.logger import logger

if TYPE_CHECKING:
    from nornflow.hooks import Hook


def load_hooks(hooks_dict: dict[str, Any]) -> list["Hook"]:
    """Load hooks from a hooks dictionary.

    Processes the hooks configuration dict and returns instantiated Hook instances.

    Args:
        hooks_dict: Dictionary mapping hook names to hook configurations

    Returns:
        List of instantiated Hook instances
    """
    hooks = []
    if not hooks_dict:
        return hooks

    for hook_name, hook_config in hooks_dict.items():
        hook_class = _resolve_hook_class(hook_name)
        if hook_class:
            try:
                hook_instance = hook_class(hook_config)
                hooks.append(hook_instance)
            except Exception as e:
                logger.exception(f"Failed to instantiate hook '{hook_name}': {e}")
                raise

    logger.debug(f"Loaded {len(hooks)} hooks from configuration.")
    return hooks


def _resolve_hook_class(hook_name: str) -> type["Hook"] | None:
    """Resolve a hook class from the hooks catalog by bare or qualified name."""
    if hasattr(HOOKS_CATALOG, "resolve"):
        try:
            return HOOKS_CATALOG.resolve(hook_name)
        except AssetNotFoundError:
            return None
        except AssetAmbiguityError as exc:
            logger.error(
                f"Hook '{hook_name}' is ambiguous. Use a qualified name. "
                f"Candidates: {', '.join(sorted(exc.candidates))}"
            )
            raise

    return HOOKS_CATALOG.get(hook_name)
