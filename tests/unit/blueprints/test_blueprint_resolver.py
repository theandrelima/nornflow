import os
from pathlib import Path
from unittest.mock import patch

import pytest

from nornflow.exceptions import BlueprintError


class TestBlueprintResolver:
    """Tests for BlueprintResolver class."""

    def test_build_context_with_all_sources(self, blueprint_resolver, mock_vars_dir, mock_workflow_path, mock_workflow_roots, mock_cli_vars):
        """Test building context with all variable sources."""
        inline_vars = {"inline_var": "inline_value", "timeout": 15}
        
        with patch.dict(os.environ, {"NORNFLOW_VAR_env_var": "env_value"}):
            context = blueprint_resolver.build_context(
                vars_dir=mock_vars_dir,
                workflow_path=mock_workflow_path,
                workflow_roots=mock_workflow_roots,
                inline_workflow_vars=inline_vars,
                cli_vars=mock_cli_vars,
            )
        
        assert "cli_var" in context
        assert "inline_var" in context
        assert "env_var" in context

    def test_build_context_precedence_order(self, blueprint_resolver, mock_vars_dir, mock_workflow_path, mock_workflow_roots):
        """Test that CLI vars have highest precedence."""
        inline_vars = {"timeout": 15}
        cli_vars = {"timeout": 5}
        
        context = blueprint_resolver.build_context(
            vars_dir=mock_vars_dir,
            workflow_path=mock_workflow_path,
            workflow_roots=mock_workflow_roots,
            inline_workflow_vars=inline_vars,
            cli_vars=cli_vars,
        )
        
        assert context["timeout"] == 5

    def test_build_context_without_workflow_path(self, blueprint_resolver, mock_vars_dir, mock_workflow_roots):
        """Test building context without a workflow path."""
        cli_vars = {"cli_var": "cli_value"}
        
        context = blueprint_resolver.build_context(
            vars_dir=mock_vars_dir,
            workflow_path=None,
            workflow_roots=mock_workflow_roots,
            inline_workflow_vars=None,
            cli_vars=cli_vars,
        )
        
        assert context["cli_var"] == "cli_value"

    def test_build_context_with_environment_variables(self, blueprint_resolver, mock_vars_dir, mock_workflow_roots):
        """Test loading environment variables with NORNFLOW_VAR_ prefix."""
        with patch.dict(os.environ, {
            "NORNFLOW_VAR_test": "test_value",
            "NORNFLOW_VAR_another": "another_value",
            "OTHER_VAR": "ignored"
        }):
            context = blueprint_resolver.build_context(
                vars_dir=mock_vars_dir,
                workflow_path=None,
                workflow_roots=mock_workflow_roots,
                inline_workflow_vars=None,
                cli_vars=None,
            )
        
        assert context["test"] == "test_value"
        assert context["another"] == "another_value"
        assert "OTHER_VAR" not in context

    def test_build_context_domain_extraction(self, blueprint_resolver, mock_vars_dir, mock_workflow_path, mock_workflow_roots):
        """Test domain extraction from workflow path."""
        context = blueprint_resolver.build_context(
            vars_dir=mock_vars_dir,
            workflow_path=mock_workflow_path,
            workflow_roots=mock_workflow_roots,
            inline_workflow_vars=None,
            cli_vars=None,
        )
        
        assert isinstance(context, dict)

    def test_resolve_template_simple(self, blueprint_resolver):
        """Test resolving a simple Jinja2 template."""
        context = {"env": "prod", "region": "us-east"}
        result = blueprint_resolver.resolve_template("deployment_{{ env }}_{{ region }}", context)
        assert result == "deployment_prod_us-east"

    def test_resolve_template_with_filters(self, blueprint_resolver):
        """Test resolving template with Jinja2 filters."""
        context = {"name": "test_device"}
        result = blueprint_resolver.resolve_template("{{ name | upper }}", context)
        assert result == "TEST_DEVICE"

    def test_resolve_template_undefined_variable(self, blueprint_resolver):
        """Test that resolving template with undefined variable raises error."""
        context = {"env": "prod"}
        with pytest.raises(BlueprintError, match="Undefined variable"):
            blueprint_resolver.resolve_template("{{ undefined_var }}", context)

    def test_resolve_template_syntax_error(self, blueprint_resolver):
        """Test that template with syntax error raises error."""
        context = {}
        with pytest.raises(BlueprintError, match="Template syntax error"):
            blueprint_resolver.resolve_template("{{ unclosed", context)

    def test_evaluate_condition_true(self, blueprint_resolver):
        """Test evaluating condition that returns true."""
        context = {"env": "prod"}
        result = blueprint_resolver.evaluate_condition("{{ env == 'prod' }}", context)
        assert result is True

    def test_evaluate_condition_false(self, blueprint_resolver):
        """Test evaluating condition that returns false."""
        context = {"env": "dev"}
        result = blueprint_resolver.evaluate_condition("{{ env == 'prod' }}", context)
        assert result is False

    def test_evaluate_condition_string_true(self, blueprint_resolver):
        """Test evaluating condition with string 'true'."""
        context = {}
        result = blueprint_resolver.evaluate_condition("true", context)
        assert result is True

    def test_evaluate_condition_string_yes(self, blueprint_resolver):
        """Test evaluating condition with string 'yes'."""
        context = {}
        result = blueprint_resolver.evaluate_condition("yes", context)
        assert result is True

    def test_evaluate_condition_string_false(self, blueprint_resolver):
        """Test evaluating condition with string 'false'."""
        context = {}
        result = blueprint_resolver.evaluate_condition("false", context)
        assert result is False

    def test_evaluate_condition_complex_expression(self, blueprint_resolver):
        """Test evaluating complex boolean expression."""
        context = {"env": "prod", "region": "us-east", "count": 5}
        result = blueprint_resolver.evaluate_condition(
            "{{ env == 'prod' and region == 'us-east' and count > 3 }}", 
            context
        )
        assert result is True

    def test_evaluate_condition_with_default_filter(self, blueprint_resolver):
        """Test evaluating condition with default filter for missing variable."""
        context = {}
        result = blueprint_resolver.evaluate_condition("{{ missing_var | default(false) }}", context)
        assert result is False

    def test_evaluate_condition_undefined_variable(self, blueprint_resolver):
        """Test that condition with undefined variable raises error."""
        context = {}
        with pytest.raises(BlueprintError, match="Undefined variable"):
            blueprint_resolver.evaluate_condition("{{ undefined_var }}", context)

    def test_build_context_with_missing_defaults_file(self, blueprint_resolver, tmp_path, mock_workflow_roots):
        """Test building context when defaults.yaml doesn't exist."""
        empty_vars_dir = tmp_path / "empty_vars"
        empty_vars_dir.mkdir()
        
        context = blueprint_resolver.build_context(
            vars_dir=empty_vars_dir,
            workflow_path=None,
            workflow_roots=mock_workflow_roots,
            inline_workflow_vars=None,
            cli_vars={"test": "value"},
        )
        
        assert context["test"] == "value"

    def test_build_context_with_missing_domain_defaults(self, blueprint_resolver, mock_vars_dir, mock_workflow_roots, tmp_path):
        """Test building context when domain defaults don't exist."""
        workflow_path = Path(mock_workflow_roots[0]) / "missing_domain" / "deploy.yaml"
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        workflow_path.touch()
        
        context = blueprint_resolver.build_context(
            vars_dir=mock_vars_dir,
            workflow_path=workflow_path,
            workflow_roots=mock_workflow_roots,
            inline_workflow_vars=None,
            cli_vars=None,
        )
        
        assert isinstance(context, dict)

    def test_resolve_template_no_template_markers(self, blueprint_resolver):
        """Test resolving plain string without template markers."""
        context = {"env": "prod"}
        result = blueprint_resolver.resolve_template("plain_string", context)
        assert result == "plain_string"

    def test_evaluate_condition_numeric_comparison(self, blueprint_resolver):
        """Test evaluating condition with numeric comparison."""
        context = {"count": 10}
        result = blueprint_resolver.evaluate_condition("{{ count > 5 }}", context)
        assert result is True
        
        result = blueprint_resolver.evaluate_condition("{{ count < 5 }}", context)
        assert result is False