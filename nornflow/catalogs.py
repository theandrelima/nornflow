import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic_serdes.utils import load_file_to_dict

from nornflow.constants import (
    BUILTIN_NAMESPACE,
    LOCAL_NAMESPACE,
    TIER_BUILTIN,
    TIER_LOCAL,
    TIER_ORDER,
    TIER_PACKAGE,
)
from nornflow.exceptions import AssetAmbiguityError, AssetNotFoundError, CoreError, ResourceError
from nornflow.logger import logger
from nornflow.utils import import_module_from_path


def qualified_key(namespace: str, bare_name: str) -> str:
    """Build a qualified catalog key from namespace and bare name."""
    return f"{namespace}.{bare_name}"


def namespace_of(reference: str) -> str:
    """Return the namespace portion of a qualified reference."""
    return reference.split(".", 1)[0]


def _apply_registration_defaults(
    kwargs: dict[str, Any],
    *,
    is_builtin: bool,
    is_package: bool = False,
) -> None:
    """Fill namespace and tier on kwargs when the caller did not pass them."""
    if "namespace" in kwargs and "tier" in kwargs:
        return

    if is_builtin:
        kwargs.setdefault("namespace", BUILTIN_NAMESPACE)
        kwargs.setdefault("tier", TIER_BUILTIN)
        return

    if is_package:
        kwargs.setdefault("tier", TIER_PACKAGE)
        return

    kwargs.setdefault("namespace", LOCAL_NAMESPACE)
    kwargs.setdefault("tier", TIER_LOCAL)


