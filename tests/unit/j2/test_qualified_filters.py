"""Tests for qualified Jinja2 filter names and environment filter sync."""

import pytest

from nornflow.constants import (
    BUILTIN_NAMESPACE,
    LOCAL_NAMESPACE,
    TIER_BUILTIN,
    TIER_LOCAL,
    TIER_PACKAGE,
)
from nornflow.exceptions import AssetAmbiguityError
from nornflow.j2 import Jinja2Service


def _sync_filters(service: Jinja2Service) -> None:
    """Re-sync environment filters after manual catalog changes."""
    service.j2_filters_catalog.finalize_package_tier()
    Jinja2Service._sync_environment_filters(service)


class TestQualifiedJinjaFilterNames:
    """Tests for dotted qualified filter names in Jinja2 templates."""

    def test_sync_registers_qualified_and_bare_aliases(self, jinja2_service):
        """Qualified catalog keys and unambiguous bare names land in environment.filters."""
        filters = jinja2_service.environment.filters

        assert "nornflow.is_set" in filters
        assert "is_set" in filters
        assert filters["is_set"] is filters["nornflow.is_set"]

    def test_stdlib_filters_preserved_after_sync(self, jinja2_service):
        """Sync must merge stdlib filters before catalog keys (regression guard)."""
        result = jinja2_service.resolve_string("{{ 'hello' | upper }}", {})
        assert result == "HELLO"

    def test_qualified_builtin_filter_renders_in_template(self, jinja2_service):
        """Pipe syntax accepts qualified builtin names such as nornflow.is_set."""
        result = jinja2_service.resolve_string(
            "{{ 'my_var' | nornflow.is_set }}",
            {"my_var": "present"},
        )
        assert result == "True"

        result = jinja2_service.resolve_string(
            "{{ 'missing_var' | nornflow.is_set }}",
            {},
        )
        assert result == "False"

    def test_bare_and_qualified_builtin_filters_are_equivalent(self, jinja2_service):
        """Bare and qualified names invoke the same callable when unambiguous."""
        context = {"flag": "yes"}
        bare = jinja2_service.resolve_string("{{ 'flag' | is_set }}", context)
        qualified = jinja2_service.resolve_string("{{ 'flag' | nornflow.is_set }}", context)
        assert bare == qualified == "True"

    def test_qualified_local_filter_renders_in_template(self, jinja2_service):
        """Pipe syntax accepts qualified local filter names."""

        def local_tag(value: str) -> str:
            return f"local:{value}"

        catalog = jinja2_service.j2_filters_catalog
        catalog.register("tag", local_tag, namespace=LOCAL_NAMESPACE, tier=TIER_LOCAL)
        _sync_filters(jinja2_service)

        filters = jinja2_service.environment.filters
        assert "local.tag" in filters

        result = jinja2_service.resolve_string("{{ 'payload' | local.tag }}", {})
        assert result == "local:payload"

    def test_local_shadow_bare_uses_tier_winner_qualified_uses_local(self, jinja2_service):
        """Bare pipe resolves tier winner; qualified pipe selects the namespaced copy."""

        def builtin_dup(value: str) -> str:
            return f"builtin:{value}"

        def local_dup(value: str) -> str:
            return f"local:{value}"

        catalog = jinja2_service.j2_filters_catalog
        catalog.register("dup_filter", builtin_dup, namespace=BUILTIN_NAMESPACE, tier=TIER_BUILTIN)
        catalog.register("dup_filter", local_dup, namespace=LOCAL_NAMESPACE, tier=TIER_LOCAL)
        _sync_filters(jinja2_service)

        bare = jinja2_service.resolve_string("{{ 'x' | dup_filter }}", {})
        qualified = jinja2_service.resolve_string("{{ 'x' | local.dup_filter }}", {})

        assert bare == "builtin:x"
        assert qualified == "local:x"

    def test_context_variable_does_not_shadow_qualified_filter(self, jinja2_service):
        """A context key matching the namespace prefix does not break qualified filters."""
        context = {"nornflow": {"is_set": "not-a-filter"}}
        result = jinja2_service.resolve_string(
            "{{ 'my_var' | nornflow.is_set }}",
            {**context, "my_var": "value"},
        )
        assert result == "True"

    def test_variable_dot_access_is_unrelated_to_filter_namespace(self, jinja2_service):
        """Dots in variable expressions remain attribute lookup, not catalog resolution."""
        result = jinja2_service.resolve_string("{{ nested.key }}", {"nested": {"key": "from-var"}})
        assert result == "from-var"

    def test_ambiguous_bare_name_not_exposed_as_filter_alias(self, jinja2_service):
        """Package-vs-package bare ambiguity must not register a bare filter alias."""

        def pkg_a(value: str) -> str:
            return f"a:{value}"

        def pkg_b(value: str) -> str:
            return f"b:{value}"

        catalog = jinja2_service.j2_filters_catalog
        catalog.register("ambig_filter", pkg_a, namespace="pkg_a", tier=TIER_PACKAGE)
        catalog.register("ambig_filter", pkg_b, namespace="pkg_b", tier=TIER_PACKAGE)
        _sync_filters(jinja2_service)

        filters = jinja2_service.environment.filters
        assert "pkg_a.ambig_filter" in filters
        assert "pkg_b.ambig_filter" in filters
        assert "ambig_filter" not in filters

        with pytest.raises(AssetAmbiguityError):
            catalog.resolve("ambig_filter")

        result_a = jinja2_service.resolve_string("{{ 'x' | pkg_a.ambig_filter }}", {})
        result_b = jinja2_service.resolve_string("{{ 'x' | pkg_b.ambig_filter }}", {})
        assert result_a == "a:x"
        assert result_b == "b:x"
