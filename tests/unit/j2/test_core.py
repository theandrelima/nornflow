"""Unit tests for nornflow.j2.core module."""

from unittest.mock import MagicMock, patch

import pytest
from jinja2 import Environment

from nornflow.j2 import Jinja2Service
from nornflow.j2.exceptions import Jinja2ServiceError, TemplateError, TemplateValidationError


class TestJinja2Service:
    """Test suite for Jinja2Service singleton."""

    def test_singleton_behavior(self):
        """Test that Jinja2Service is a singleton."""
        service1 = Jinja2Service()
        service2 = Jinja2Service()
        assert service1 is service2

    def test_environment_property(self):
        """Test that environment property returns a valid Environment instance."""
        service = Jinja2Service()
        env = service.environment
        assert isinstance(env, Environment)

    @patch.object(Jinja2Service, "compile_template")
    def test_resolve_string_success(self, mock_compile):
        """Test resolve_string with valid template."""
        mock_template = MagicMock()
        mock_template.render.return_value = "resolved"
        mock_compile.return_value = mock_template

        service = Jinja2Service()
        result = service.resolve_string("{{ var }}", {"var": "value"})

        assert result == "resolved"
        mock_compile.assert_called_once_with("{{ var }}")
        mock_template.render.assert_called_once_with({"var": "value"})

    @patch.object(Jinja2Service, "compile_template")
    def test_resolve_string_undefined_error(self, mock_compile):
        """Test resolve_string raises TemplateError on undefined variable."""
        from jinja2 import UndefinedError
        mock_compile.side_effect = UndefinedError("Undefined variable")

        service = Jinja2Service()
        with pytest.raises(TemplateError, match="Undefined variable"):
            service.resolve_string("{{ invalid }}", {})

    @patch.object(Jinja2Service, "compile_template")
    def test_resolve_string_syntax_error(self, mock_compile):
        """Test resolve_string raises TemplateError on syntax error."""
        from jinja2 import TemplateSyntaxError
        mock_compile.side_effect = TemplateSyntaxError("Syntax error", 1, "template")

        service = Jinja2Service()
        with pytest.raises(TemplateError, match="Template syntax error"):
            service.resolve_string("{{ invalid", {})

    def test_resolve_string_non_template(self):
        """Test resolve_string returns plain string if not a template."""
        service = Jinja2Service()
        result = service.resolve_string("plain text", {})
        assert result == "plain text"

    def test_resolve_string_invalid_type(self):
        """Test resolve_string raises error for non-string input."""
        service = Jinja2Service()
        with pytest.raises(TemplateValidationError, match="Expected string"):
            service.resolve_string(123, {})

    def test_resolve_data_dict(self):
        """Test resolve_data with dict input."""
        with patch.object(Jinja2Service, "resolve_string") as mock_resolve:
            mock_resolve.return_value = "resolved_value"

            service = Jinja2Service()
            data = {"key": "{{ var }}"}
            context = {"var": "test"}

            result = service.resolve_data(data, context)

            assert result == {"key": "resolved_value"}
            mock_resolve.assert_called_once_with("{{ var }}", context, "")

    def test_resolve_data_list(self):
        """Test resolve_data with list input."""
        with patch.object(Jinja2Service, "resolve_string") as mock_resolve:
            mock_resolve.return_value = "item1"

            service = Jinja2Service()
            data = ["{{ var }}"]
            context = {"var": "item1"}

            result = service.resolve_data(data, context)

            assert result == ["item1"]
            mock_resolve.assert_called_once_with("{{ var }}", context, "")

    def test_resolve_data_tuple(self):
        """Test resolve_data with tuple input (normalized to list)."""
        with patch.object(Jinja2Service, "resolve_string") as mock_resolve:
            mock_resolve.return_value = "item"

            service = Jinja2Service()
            data = ("{{ var }}",)
            context = {"var": "item"}

            result = service.resolve_data(data, context)

            assert result == ["item"]

    def test_resolve_data_non_string(self):
        """Test resolve_data with non-string values."""
        service = Jinja2Service()
        data = {"key": 123}
        context = {}

        result = service.resolve_data(data, context)

        assert result == {"key": 123}

    def test_resolve_to_bool_true(self):
        """Test resolve_to_bool with boolean True."""
        service = Jinja2Service()
        result = service.resolve_to_bool(True, {})
        assert result is True

    def test_resolve_to_bool_false(self):
        """Test resolve_to_bool with boolean False."""
        service = Jinja2Service()
        result = service.resolve_to_bool(False, {})
        assert result is False

    def test_resolve_to_bool_template(self):
        """Test resolve_to_bool with template resolving to truthy."""
        with patch.object(Jinja2Service, "resolve_string") as mock_resolve:
            mock_resolve.return_value = "yes"

            service = Jinja2Service()
            result = service.resolve_to_bool("{{ var }}", {"var": "yes"})

            assert result is True
            mock_resolve.assert_called_once_with("{{ var }}", {"var": "yes"})

    def test_resolve_to_bool_plain_string(self):
        """Test resolve_to_bool with plain truthy string."""
        service = Jinja2Service()
        result = service.resolve_to_bool("true", {})
        assert result is True

    def test_resolve_to_bool_falsy_string(self):
        """Test resolve_to_bool with falsy string."""
        service = Jinja2Service()
        result = service.resolve_to_bool("false", {})
        assert result is False

    def test_to_bool_various_values(self):
        """Test to_bool with various inputs."""
        service = Jinja2Service()

        assert service.to_bool(True) is True
        assert service.to_bool(False) is False
        assert service.to_bool("yes") is True
        assert service.to_bool("no") is False
        assert service.to_bool("1") is True
        assert service.to_bool("0") is False
        assert service.to_bool(123) is True
        assert service.to_bool(0) is False

    def test_validate_template_success(self):
        """Test validate_template with valid template."""
        service = Jinja2Service()
        is_valid, error = service.validate_template("{{ valid }}")
        assert is_valid is True
        assert error == ""

    def test_validate_template_error(self):
        """Test validate_template with invalid template."""
        service = Jinja2Service()
        is_valid, error = service.validate_template("{{ invalid")
        assert is_valid is False
        assert "unexpected end of template" in error

    def test_is_template_true(self):
        """Test is_template detects Jinja2 markers."""
        service = Jinja2Service()
        assert service.is_template("{{ var }}") is True
        assert service.is_template("{% if %}") is True
        assert service.is_template("{# comment #}") is True
        assert service.is_template("{{- var -}}") is True

    def test_is_template_false(self):
        """Test is_template returns False for non-templates."""
        service = Jinja2Service()
        assert service.is_template("plain text") is False
        assert service.is_template("") is False
        assert service.is_template("no markers here") is False

    @patch("nornflow.j2.core.ALL_BUILTIN_J2_FILTERS", {"test_filter": lambda x: x})
    def test_initialize_environment_registers_filters(self):
        """Test _initialize_environment registers built-in filters."""
        with patch("nornflow.j2.core.CallableCatalog") as mock_catalog_class:
            mock_catalog = MagicMock()
            mock_catalog_class.return_value = mock_catalog

            service = Jinja2Service()
            service._initialize_environment(service)

            assert service._j2_filters_catalog is mock_catalog
            mock_catalog.register.assert_called()

    def test_register_custom_filters(self):
        """Test register_custom_filters discovers and registers filters."""
        # Reset singleton to ensure patch applies
        Jinja2Service._instance = None
        with patch("nornflow.j2.core.CallableCatalog") as mock_catalog_class, \
             patch("nornflow.j2.core.is_public_callable") as mock_predicate, \
             patch("os.path.exists", return_value=True), \
             patch("os.listdir", return_value=["filter.py"]):

            mock_catalog = MagicMock()
            mock_catalog_class.return_value = mock_catalog

            service = Jinja2Service()
            service.register_custom_filters(["/fake/dir"])

            mock_catalog.discover_items_in_dir.assert_called_with("/fake/dir", predicate=mock_predicate)

    def test_get_registered_j2_filters(self):
        """Test get_registered_j2_filters returns environment filters."""
        service = Jinja2Service()
        result = service.get_registered_j2_filters()
        assert isinstance(result, dict)
        assert len(result) > 0  # Should have built-in filters

    def test_j2_filters_catalog_property(self):
        """Test j2_filters_catalog property."""
        service = Jinja2Service()
        catalog = service.j2_filters_catalog
        assert catalog is not None

    def test_j2_filters_catalog_setter_raises_error(self):
        """Test j2_filters_catalog setter raises error."""
        service = Jinja2Service()
        with pytest.raises(Jinja2ServiceError, match="J2 filters catalog cannot be set directly"):
            service.j2_filters_catalog = "invalid"

    def test_environment_setter_invalid_type(self):
        """Test environment setter raises error for invalid type."""
        service = Jinja2Service()
        with pytest.raises(Jinja2ServiceError, match="Expected Environment instance"):
            service.environment = "invalid"

    @patch("nornflow.j2.core.Environment.from_string")
    def test_compile_template_success(self, mock_from_string):
        """Test compile_template caches and returns template."""
        mock_template = MagicMock()
        mock_from_string.return_value = mock_template

        service = Jinja2Service()
        result1 = service.compile_template("{{ test }}")
        result2 = service.compile_template("{{ test }}")

        assert result1 is mock_template
        assert result1 is result2  # Cached
        mock_from_string.assert_called_once()

    @patch("nornflow.j2.core.Environment.from_string")
    def test_compile_template_error(self, mock_from_string):
        """Test compile_template raises TemplateValidationError on error."""
        from jinja2 import TemplateSyntaxError
        mock_from_string.side_effect = TemplateSyntaxError("Error", 1, "template")

        service = Jinja2Service()
        with pytest.raises(TemplateValidationError):
            service.compile_template("{{ invalid")

    @patch("nornflow.j2.core.CallableCatalog")
    def test_initialize_with_settings(self, mock_catalog_class):
        """Test initialize_with_settings calls register_custom_filters."""
        with patch.object(Jinja2Service, "register_custom_filters") as mock_register:
            from nornflow.settings import NornFlowSettings

            settings = NornFlowSettings(local_j2_filters=["/dir"], nornir_config_file="/fake/config")
            Jinja2Service.initialize_with_settings(settings)

            mock_register.assert_called_once_with(["/dir"])