class Catalog(ABC, dict[str, Any]):
    """Base catalog that tracks namespaced assets and supports tier-priority resolution."""

    def __init__(self, name: str):
        """Initialize an empty catalog with a name for error messages.

        Args:
            name: The name of this catalog.
        """
        super().__init__()
        self.name = name

        # Registration metadata keyed by qualified name (e.g. "nornflow.set").
        # Example: {"nornflow.set": {"bare_name": "set", "namespace": "nornflow", "tier": "builtin", ...}}
        self.sources: dict[str, dict[str, Any]] = {}

        # Bare name -> tier -> list of qualified keys sharing that bare name.
        # Example: {"set": {"builtin": ["nornflow.set"], "local": ["local.set"]}}
        self._bare_index: dict[str, dict[str, list[str]]] = {}

        # Bare name -> winning qualified key for bare resolution (when unambiguous).
        # Example: {"set": "nornflow.set", "backup": "local.backup"}
        self._bare_owners: dict[str, str] = {}

        # True after finalize_package_tier(); gates package-tier bare resolution.
        self._package_tier_finalized = False

    def __contains__(self, reference: str) -> bool:
        """Return True if a bare or qualified reference exists in the catalog."""
        return self._reference_exists(reference)

    def register_namespaced(
        self,
        bare_name: str,
        item: Any,
        namespace: str,
        tier: str,
        **kwargs: Any,
    ) -> Any:
        """Register an asset under a qualified namespace key.

        Args:
            bare_name: Unqualified asset name.
            item: Asset value to store.
            namespace: Catalog namespace (``nornflow``, ``local``, or package name).
            tier: Registration tier (``builtin``, ``local``, or ``package``).
            **kwargs: Extra fields merged into ``sources`` (module_name, description, ...).

        Returns:
            The registered item.
        """
        key = qualified_key(namespace, bare_name)
        super().__setitem__(key, item)
        self.sources[key] = {
            "registered_at": datetime.now(),
            "bare_name": bare_name,
            "namespace": namespace,
            "tier": tier,
            **kwargs,
        }

        tier_map = self._bare_index.setdefault(bare_name, {})
        tier_keys = tier_map.setdefault(tier, [])
        if key not in tier_keys:
            tier_keys.append(key)

        if tier == TIER_BUILTIN or (tier == TIER_LOCAL and bare_name not in self._bare_owners):
            self._bare_owners[bare_name] = key

        logger.debug(
            f"Registered item '{key}' (bare='{bare_name}', tier={tier}) in {self.name} catalog"
        )
        return item

    def register(self, name: str, item: Any, **kwargs: Any) -> Any:
        """Register an item, inferring namespace and tier when omitted.

        Args:
            name: Bare or legacy key for the item.
            item: Value to store.
            **kwargs: Metadata; may include ``namespace`` and ``tier``.

        Returns:
            The registered value.
        """
        namespace = kwargs.pop("namespace", None)
        tier = kwargs.pop("tier", None)
        bare_name = kwargs.pop("bare_name", None) or name

        if namespace and tier:
            return self.register_namespaced(bare_name, item, namespace, tier, **kwargs)

        inferred_namespace, inferred_tier = self._infer_namespace_and_tier(item, kwargs)
        return self.register_namespaced(
            bare_name, item, inferred_namespace, inferred_tier, **kwargs
        )

    def _infer_namespace_and_tier(self, item: Any, kwargs: dict[str, Any]) -> tuple[str, str]:
        """Infer namespace and tier from metadata or item origin."""
        module_name = kwargs.get("module_name") or getattr(item, "__module__", None)

        if module_name and str(module_name).startswith("nornflow.builtins"):
            return BUILTIN_NAMESPACE, TIER_BUILTIN

        if kwargs.get("is_package"):
            namespace = kwargs.get("namespace")
            if not namespace:
                raise ResourceError(
                    f"Package {self.name} registration requires namespace when is_package=True",
                    resource_type=self.name,
                    resource_name=kwargs.get("bare_name", "unknown"),
                )
            return namespace, TIER_PACKAGE

        return LOCAL_NAMESPACE, TIER_LOCAL

    def finalize_package_tier(self) -> None:
        """Assign bare owners for unambiguous single-package names after all packages load."""
        for bare_name, tier_map in self._bare_index.items():
            if bare_name in self._bare_owners:
                continue

            package_keys = tier_map.get(TIER_PACKAGE, [])
            if len(package_keys) != 1:
                continue

            self._bare_owners[bare_name] = package_keys[0]

        self._package_tier_finalized = True

    def compute_collision_metadata(self) -> None:
        """Compute collision display metadata for every registered asset."""
        for bare_name, tier_map in self._bare_index.items():
            all_keys = []
            for keys in tier_map.values():
                all_keys.extend(keys)

            winner = self._bare_owners.get(bare_name)
            package_keys = tier_map.get(TIER_PACKAGE, [])
            package_ambiguous = len(package_keys) > 1

            for key in all_keys:
                peers = [peer for peer in all_keys if peer != key]
                peer_names = sorted({namespace_of(peer) for peer in peers})
                collision = self._build_collision_display(
                    key, peer_names, winner, package_ambiguous, package_keys
                )
                self.sources[key]["collision"] = collision
                self.sources[key]["bare_name"] = bare_name
                self.sources[key]["bare_winner"] = winner
                self.sources[key]["bare_ambiguous"] = (
                    package_ambiguous and key in package_keys and not winner
                )

    def _build_collision_display(
        self,
        qualified_key: str,
        peer_names: list[str],
        winner: str | None,
        package_ambiguous: bool,
        package_keys: list[str],
    ) -> str:
        """Build the Collision column display string for a catalog entry."""
        if not peer_names:
            return ""

        peer_text = ", ".join(peer_names)
        if package_ambiguous and qualified_key in package_keys and not winner:
            return f"{peer_text} (bare ambiguous)"
        if winner:
            return f"{peer_text} (bare → {winner})"
        return peer_text

    def resolve(self, reference: str) -> Any:
        """Resolve a bare or qualified reference to its catalog value.

        Args:
            reference: Bare name or ``namespace.name`` qualified reference.

        Returns:
            The registered asset value.

        Raises:
            AssetNotFoundError: If the reference does not exist.
            AssetAmbiguityError: If a bare reference is same-tier ambiguous.
        """
        key = self.resolve_key(reference)
        return self[key]

    def resolve_key(self, reference: str) -> str:
        """Resolve a reference to its qualified catalog key.

        Args:
            reference: Bare name or qualified reference.

        Returns:
            Qualified catalog key.

        Raises:
            AssetNotFoundError: If the reference does not exist.
            AssetAmbiguityError: If a bare reference is same-tier ambiguous.
        """
        qualified_key_match = self._qualified_key_if_present(reference)
        if qualified_key_match is not None:
            return qualified_key_match

        bare_name = self._bare_name_if_registered(reference)
        if bare_name is None:
            raise AssetNotFoundError(reference, self.name)

        tier_map = self._bare_index[bare_name]

        if bare_name in self._bare_owners:
            return self._bare_owners[bare_name]

        package_keys = tier_map.get(TIER_PACKAGE, [])
        if self._package_tier_finalized and len(package_keys) > 1:
            raise AssetAmbiguityError(reference, self.name, package_keys, TIER_PACKAGE)

        for tier in TIER_ORDER:
            keys = tier_map.get(tier, [])
            if not keys:
                continue

            # Skip package tier until all packages registered and finalize_package_tier() ran.
            if tier == TIER_PACKAGE and not self._package_tier_finalized:
                continue

            if len(keys) > 1:
                raise AssetAmbiguityError(reference, self.name, keys, tier)

            return keys[0]

        raise AssetNotFoundError(reference, self.name)

    def _reference_exists(self, reference: str) -> bool:
        """Return True when reference is a known bare name or qualified catalog key."""
        if self._bare_name_if_registered(reference) is not None:
            return True
        return self._qualified_key_if_present(reference) is not None

    def _bare_name_if_registered(self, reference: str) -> str | None:
        """Return bare_name when reference appears in the bare index."""
        if reference in self._bare_index:
            return reference
        return None

    def _qualified_key_if_present(self, reference: str) -> str | None:
        """Return reference when it is an exact qualified key in this catalog."""
        if "." not in reference:
            return None
        if dict.__contains__(self, reference):
            return reference
        return None

    def get_collision_peers(self, qualified_key: str) -> list[str]:
        """Return other qualified keys sharing the same bare name."""
        bare_name = self.sources.get(qualified_key, {}).get("bare_name")
        if not bare_name:
            return []

        tier_map = self._bare_index.get(bare_name, {})
        peers = []
        for keys in tier_map.values():
            peers.extend(key for key in keys if key != qualified_key)
        return peers

    def get_bare_collisions(self, bare_name: str) -> list[str]:
        """Return all qualified keys registered under a bare name."""
        tier_map = self._bare_index.get(bare_name, {})
        result = []
        for keys in tier_map.values():
            result.extend(keys)
        return result

    def get_unambiguous_bare_names(self) -> list[str]:
        """Return bare names that resolve without ambiguity."""
        names = []
        for bare_name in self._bare_index:
            try:
                self.resolve(bare_name)
            except (AssetAmbiguityError, AssetNotFoundError):
                continue
            names.append(bare_name)
        return names

    @property
    def is_empty(self) -> bool:
        """Check if the catalog is empty."""
        return len(self) == 0

    def get_item_info(self, name: str, include_name: bool = True) -> dict[str, Any] | None:
        """Get detailed information about an item."""
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
        """Get information about all items in the catalog."""
        return {
            name: self.get_item_info(name, include_name)
            for name in self
            if self.get_item_info(name) is not None
        }

    def items_with_info(self) -> list[tuple[str, Any, dict[str, Any]]]:
        """Get a list of (key, value, metadata) tuples for all items."""
        return [(name, self[name], self.sources.get(name, {})) for name in self]

    def get_builtin_items(self) -> dict[str, Any]:
        """Get all built-in items in the catalog."""
        return {
            name: self[name]
            for name in self
            if self.sources.get(name, {}).get("tier") == TIER_BUILTIN
            or self.sources.get(name, {}).get("is_builtin", False)
        }

    def get_custom_items(self) -> dict[str, Any]:
        """Get all custom (non-builtin) items in the catalog."""
        return {
            name: self[name]
            for name in self
            if self.sources.get(name, {}).get("tier") != TIER_BUILTIN
            and not self.sources.get(name, {}).get("is_builtin", False)
        }


