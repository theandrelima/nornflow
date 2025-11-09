import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from nornflow.exceptions import CatalogError, CoreError, ResourceError
from nornflow.utils import import_module_from_path


class Catalog(ABC, dict[str, Any]):
    """Base catalog that provides core functionality for tracking items and their sources.

    This catalog extends dict while adding:
    - Source tracking for each item
    - Basic registration and query methods
    """

    def __init__(self, name: str):
        """Initialize an empty catalog with a name for error messages.

        Args:
            name: The name of this catalog.
        """
        super().__init__()
        self.name = name
        self.sources: dict[str, dict[str, Any]] = {}

    def __setitem__(self, key: str, value: Any, **kwargs) -> None:
        """Sets an item in the catalog and tracks metadata.

        Args:
            key: The key for the item.
            value: The value to store.
            **kwargs: Arbitrary metadata to associate with the item.
        """
        super().__setitem__(key, value)
        self.sources[key] = {"registered_at": datetime.now(), **kwargs}

    def register(self, name: str, item: Any, **kwargs) -> Any:
        """Registers an item in the catalog and stores its metadata.

        Args:
            name: The key for the item.
            item: The value to store.
            **kwargs: Arbitrary metadata to associate with the item.

        Returns:
            The registered value.
        """
        self.__setitem__(name, item, **kwargs)
        return item

    @property
    def is_empty(self) -> bool:
        """Check if the catalog is empty."""
        return len(self) == 0

    def get_item_info(self, name: str, include_name: bool = True) -> dict[str, Any] | None:
        """Get detailed information about an item.

        Args:
            name: The name of the item to look up.
            include_name: Whether to include the name in the returned info.

        Returns:
            A dictionary with item metadata or None if not found.
        """
        if name not in self:
            return None

        info = {
            "type": type(self[name]).__name__,
            "value": self[name],
        }

        if include_name:
            info["name"] = name

        info.update(self.sources.get(name, {}))
        return info

    def get_all_items_info(self, include_name: bool = False) -> dict[str, dict[str, Any]]:
        """Get information about all items in the catalog.

        Args:
            include_name: Whether to include the name in each info dict.

        Returns:
            A dictionary mapping item names to their metadata.
        """
        return {
            name: self.get_item_info(name, include_name)
            for name in self
            if self.get_item_info(name) is not None
        }

    def items_with_info(self) -> list[tuple[str, Any, dict[str, Any]]]:
        """Get a list of (key, value, metadata) tuples for all items.

        Returns:
            A list of tuples with key, value, and metadata dictionary.
        """
        return [(name, self[name], self.sources.get(name, {})) for name in self]

    def get_builtin_items(self) -> dict[str, Any]:
        """Get all built-in items in the catalog.

        Returns:
            Dictionary of built-in items.
        """
        return {name: self[name] for name in self if self.sources.get(name, {}).get("is_builtin", False)}

    def get_custom_items(self) -> dict[str, Any]:
        """Get all custom (non-builtin) items in the catalog.

        Returns:
            Dictionary of custom items.
        """
        return {name: self[name] for name in self if not self.sources.get(name, {}).get("is_builtin", False)}

    def discover_items_in_dir(self, dir_path: str, **kwargs) -> int:
        """Discover and register items from a directory.

        This implements the template method pattern, delegating specific behavior
        to _get_files_to_process and _process_file methods that subclasses must implement.

        Args:
            dir_path: Path to the directory to scan.
            **kwargs: Additional arguments for specific catalog types.

        Returns:
            Number of items discovered and registered.

        Raises:
            ResourceError: If directory doesn't exist.
        """
        path = Path(dir_path)
        if not path.is_dir():
            raise ResourceError(
                f"Directory not found: {dir_path}. Couldn't load {self.name}.",
                resource_type=self.name,
                resource_name=dir_path,
            )

        total_items = 0
        files = self._get_files_to_process(path, **kwargs)

        for file_path in files:
            items_added = self._process_file(file_path, **kwargs)
            total_items += items_added

        return total_items

    @abstractmethod
    def _get_files_to_process(self, dir_path: Path, **kwargs) -> list[Path]:
        """Get list of files to process from a directory.

        Args:
            dir_path: Path to the directory.
            **kwargs: Additional arguments for filtering files.

        Returns:
            List of Path objects to process.
        """

    @abstractmethod
    def _process_file(self, file_path: Path, **kwargs) -> int:
        """Process a single file and register any discovered items.

        Args:
            file_path: Path to the file.
            **kwargs: Additional arguments for processing.

        Returns:
            Number of items registered from this file.
        """


