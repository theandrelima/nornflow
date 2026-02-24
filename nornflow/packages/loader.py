import importlib
from pathlib import Path

from nornflow.exceptions import ResourceError
from nornflow.logger import logger
from nornflow.packages.descriptor import PackageDescriptor


class PackageLoader:
    """Resolves installed package paths and discovers resource subdirectories.

    Instantiated once during NornFlow initialization with validated
    PackageDescriptor instances. Queried by each catalog load method
    to get filesystem paths for package resource directories.

    Args:
        descriptors: Validated PackageDescriptor instances from settings.
    """

    def __init__(self, descriptors: list[PackageDescriptor]):
        self._descriptors = descriptors

    def get_resource_dirs(self, resource_type: str) -> list[tuple[str, Path]]:
        """Get (package_name, directory_path) pairs for a given resource type.

        Iterates descriptors, skips those that don't include this resource type,
        and resolves filesystem paths for those that do. Missing subdirectories
        are logged at WARNING if explicitly requested, DEBUG otherwise.

        Args:
            resource_type: One of the valid resource type strings.

        Returns:
            List of (package_name, path_to_resource_dir) tuples for existing dirs.

        Raises:
            ResourceError: If a package cannot be imported.
        """
        result = []

        for desc in self._descriptors:
            if not desc.should_import(resource_type):
                continue

            resource_dir = self._resolve_resource_dir(desc.name, resource_type)

            if resource_dir:
                result.append((desc.name, resource_dir))
            elif desc.explicitly_includes(resource_type):
                logger.warning(
                    f"Package '{desc.name}' has no '{resource_type}/' directory, "
                    f"but '{resource_type}' is explicitly listed in its include config. Skipping."
                )
            else:
                logger.debug(
                    f"Package '{desc.name}' has no '{resource_type}/' directory. "
                    f"Skipping {resource_type} for this package."
                )

        return result

    def _resolve_resource_dir(self, package_name: str, resource_type: str) -> Path | None:
        """Resolve the filesystem path for a resource type within a package.

        Args:
            package_name: Python package import path.
            resource_type: Resource type subdirectory name.

        Returns:
            Path to the resource directory if it exists, None otherwise.

        Raises:
            ResourceError: If the package cannot be imported.
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError as e:
            raise ResourceError(
                f"Package '{package_name}' could not be imported. Is it installed?",
                resource_type="package",
                resource_name=package_name,
            ) from e

        package_file = getattr(package, "__file__", None)
        if not package_file:
            logger.warning(
                f"Package '{package_name}' has no __file__ attribute "
                f"(namespace packages are not supported). Skipping."
            )
            return None

        resource_dir = Path(package_file).parent / resource_type
        if not resource_dir.is_dir():
            return None

        logger.info(f"Found '{resource_type}' in package '{package_name}': {resource_dir}")
        return resource_dir