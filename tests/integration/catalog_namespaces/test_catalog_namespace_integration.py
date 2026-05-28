"""Integration tests for catalog namespace isolation across all resource types."""

import importlib

import pytest

import nornflow.builtins.filters as builtin_filters
import nornflow.builtins.tasks as builtin_tasks
from nornflow.builtins.hooks import IfHook
from nornflow.constants import BUILTIN_NAMESPACE, LOCAL_NAMESPACE
from nornflow.exceptions import AssetAmbiguityError, AssetNotFoundError
from nornflow.nornflow import NornFlow

from tests.integration.catalog_namespaces.lab_builder import (
    DOTTED_WORKFLOW,
    ECHO_TASK,
    GROUPS_FILTER,
    PKG_ALPHA,
    PKG_BETA,
    PKG_ONLY_BLUEPRINT,
    PKG_ONLY_FILTER,
    PKG_ONLY_HOOK,
    PKG_ONLY_J2,
    PKG_ONLY_TASK,
    PKG_ONLY_WORKFLOW,
    SHARED_BLUEPRINT,
    SHARED_FILTER,
    SHARED_HOOK,
    SHARED_J2,
    SHARED_TASK,
    SHARED_WORKFLOW,
)


def _qualified(namespace: str, bare: str) -> str:
    return f"{namespace}.{bare}"