class CallableCatalog(Catalog):
    """Catalog specialized for Python callables like Nornir tasks and filters.

    This catalog extends BaseCatalog with functionality for:
    - Discovering Python modules in directories
    - Registering functions from modules based on predicates
    - Tracking built-in vs custom items
    """

    def register(
        self, name: str, item: Any, module_path: str | None = None, module_name: str | None = None, **kwargs
    ) -> Any:
        """Register a Python function/class with module tracking.

        Args:
            name: The name of the item.
            item: The item to register.
            module_path: Path to the module file.
            module_name: Python dotted module name.
            **kwargs: Additional metadata.

        Returns:
            The registered item.

        Raises:
            CatalogError: If a custom item tries to override a built-in.
        """
        if module_name is None and hasattr(item, "__module__"):
            module_name = getattr(item, "__module__", None)

        is_builtin = bool(module_name and module_name.startswith("nornflow.builtins"))

        if name in self and self.sources.get(name, {}).get("is_builtin", False):
            raise CatalogError(
                f"Cannot override built-in '{name}' with a custom implementation", catalog_name=self.name
            )

        return super().register(
            name, item, module_path=module_path, module_name=module_name, is_builtin=is_builtin, **kwargs
        )

    def register_from_module(
        self,
        module: Any,
        predicate: Callable[[Any], bool] | None = None,
        transform_item: Callable[[Any], Any] | None = None,
    ) -> int:
        """Register items from a module that match the predicate.

        Args:
            module: The module to extract items from.
            predicate: Optional function to filter items (e.g., is_task).
            transform_item: Optional function to transform items before registration.

        Returns:
            Number of items registered.
        """
        module_path = getattr(module, "__file__", None)
        module_name = getattr(module, "__name__", None)

        if predicate is None:
            predicate = callable

        count = 0

        for name, obj in inspect.getmembers(module, predicate):
            # Transform the item if needed
            # for example, for nornir filters catalog, we need to extract parameters
            if transform_item:
                obj = transform_item(obj)

            self.register(name, obj, module_path=module_path, module_name=module_name)
            count += 1

        return count

    def _get_files_to_process(self, dir_path: Path, **kwargs) -> list[Path]:
        """Get Python files from a directory.

        Args:
            dir_path: Path to the directory.
            **kwargs: Additional arguments (unused).

        Returns:
            List of Python files to process.
        """
        return [py_file for py_file in dir_path.rglob("*.py") if not py_file.name.startswith("__")]

    def _process_file(self, file_path: Path, **kwargs) -> int:
        """Process a Python file by importing it and registering its items.

        Args:
            file_path: Path to the Python file.
            **kwargs: May contain 'predicate' and 'transform_item' for filtering/processing.

        Returns:
            Number of items registered from this file.

        Raises:
            CoreError: If module import fails.
        """
        predicate = kwargs.get("predicate")
        transform_item = kwargs.get("transform_item")
        module_name = file_path.stem
        module_path = str(file_path)

        try:
            module = import_module_from_path(module_name, module_path)
            return self.register_from_module(module, predicate, transform_item)
        except Exception as e:
            raise CoreError(
                f"Failed to import module '{module_name}' from '{module_path}': {e!s}",
                component="ItemDiscovery",
            ) from e

    def discover_items_in_dir(
        self,
        dir_path: str,
        predicate: Callable[[Any], bool] | None = None,
        transform_item: Callable[[Any], Any] | None = None,
        **kwargs,
    ) -> int:
        """Discover and register items from Python modules in a directory.

        Args:
            dir_path: Path to the directory to scan.
            predicate: Function to filter items to register.
            transform_item: Function to transform items before registration.
            **kwargs: Additional arguments (passed to base implementation).

        Returns:
            Number of items discovered and registered.

        Raises:
            ResourceError: If directory doesn't exist.
            CoreError: If module import fails.
        """
        return super().discover_items_in_dir(
            dir_path, predicate=predicate, transform_item=transform_item, **kwargs
        )

    def get_sources_by_module(self) -> dict[str, list[str]]:
        """Get items grouped by their source modules.

        Returns:
            Dictionary mapping module names to lists of item names.
        """
        modules: dict[str, list[str]] = {}

        for name in self:
            module_name = self.sources.get(name, {}).get("module_name")
            if not module_name:
                continue

            if module_name not in modules:
                modules[module_name] = []

            modules[module_name].append(name)

        return modules


class FileCatalog(Catalog):
    """Catalog for file resources like workflow definitions.

    This catalog extends BaseCatalog with functionality for:
    - Discovering files in directories based on custom predicates
    - Registering file paths rather than importing modules
    """

    def _get_files_to_process(self, dir_path: Path, **kwargs) -> list[Path]:
        """Get all files from a directory based on recursive flag.

        Args:
            dir_path: Path to the directory.
            **kwargs: Contains 'recursive' flag to control directory traversal.

        Returns:
            List of files to process.
        """
        recursive = kwargs.get("recursive", True)
        glob_method = dir_path.rglob if recursive else dir_path.glob
        return list(glob_method("*"))

    def _process_file(self, file_path: Path, **kwargs) -> int:
        """Process a file by applying predicate and registering if matched.

        Args:
            file_path: Path to the file.
            **kwargs: Contains 'predicate' for filtering files.

        Returns:
            1 if the file was registered, 0 otherwise.
        """
        predicate = kwargs.get("predicate")

        if file_path.is_file() and predicate and predicate(file_path):
            self.register(name=file_path.name, item=file_path, file_path=str(file_path))
            return 1
        return 0

    def discover_items_in_dir(
        self, dir_path: str, predicate: Callable[[Path], bool], recursive: bool = True, **kwargs
    ) -> int:
        """Discover and register file paths in a directory.

        Args:
            dir_path: Path to the directory to scan.
            predicate: Function to determine if a file should be included.
            recursive: Whether to search recursively through subdirectories.
            **kwargs: Additional arguments (passed to base implementation).

        Returns:
            Number of files discovered and registered.

        Raises:
            ResourceError: If directory doesn't exist.
        """
        return super().discover_items_in_dir(dir_path, predicate=predicate, recursive=recursive, **kwargs)

    def get_by_extension(self, extension: str) -> dict[str, Path]:
        """Get all files with a specific extension.

        Args:
            extension: File extension to filter by (with or without dot).

        Returns:
            Dictionary of items with matching extension.
        """
        if not extension.startswith("."):
            extension = f".{extension}"

        return {
            name: path
            for name, path in self.items()
            if isinstance(path, Path) and path.suffix.lower() == extension.lower()
        }
