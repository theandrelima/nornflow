import pytest
from nornflow.blueprints.expander import BlueprintExpander
from nornflow.exceptions import BlueprintCircularDependencyError, BlueprintError, ResourceError


class TestBlueprintExpander:
    """Tests for BlueprintExpander class."""

    def test_expand_blueprints_no_catalog(self, blueprint_resolver):
        """Test expansion with no blueprints catalog."""
        expander = BlueprintExpander(blueprint_resolver)
        tasks = [{"name": "task1", "task": "echo"}]
        result = expander.expand_blueprints(
            tasks=tasks,
            blueprints_catalog=None,
            vars_dir=None,
            workflow_path=None,
            workflow_roots=None,
            inline_vars=None,
        )
        assert result == tasks

    def test_expand_blueprints_simple_blueprint(self, blueprint_resolver, mock_blueprints_catalog, mock_vars_dir, mock_workflow_path, mock_workflow_roots, mock_cli_vars):
        """Test expanding a simple blueprint reference."""
        expander = BlueprintExpander(blueprint_resolver)
        tasks = [{"blueprint": "sample"}]
        result = expander.expand_blueprints(
            tasks=tasks,
            blueprints_catalog=mock_blueprints_catalog,
            vars_dir=mock_vars_dir,
            workflow_path=mock_workflow_path,
            workflow_roots=mock_workflow_roots,
            inline_vars=None,
            cli_vars=mock_cli_vars,
        )
        assert len(result) == 1
        assert result[0]["name"] == "sample_task"

    def test_expand_blueprints_with_condition_true(self, blueprint_resolver, mock_blueprints_catalog, mock_vars_dir, mock_workflow_path, mock_workflow_roots):
        """Test blueprint expansion with a true condition."""
        expander = BlueprintExpander(blueprint_resolver)
        tasks = [{"blueprint": "sample", "if": "true"}]
        result = expander.expand_blueprints(
            tasks=tasks,
            blueprints_catalog=mock_blueprints_catalog,
            vars_dir=mock_vars_dir,
            workflow_path=mock_workflow_path,
            workflow_roots=mock_workflow_roots,
            inline_vars=None,
        )
        assert len(result) == 1

    def test_expand_blueprints_with_condition_false(self, blueprint_resolver, mock_blueprints_catalog, mock_vars_dir, mock_workflow_path, mock_workflow_roots):
        """Test blueprint expansion with a false condition."""
        expander = BlueprintExpander(blueprint_resolver)
        tasks = [{"blueprint": "sample", "if": "false"}]
        result = expander.expand_blueprints(
            tasks=tasks,
            blueprints_catalog=mock_blueprints_catalog,
            vars_dir=mock_vars_dir,
            workflow_path=mock_workflow_path,
            workflow_roots=mock_workflow_roots,
            inline_vars=None,
        )
        assert result == []

    def test_expand_blueprints_nested_blueprint(self, blueprint_resolver, tmp_path, mock_vars_dir, mock_workflow_path, mock_workflow_roots):
        """Test expanding nested blueprints."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        parent_blueprint = blueprint_dir / "parent.yaml"
        parent_blueprint.write_text("""
tasks:
  - blueprint: child
""")
        child_blueprint = blueprint_dir / "child.yaml"
        child_blueprint.write_text("""
tasks:
  - name: child_task
    task: echo