class TestTasksCatalogIntegration:
    """Tasks catalog namespace resolution through NornFlow startup."""

    def test_qualified_keys_exist_for_all_tiers(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.tasks_catalog
        assert _qualified(BUILTIN_NAMESPACE, "set") in catalog
        assert _qualified(LOCAL_NAMESPACE, SHARED_TASK) in catalog
        assert _qualified(PKG_ALPHA, SHARED_TASK) in catalog
        assert _qualified(PKG_BETA, SHARED_TASK) in catalog

    def test_bare_builtin_task_resolves_to_nornflow(self, nornflow_lab: NornFlow) -> None:
        assert nornflow_lab.tasks_catalog.resolve("set") is builtin_tasks.set

    def test_local_echo_does_not_steal_bare_builtin_name(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.tasks_catalog
        assert catalog.resolve(ECHO_TASK) is builtin_tasks.echo
        assert catalog.resolve(_qualified(LOCAL_NAMESPACE, ECHO_TASK)) is catalog[
            _qualified(LOCAL_NAMESPACE, ECHO_TASK)
        ]

    def test_bare_three_tier_collision_resolves_to_local(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.tasks_catalog
        local_task = catalog.resolve(SHARED_TASK)
        assert local_task is catalog[_qualified(LOCAL_NAMESPACE, SHARED_TASK)]
        assert local_task is not catalog[_qualified(PKG_ALPHA, SHARED_TASK)]

    def test_qualified_package_tasks_are_distinct(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.tasks_catalog
        alpha = catalog.resolve(_qualified(PKG_ALPHA, SHARED_TASK))
        beta = catalog.resolve(_qualified(PKG_BETA, SHARED_TASK))
        assert alpha is not beta

    def test_package_only_bare_name_is_ambiguous(self, nornflow_lab: NornFlow) -> None:
        with pytest.raises(AssetAmbiguityError):
            nornflow_lab.tasks_catalog.resolve(PKG_ONLY_TASK)

    def test_collision_metadata_lists_peers(self, nornflow_lab: NornFlow) -> None:
        sources = nornflow_lab.tasks_catalog.sources
        collision = sources[_qualified(PKG_ALPHA, SHARED_TASK)]["collision"]
        assert LOCAL_NAMESPACE in collision
        assert PKG_BETA in collision


class TestFiltersCatalogIntegration:
    """Inventory filters catalog namespace resolution."""

    def test_bare_builtin_filter_wins_over_local(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.filters_catalog
        bare = catalog.resolve(GROUPS_FILTER)
        assert bare[0] is builtin_filters.groups
        local_qualified = catalog.resolve(_qualified(LOCAL_NAMESPACE, GROUPS_FILTER))
        assert local_qualified is catalog[_qualified(LOCAL_NAMESPACE, GROUPS_FILTER)]
        assert local_qualified[0] is not builtin_filters.groups

    def test_bare_shared_filter_resolves_to_local(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.filters_catalog
        assert catalog.resolve(SHARED_FILTER) is catalog[_qualified(LOCAL_NAMESPACE, SHARED_FILTER)]

    def test_package_only_filter_is_ambiguous(self, nornflow_lab: NornFlow) -> None:
        with pytest.raises(AssetAmbiguityError):
            nornflow_lab.filters_catalog.resolve(PKG_ONLY_FILTER)

    def test_qualified_package_filters_resolve(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.filters_catalog
        alpha = catalog.resolve(_qualified(PKG_ALPHA, PKG_ONLY_FILTER))
        beta = catalog.resolve(_qualified(PKG_BETA, PKG_ONLY_FILTER))
        assert alpha[0] is not beta[0]


class TestWorkflowsCatalogIntegration:
    """Workflow file catalog namespace resolution."""

    def test_bare_workflow_resolves_to_local(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.workflows_catalog
        assert catalog.resolve(SHARED_WORKFLOW) == catalog[_qualified(LOCAL_NAMESPACE, SHARED_WORKFLOW)]

    def test_dotted_filename_bare_and_qualified(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.workflows_catalog
        assert catalog.resolve(DOTTED_WORKFLOW) == catalog[_qualified(LOCAL_NAMESPACE, DOTTED_WORKFLOW)]
        assert catalog.resolve(_qualified(PKG_ALPHA, DOTTED_WORKFLOW)) == catalog[
            _qualified(PKG_ALPHA, DOTTED_WORKFLOW)
        ]

    def test_package_only_workflow_is_ambiguous(self, nornflow_lab: NornFlow) -> None:
        with pytest.raises(AssetAmbiguityError):
            nornflow_lab.workflows_catalog.resolve(PKG_ONLY_WORKFLOW)

    def test_qualified_workflows_are_package_scoped(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.workflows_catalog
        alpha = catalog.resolve(_qualified(PKG_ALPHA, SHARED_WORKFLOW))
        beta = catalog.resolve(_qualified(PKG_BETA, SHARED_WORKFLOW))
        assert alpha != beta


class TestBlueprintsCatalogIntegration:
    """Blueprint file catalog namespace resolution."""

    def test_bare_blueprint_resolves_to_local(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.blueprints_catalog
        assert catalog.resolve(SHARED_BLUEPRINT) == catalog[_qualified(LOCAL_NAMESPACE, SHARED_BLUEPRINT)]

    def test_package_only_blueprint_is_ambiguous(self, nornflow_lab: NornFlow) -> None:
        with pytest.raises(AssetAmbiguityError):
            nornflow_lab.blueprints_catalog.resolve(PKG_ONLY_BLUEPRINT)

    def test_qualified_blueprints_differ_by_package(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.blueprints_catalog
        assert catalog.resolve(_qualified(PKG_ALPHA, SHARED_BLUEPRINT)) != catalog.resolve(
            _qualified(PKG_BETA, SHARED_BLUEPRINT)
        )


class TestHooksCatalogIntegration:
    """Hooks catalog namespace resolution (import-time registration)."""

    def test_bare_builtin_hook_resolves(self, nornflow_lab: NornFlow) -> None:
        assert nornflow_lab.hooks_catalog.resolve("if") is IfHook

    def test_bare_shared_hook_resolves_to_local(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.hooks_catalog
        assert catalog.resolve(SHARED_HOOK) is catalog[_qualified(LOCAL_NAMESPACE, SHARED_HOOK)]

    def test_package_only_hook_is_ambiguous(self, nornflow_lab: NornFlow) -> None:
        with pytest.raises(AssetAmbiguityError):
            nornflow_lab.hooks_catalog.resolve(PKG_ONLY_HOOK)

    def test_qualified_package_hooks_are_distinct(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.hooks_catalog
        alpha = catalog.resolve(_qualified(PKG_ALPHA, SHARED_HOOK))
        beta = catalog.resolve(_qualified(PKG_BETA, SHARED_HOOK))
        assert alpha is not beta


class TestJ2FiltersCatalogIntegration:
    """Jinja2 filters catalog namespace resolution via Jinja2Service."""

    def test_bare_builtin_j2_filter_available(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.j2_filters_catalog
        assert "is_set" in catalog.get_unambiguous_bare_names()
        assert catalog.resolve("is_set") is catalog.resolve(_qualified(BUILTIN_NAMESPACE, "is_set"))

    def test_bare_shared_j2_filter_resolves_to_local(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.j2_filters_catalog
        assert catalog.resolve(SHARED_J2) is catalog[_qualified(LOCAL_NAMESPACE, SHARED_J2)]

    def test_package_only_j2_filter_is_ambiguous(self, nornflow_lab: NornFlow) -> None:
        with pytest.raises(AssetAmbiguityError):
            nornflow_lab.j2_filters_catalog.resolve(PKG_ONLY_J2)

    def test_qualified_j2_filters_registered(self, nornflow_lab: NornFlow) -> None:
        catalog = nornflow_lab.j2_filters_catalog
        assert _qualified(PKG_ALPHA, SHARED_J2) in catalog
        assert _qualified(PKG_BETA, SHARED_J2) in catalog


class TestProcessorsPackageDiscovery:
    """Processors are not catalog-backed; verify package discovery only."""

    def test_both_packages_expose_processor_dirs(self, nornflow_lab: NornFlow) -> None:
        loader = nornflow_lab.package_loader
        assert loader is not None
        dirs = loader.get_resource_dirs("processors")
        pkg_names = {name for name, _ in dirs}
        assert pkg_names == {PKG_ALPHA, PKG_BETA}

    def test_processor_modules_imported_during_init(self, nornflow_lab: NornFlow) -> None:
        alpha = importlib.import_module(f"{PKG_ALPHA}.processors.proc_alpha")
        beta = importlib.import_module(f"{PKG_BETA}.processors.proc_beta")
        assert alpha.INTEG_MARKER == "alpha"
        assert beta.INTEG_MARKER == "beta"


class TestCrossCatalogConsistency:
    """Sanity checks that every catalog finalized metadata."""

    def test_all_catalogs_have_collision_metadata(self, nornflow_lab: NornFlow) -> None:
        catalogs = [
            nornflow_lab.tasks_catalog,
            nornflow_lab.filters_catalog,
            nornflow_lab.workflows_catalog,
            nornflow_lab.blueprints_catalog,
            nornflow_lab.hooks_catalog,
            nornflow_lab.j2_filters_catalog,
        ]
        for catalog in catalogs:
            for key, meta in catalog.sources.items():
                assert "bare_name" in meta, f"{catalog.name}:{key} missing bare_name"
                assert "collision" in meta, f"{catalog.name}:{key} missing collision"

    def test_missing_qualified_reference_raises(self, nornflow_lab: NornFlow) -> None:
        with pytest.raises(AssetNotFoundError):
            nornflow_lab.tasks_catalog.resolve("no_such_pkg.no_such_task")