class DiscoverableCatalog(Catalog):
    """Catalog that supports discovering items from directories."""

    max_description_size = 100

    def discover_items_in_dir(self, dir_path: str, **kwargs: Any) -> int:
        """Discover and register items from a directory."""
        logger.info(f"Starting discovery of {self.name} items in directory: {dir_path}")
        path = Path(dir_path)
        if not path.is_dir():
            logger.error(f"Directory not found for {self.name} discovery: {dir_path}")
            raise ResourceError(
                f"Directory not found: {dir_path}. Couldn't load {self.name}.",
                resource_type=self.name,
                resource_name=dir_path,
            )

        total_items = 0
        files = self._get_files_to_process(path, **kwargs)
        logger.debug(f"Found {len(files)} files to process in {dir_path}")

        for file_path in files:
            items_added = self._process_file(file_path, **kwargs)
            total_items += items_added

        logger.info(
            f"Completed {self.name} discovery: {total_items} items registered from {len(files)} files"
        )
        return total_items

    @abstractmethod
    def _get_files_to_process(self, dir_path: Path, **kwargs: Any) -> list[Path]:
        """Get list of files to process from a directory."""

    @abstractmethod
    def _process_file(self, file_path: Path, **kwargs: Any) -> int:
        """Process a single file and register any discovered items."""