""")
        catalog = {"parent": parent_blueprint, "child": child_blueprint}

        expander = BlueprintExpander(blueprint_resolver)
        tasks = [{"blueprint": "parent"}]
        result = expander.expand_blueprints(
            tasks=tasks,
            blueprints_catalog=catalog,
            vars_dir=mock_vars_dir,
            workflow_path=mock_workflow_path,
            workflow_roots=mock_workflow_roots,
            inline_vars=None,
        )
        assert len(result) == 1
        assert result[0]["name"] == "child_task"

    def test_expand_blueprints_circular_dependency(self, blueprint_resolver, tmp_path, mock_vars_dir, mock_workflow_path, mock_workflow_roots):
        """Test detection of circular blueprint dependencies."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        blueprint_a = blueprint_dir / "a.yaml"
        blueprint_a.write_text("""
tasks:
  - blueprint: b
""")
        blueprint_b = blueprint_dir / "b.yaml"
        blueprint_b.write_text("""
tasks:
  - blueprint: a
""")
        catalog = {"a": blueprint_a, "b": blueprint_b}

        expander = BlueprintExpander(blueprint_resolver)
        tasks = [{"blueprint": "a"}]
        with pytest.raises(BlueprintCircularDependencyError):
            expander.expand_blueprints(
                tasks=tasks,
                blueprints_catalog=catalog,
                vars_dir=mock_vars_dir,
                workflow_path=mock_workflow_path,
                workflow_roots=mock_workflow_roots,
                inline_vars=None,
            )

    def test_expand_blueprints_missing_blueprint(self, blueprint_resolver, mock_vars_dir, mock_workflow_path, mock_workflow_roots, tmp_path, monkeypatch):
        """Test error when blueprint is missing."""
        monkeypatch.chdir(tmp_path)
        
        expander = BlueprintExpander(blueprint_resolver)
        tasks = [{"blueprint": "this_blueprint_absolutely_does_not_exist_anywhere_xyz123"}]
        with pytest.raises(BlueprintError, match="Blueprint not found in catalog or filesystem"):
            expander.expand_blueprints(
                tasks=tasks,
                blueprints_catalog={},
                vars_dir=mock_vars_dir,
                workflow_path=mock_workflow_path,
                workflow_roots=mock_workflow_roots,
                inline_vars=None,
            )

    def test_expand_blueprints_invalid_yaml(self, blueprint_resolver, tmp_path, mock_vars_dir, mock_workflow_path, mock_workflow_roots):
        """Test error with invalid YAML in blueprint."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        invalid_blueprint = blueprint_dir / "invalid.yaml"
        invalid_blueprint.write_text("invalid: yaml: content: [")
        catalog = {"invalid": invalid_blueprint}

        expander = BlueprintExpander(blueprint_resolver)
        tasks = [{"blueprint": "invalid"}]
        with pytest.raises(ResourceError, match="Failed to hash file content"):
            expander.expand_blueprints(
                tasks=tasks,
                blueprints_catalog=catalog,
                vars_dir=mock_vars_dir,
                workflow_path=mock_workflow_path,
                workflow_roots=mock_workflow_roots,
                inline_vars=None,
            )

    def test_expand_blueprints_invalid_structure(self, blueprint_resolver, tmp_path, mock_vars_dir, mock_workflow_path, mock_workflow_roots):
        """Test error with invalid blueprint structure."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        invalid_blueprint = blueprint_dir / "invalid.yaml"
        invalid_blueprint.write_text("not_tasks: []")
        catalog = {"invalid": invalid_blueprint}

        expander = BlueprintExpander(blueprint_resolver)
        tasks = [{"blueprint": "invalid"}]
        with pytest.raises(BlueprintError, match="Blueprint must contain ONLY 'tasks' key"):
            expander.expand_blueprints(
                tasks=tasks,
                blueprints_catalog=catalog,
                vars_dir=mock_vars_dir,
                workflow_path=mock_workflow_path,
                workflow_roots=mock_workflow_roots,
                inline_vars=None,
            )

    def test_expand_blueprints_tasks_not_list(self, blueprint_resolver, tmp_path, mock_vars_dir, mock_workflow_path, mock_workflow_roots):
        """Test error when tasks is not a list."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        invalid_blueprint = blueprint_dir / "invalid.yaml"
        invalid_blueprint.write_text("tasks: not_a_list")
        catalog = {"invalid": invalid_blueprint}

        expander = BlueprintExpander(blueprint_resolver)
        tasks = [{"blueprint": "invalid"}]
        with pytest.raises(BlueprintError, match="'tasks' must be a list"):
            expander.expand_blueprints(
                tasks=tasks,
                blueprints_catalog=catalog,
                vars_dir=mock_vars_dir,
                workflow_path=mock_workflow_path,
                workflow_roots=mock_workflow_roots,
                inline_vars=None,
            )