class ClassCatalog(Catalog):
    """Catalog specialized for class-based assets such as hooks."""

    def register(self, name: str, item: Any, **kwargs: Any) -> Any:
        """Register a class with metadata extraction."""
        if inspect.isclass(item):
            if not kwargs.get("description"):
                description = None
                if hasattr(item, "description") and item.description:
                    description = item.description
                elif item.__doc__:
                    first_line = item.__doc__.strip().split("\n", 1)[0].strip()
                    if first_line:
                        description = first_line
                if description:
                    kwargs["description"] = description

            if "module_name" not in kwargs:
                kwargs["module_name"] = getattr(item, "__module__", "") or ""

            module_name = kwargs["module_name"]
            is_builtin = module_name.startswith("nornflow.builtins")
            kwargs["is_builtin"] = is_builtin
            _apply_registration_defaults(kwargs, is_builtin=is_builtin)

        return super().register(name, item, **kwargs)


class CallableCatalog(DiscoverableCatalog):
    """Catalog specialized for Python callables like Nornir tasks and filters."""

    def register(
        self,
        name: str,
        item: Any,
        module_path: str | None = None,
        module_name: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Register a Python callable with module tracking."""
        if callable(item):
            description = self._extract_description_from_callable(item)
            kwargs.setdefault("description", description)

        if not module_name and hasattr(item, "__module__"):
            module_name = getattr(item, "__module__", None)

        is_builtin = bool(module_name and module_name.startswith("nornflow.builtins"))
        kwargs.setdefault("is_builtin", is_builtin)
        _apply_registration_defaults(
            kwargs,
            is_builtin=is_builtin,
            is_package=bool(kwargs.get("is_package")),
        )

        result = super().register(
            name, item, module_path=module_path, module_name=module_name, **kwargs
        )
        logger.debug(
            f"Registered callable '{name}' from module '{module_name}' in {self.name} catalog"
        )
        return result

    def _extract_description_from_callable(self, item: Any) -> str:
        """Extract description from a callable's docstring."""
        docstring = getattr(item, "__doc__", None)
        if not docstring:
            return "No description available"
        docstring = docstring.strip()
        if not docstring:
            return "No description available"
        first_line = docstring.split("\n", 1)[0].strip()
        if len(first_line) > self.max_description_size:
            first_line = first_line[: self.max_description_size - 3] + "..."
        return first_line

    def register_from_module(
        self,
        module: Any,
        predicate: Callable[[Any], bool] | None = None,
        transform_item: Callable[[Any], Any] | None = None,
        namespace: str | None = None,
        tier: str | None = None,
    ) -> int:
        """Register items from a module that match the predicate."""
        module_path = getattr(module, "__file__", None)
        module_name = getattr(module, "__name__", None)

        if predicate is None:
            predicate = callable

        count = 0
        register_kwargs = {}
        if namespace:
            register_kwargs["namespace"] = namespace
        if tier:
            register_kwargs["tier"] = tier

        for name, obj in inspect.getmembers(module, predicate):
            if transform_item:
                obj = transform_item(obj)

            self.register(
                name,
                obj,
                module_path=module_path,
                module_name=module_name,
                **register_kwargs,
            )
            count += 1

        logger.debug(f"Registered {count} items from module '{module_name}'")
        return count

    def _get_files_to_process(self, dir_path: Path, **kwargs: Any) -> list[Path]:
        """Get Python files from a directory."""
        return [py_file for py_file in dir_path.rglob("*.py") if not py_file.name.startswith("__")]

    def _process_file(self, file_path: Path, **kwargs: Any) -> int:
        """Process a Python file by importing it and registering its items."""
        predicate = kwargs.get("predicate")
        transform_item = kwargs.get("transform_item")
        namespace = kwargs.get("namespace")
        tier = kwargs.get("tier")
        module_name = file_path.stem
        module_path = str(file_path)

        try:
            module = import_module_from_path(module_name, module_path)
            count = self.register_from_module(
                module,
                predicate,
                transform_item,
                namespace=namespace,
                tier=tier,
            )
            logger.debug(f"Processed file '{file_path}': {count} items registered")
            return count
        except Exception as e:
            logger.exception(f"Failed to process file '{file_path}': {e}")
            raise CoreError(
                f"Failed to import module '{module_name}' from '{module_path}': {e!s}",
                component="ItemDiscovery",
            ) from e

    def discover_items_in_dir(
        self,
        dir_path: str,
        predicate: Callable[[Any], bool] | None = None,
        transform_item: Callable[[Any], Any] | None = None,
        namespace: str | None = None,
        tier: str | None = None,
        **kwargs: Any,
    ) -> int:
        """Discover and register items from Python modules in a directory."""
        return super().discover_items_in_dir(
            dir_path,
            predicate=predicate,
            transform_item=transform_item,
            namespace=namespace,
            tier=tier,
            **kwargs,
        )

    def get_sources_by_module(self) -> dict[str, list[str]]:
        """Get items grouped by their source modules."""
        modules = {}

        for name in self:
            module_name = self.sources.get(name, {}).get("module_name")
            if not module_name:
                continue

            if module_name not in modules:
                modules[module_name] = []

            modules[module_name].append(name)

        return modules


class FileCatalog(DiscoverableCatalog):
    """Catalog for file resources like workflow definitions."""

    nornflow_builtins_dir = Path(__file__).resolve().parent / "builtins"

    def register(self, name: str, item: Any, **kwargs: Any) -> Any:
        """Register a file path with description extraction from YAML."""
        if isinstance(item, Path):
            description = self._extract_description_from_file(item)
            kwargs.setdefault("description", description)
            is_builtin = item.resolve().is_relative_to(self.nornflow_builtins_dir)
            kwargs["is_builtin"] = is_builtin
            _apply_registration_defaults(
                kwargs,
                is_builtin=is_builtin,
                is_package=bool(kwargs.get("is_package")),
            )

        return super().register(name, item, **kwargs)

    def get_package_names(self) -> set[str]:
        """Return qualified keys for entries that originated from imported packages."""
        return {
            name
            for name in self
            if self.sources.get(name, {}).get("is_package", False)
            or self.sources.get(name, {}).get("tier") == TIER_PACKAGE
        }

    def _extract_description_from_file(self, file_path: Path) -> str:
        """Extract description from a file."""
        try:
            data = load_file_to_dict(file_path)
            if "workflow" in data:
                description = data["workflow"].get("description", "No description available")
            else:
                description = data.get("description", "No description available")
            if len(description) > self.max_description_size:
                description = description[: self.max_description_size - 3] + "..."
            return description
        except Exception:
            return "Could not load description from file"

    def _get_files_to_process(self, dir_path: Path, **kwargs: Any) -> list[Path]:
        """Get all files from a directory based on recursive flag."""
        recursive = kwargs.get("recursive", True)
        glob_method = dir_path.rglob if recursive else dir_path.glob
        return list(glob_method("*"))

    def _process_file(self, file_path: Path, **kwargs: Any) -> int:
        """Process a file by applying predicate and registering if matched."""
        predicate = kwargs.get("predicate")
        is_package = kwargs.get("is_package", False)
        namespace = kwargs.get("namespace", LOCAL_NAMESPACE)
        tier = kwargs.get("tier", TIER_PACKAGE if is_package else TIER_LOCAL)

        if file_path.is_file() and predicate and predicate(file_path):
            self.register(
                name=file_path.name,
                item=file_path,
                file_path=str(file_path),
                is_package=is_package,
                namespace=namespace,
                tier=tier,
            )
            logger.debug(f"Registered file '{file_path}' in {self.name} catalog")
            return 1
        return 0

    def discover_items_in_dir(
        self,
        dir_path: str,
        predicate: Callable[[Path], bool],
        recursive: bool = True,
        is_package: bool = False,
        namespace: str | None = None,
        tier: str | None = None,
        **kwargs: Any,
    ) -> int:
        """Discover and register file paths in a directory."""
        effective_namespace = namespace or LOCAL_NAMESPACE
        effective_tier = tier or (TIER_PACKAGE if is_package else TIER_LOCAL)
        return super().discover_items_in_dir(
            dir_path,
            predicate=predicate,
            recursive=recursive,
            is_package=is_package,
            namespace=effective_namespace,
            tier=effective_tier,
            **kwargs,
        )

    def get_by_extension(self, extension: str) -> dict[str, Path]:
        """Get all files with a specific extension."""
        if not extension.startswith("."):
            extension = f".{extension}"

        return {
            name: path
            for name, path in self.items()
            if isinstance(path, Path) and path.suffix.lower() == extension.lower()
        }
