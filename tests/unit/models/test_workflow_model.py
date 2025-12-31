"""Tests for WorkflowModel."""

import pytest

from nornflow.constants import FailureStrategy
from nornflow.exceptions import BlueprintCircularDependencyError, BlueprintError, WorkflowError
from nornflow.models import WorkflowModel


class TestWorkflowModel:
    def test_create_success(self):
        """Test successful workflow creation."""
        workflow_dict = {
            "workflow": {
                "name": "test_workflow",
                "description": "Test",
                "tasks": [{"name": "task1"}]
            }
        }
        workflow = WorkflowModel.create(workflow_dict)
        assert workflow.name == "test_workflow"
        assert len(workflow.tasks) == 1

    def test_create_missing_workflow_key(self):
        """Test error when workflow key missing."""
        with pytest.raises(WorkflowError, match="'workflow' as a root-level key"):
            WorkflowModel.create({})

    def test_validate_failure_strategy(self):
        """Test failure strategy validation."""
        assert WorkflowModel.validate_failure_strategy("skip_failed") == FailureStrategy.SKIP_FAILED
        assert WorkflowModel.validate_failure_strategy("skip-failed") == FailureStrategy.SKIP_FAILED
        with pytest.raises(WorkflowError):
            WorkflowModel.validate_failure_strategy("invalid")

    def test_validate_inventory_filters(self):
        """Test inventory filters validation."""
        workflow = WorkflowModel.create({
            "workflow": {
                "name": "test",
                "tasks": [{"name": "dummy_task"}],
                "inventory_filters": {"key": ["list", "of", "items"]}
            }
        })
        assert workflow.inventory_filters["key"] == ("list", "of", "items")

    def test_validate_processors(self):
        """Test processors validation."""
        workflow = WorkflowModel.create({
            "workflow": {
                "name": "test",
                "tasks": [{"name": "dummy_task"}],
                "processors": [{"class": "MyProcessor", "args": {}}]
            }
        })
        assert len(workflow.processors) == 1
        assert isinstance(workflow.processors, tuple)

    def test_validate_vars(self):
        """Test vars validation."""
        workflow = WorkflowModel.create({
            "workflow": {
                "name": "test",
                "tasks": [{"name": "dummy_task"}],
                "vars": {"key": ["list", "values"]}
            }
        })
        assert workflow.vars["key"] == ("list", "values")

    def test_empty_optional_fields(self):
        """Test workflow with minimal required fields."""
        workflow_dict = {
            "workflow": {
                "name": "minimal",
                "tasks": [{"name": "dummy_task"}]
            }
        }
        workflow = WorkflowModel.create(workflow_dict)
        assert workflow.name == "minimal"
        assert len(workflow.tasks) == 1
        assert not workflow.inventory_filters
        assert not workflow.processors
        assert not workflow.vars

    def test_with_all_fields(self):
        """Test workflow with all fields specified."""
        workflow_dict = {
            "workflow": {
                "name": "complete",
                "description": "A complete workflow",
                "tasks": [
                    {"name": "task1", "args": {"arg1": "value1"}},
                    {"name": "task2"}
                ],
                "inventory_filters": {
                    "platform": "ios",
                    "groups": ["core", "edge"]
                },
                "processors": [
                    {"class": "Processor1"}
                ],
                "vars": {
                    "var1": "value1",
                    "var2": ["a", "b", "c"]
                },
                "failure_strategy": "fail-fast"
            }
        }
        workflow = WorkflowModel.create(workflow_dict)
        
        assert workflow.name == "complete"
        assert workflow.description == "A complete workflow"
        assert len(workflow.tasks) == 2
        assert workflow.inventory_filters["platform"] == "ios"
        assert workflow.inventory_filters["groups"] == ("core", "edge")
        assert len(workflow.processors) == 1
        assert workflow.vars["var1"] == "value1"
        assert workflow.vars["var2"] == ("a", "b", "c")
        assert workflow.failure_strategy == FailureStrategy.FAIL_FAST


class TestWorkflowModelBlueprintExpansion:
    """Tests for blueprint expansion in WorkflowModel.create()."""

    def test_create_without_blueprints(self):
        """Test workflow creation without any blueprint references."""
        workflow_dict = {
            "workflow": {
                "name": "no_blueprints",
                "tasks": [{"name": "task1"}]
            }
        }
        workflow = WorkflowModel.create(workflow_dict)
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].name == "task1"

    def test_create_with_simple_blueprint(self, tmp_path):
        """Test workflow with a simple blueprint reference."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        blueprint_file = blueprint_dir / "simple.yaml"
        blueprint_file.write_text("""tasks:
  - name: blueprint_task
    args:
      message: "from blueprint"
""")
        
        blueprints_catalog = {"simple": blueprint_file}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "with_blueprint",
                "tasks": [{"blueprint": "simple"}]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=None,
            workflow_roots=[str(tmp_path)]
        )
        
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].name == "blueprint_task"

    def test_create_with_multiple_blueprints(self, tmp_path):
        """Test workflow with multiple blueprint references."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        bp1 = blueprint_dir / "bp1.yaml"
        bp1.write_text("""tasks:
  - name: task1
    args:
      key: value1
""")
        
        bp2 = blueprint_dir / "bp2.yaml"
        bp2.write_text("""tasks:
  - name: task2
    args:
      key: value2
""")
        
        blueprints_catalog = {"bp1": bp1, "bp2": bp2}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "multi_blueprint",
                "tasks": [
                    {"blueprint": "bp1"},
                    {"blueprint": "bp2"}
                ]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=None,
            workflow_roots=[str(tmp_path)]
        )
        
        assert len(workflow.tasks) == 2
        assert workflow.tasks[0].name == "task1"
        assert workflow.tasks[1].name == "task2"

    def test_create_mixed_blueprints_and_tasks(self, tmp_path):
        """Test workflow with both blueprint references and direct tasks."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        blueprint_file = blueprint_dir / "mixed.yaml"
        blueprint_file.write_text("""tasks:
  - name: blueprint_task
    args:
      from: blueprint
""")
        
        blueprints_catalog = {"mixed": blueprint_file}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "mixed_workflow",
                "tasks": [
                    {"name": "direct_task1", "args": {"from": "direct"}},
                    {"blueprint": "mixed"},
                    {"name": "direct_task2", "args": {"from": "direct"}}
                ]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=None,
            workflow_roots=[str(tmp_path)]
        )
        
        assert len(workflow.tasks) == 3
        assert workflow.tasks[0].name == "direct_task1"
        assert workflow.tasks[1].name == "blueprint_task"
        assert workflow.tasks[2].name == "direct_task2"

    def test_create_with_nested_blueprints(self, tmp_path):
        """Test workflow with nested blueprint references."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        parent = blueprint_dir / "parent.yaml"
        parent.write_text("""tasks:
  - name: parent_task
    args:
      level: parent
  - blueprint: child
""")
        
        child = blueprint_dir / "child.yaml"
        child.write_text("""tasks:
  - name: child_task
    args:
      level: child
""")
        
        blueprints_catalog = {"parent": parent, "child": child}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "nested",
                "tasks": [{"blueprint": "parent"}]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=None,
            workflow_roots=[str(tmp_path)]
        )
        
        assert len(workflow.tasks) == 2
        assert workflow.tasks[0].name == "parent_task"
        assert workflow.tasks[1].name == "child_task"

    def test_create_blueprint_with_true_condition(self, tmp_path):
        """Test blueprint with 'if' condition that evaluates to true."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        blueprint_file = blueprint_dir / "conditional.yaml"
        blueprint_file.write_text("""tasks:
  - name: conditional_task
    args:
      condition: included
""")
        
        blueprints_catalog = {"conditional": blueprint_file}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "conditional_workflow",
                "tasks": [{"blueprint": "conditional", "if": "true"}]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=None,
            workflow_roots=[str(tmp_path)]
        )
        
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].name == "conditional_task"

    def test_create_blueprint_with_false_condition(self, tmp_path):
        """Test blueprint with 'if' condition that evaluates to false."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        blueprint_file = blueprint_dir / "conditional.yaml"
        blueprint_file.write_text("""tasks:
  - name: conditional_task
    args:
      condition: excluded
""")
        
        blueprints_catalog = {"conditional": blueprint_file}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "conditional_workflow",
                "tasks": [{"blueprint": "conditional", "if": "false"}]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=None,
            workflow_roots=[str(tmp_path)]
        )
        
        assert len(workflow.tasks) == 0

    def test_create_blueprint_with_jinja_condition(self, tmp_path):
        """Test blueprint with Jinja2 expression condition."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        blueprint_file = blueprint_dir / "jinja_cond.yaml"
        blueprint_file.write_text("""tasks:
  - name: jinja_task
    args:
      type: conditional
""")
        
        blueprints_catalog = {"jinja_cond": blueprint_file}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "jinja_condition",
                "vars": {"include_task": True},
                "tasks": [{"blueprint": "jinja_cond", "if": "{{ include_task }}"}]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=None,
            workflow_roots=[str(tmp_path)]
        )
        
        assert len(workflow.tasks) == 1

    def test_create_blueprint_with_cli_vars(self, tmp_path):
        """Test blueprint expansion with CLI variables."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        blueprint_file = blueprint_dir / "cli_aware.yaml"
        blueprint_file.write_text("""tasks:
  - name: cli_task
    args:
      source: cli_vars
""")
        
        blueprints_catalog = {"cli_aware": blueprint_file}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "cli_vars_test",
                "tasks": [{"blueprint": "{{ bp_from_cli }}", "if": "{{ enable_blueprint }}"}]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=None,
            workflow_roots=[str(tmp_path)],
            cli_vars={"bp_from_cli": "cli_aware", "enable_blueprint": True}
        )
        
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].name == "cli_task"

    def test_create_circular_blueprint_dependency(self, tmp_path):
        """Test error when blueprints have circular dependency."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        bp_a = blueprint_dir / "a.yaml"
        bp_a.write_text("""tasks:
  - blueprint: b
""")
        
        bp_b = blueprint_dir / "b.yaml"
        bp_b.write_text("""tasks:
  - blueprint: a
""")
        
        blueprints_catalog = {"a": bp_a, "b": bp_b}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "circular",
                "tasks": [{"blueprint": "a"}]
            }
        }
        
        with pytest.raises(BlueprintCircularDependencyError):
            WorkflowModel.create(
                workflow_dict,
                blueprints_catalog=blueprints_catalog,
                vars_dir=vars_dir,
                workflow_path=None,
                workflow_roots=[str(tmp_path)]
            )

    def test_create_missing_blueprint(self, tmp_path):
        """Test error when blueprint reference cannot be found."""
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "missing_bp",
                "tasks": [{"blueprint": "nonexistent"}]
            }
        }
        
        with pytest.raises(BlueprintError, match="Blueprint not found in catalog or filesystem"):
            WorkflowModel.create(
                workflow_dict,
                blueprints_catalog={},
                vars_dir=vars_dir,
                workflow_path=None,
                workflow_roots=[str(tmp_path)]
            )

    def test_create_invalid_blueprint_structure(self, tmp_path):
        """Test error when blueprint has invalid structure."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        invalid_bp = blueprint_dir / "invalid.yaml"
        invalid_bp.write_text("""workflow:
  name: "not a blueprint"
""")
        
        blueprints_catalog = {"invalid": invalid_bp}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "invalid_structure",
                "tasks": [{"blueprint": "invalid"}]
            }
        }
        
        with pytest.raises(BlueprintError, match="Blueprint must contain ONLY 'tasks' key"):
            WorkflowModel.create(
                workflow_dict,
                blueprints_catalog=blueprints_catalog,
                vars_dir=vars_dir,
                workflow_path=None,
                workflow_roots=[str(tmp_path)]
            )

    def test_create_blueprint_tasks_not_list(self, tmp_path):
        """Test error when blueprint tasks is not a list."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        invalid_bp = blueprint_dir / "not_list.yaml"
        invalid_bp.write_text("""tasks: "should be a list"
""")
        
        blueprints_catalog = {"not_list": invalid_bp}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "tasks_not_list",
                "tasks": [{"blueprint": "not_list"}]
            }
        }
        
        with pytest.raises(BlueprintError, match="'tasks' must be a list"):
            WorkflowModel.create(
                workflow_dict,
                blueprints_catalog=blueprints_catalog,
                vars_dir=vars_dir,
                workflow_path=None,
                workflow_roots=[str(tmp_path)]
            )

    def test_create_blueprint_with_variable_resolution(self, tmp_path):
        """Test blueprint name using variable resolution."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        blueprint_file = blueprint_dir / "dynamic.yaml"
        blueprint_file.write_text("""tasks:
  - name: dynamic_task
    args:
      resolved: "{{ my_var }}"
""")
        
        blueprints_catalog = {"dynamic": blueprint_file}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "variable_resolution",
                "vars": {"bp_name": "dynamic", "my_var": "test_value"},
                "tasks": [{"blueprint": "{{ bp_name }}"}]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=None,
            workflow_roots=[str(tmp_path)]
        )
        
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].name == "dynamic_task"

    def test_create_blueprint_with_env_vars(self, tmp_path, monkeypatch):
        """Test blueprint expansion with environment variables."""
        monkeypatch.setenv("NORNFLOW_VAR_ENABLE_FEATURE", "true")
        
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        blueprint_file = blueprint_dir / "env_aware.yaml"
        blueprint_file.write_text("""tasks:
  - name: env_task
    args:
      env_based: true
""")
        
        blueprints_catalog = {"env_aware": blueprint_file}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "env_vars_test",
                "tasks": [{"blueprint": "env_aware", "if": "{{ ENABLE_FEATURE }}"}]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=None,
            workflow_roots=[str(tmp_path)]
        )
        
        assert len(workflow.tasks) == 1

    def test_create_blueprint_with_domain_defaults(self, tmp_path):
        """Test blueprint expansion with domain-specific defaults."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        blueprint_file = blueprint_dir / "domain_aware.yaml"
        blueprint_file.write_text("""tasks:
  - name: domain_task
    args:
      domain_based: true
""")
        
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        domain_dir = vars_dir / "networking"
        domain_dir.mkdir()
        
        defaults_file = domain_dir / "defaults.yaml"
        defaults_file.write_text("include_domain_task: true\n")
        
        workflow_dir = tmp_path / "workflows" / "networking"
        workflow_dir.mkdir(parents=True)
        workflow_path = workflow_dir / "test.yaml"
        
        blueprints_catalog = {"domain_aware": blueprint_file}
        
        workflow_dict = {
            "workflow": {
                "name": "domain_defaults_test",
                "tasks": [{"blueprint": "domain_aware", "if": "{{ include_domain_task }}"}]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=workflow_path,
            workflow_roots=[str(tmp_path / "workflows")]
        )
        
        assert len(workflow.tasks) == 1

    def test_create_deeply_nested_blueprints(self, tmp_path):
        """Test workflow with deeply nested blueprint hierarchy."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        level1 = blueprint_dir / "level1.yaml"
        level1.write_text("""tasks:
  - name: task_level1
    args:
      level: 1
  - blueprint: level2
""")
        
        level2 = blueprint_dir / "level2.yaml"
        level2.write_text("""tasks:
  - name: task_level2
    args:
      level: 2
  - blueprint: level3
""")
        
        level3 = blueprint_dir / "level3.yaml"
        level3.write_text("""tasks:
  - name: task_level3
    args:
      level: 3
""")
        
        blueprints_catalog = {"level1": level1, "level2": level2, "level3": level3}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "deeply_nested",
                "tasks": [{"blueprint": "level1"}]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=None,
            workflow_roots=[str(tmp_path)]
        )
        
        assert len(workflow.tasks) == 3
        assert workflow.tasks[0].name == "task_level1"
        assert workflow.tasks[1].name == "task_level2"
        assert workflow.tasks[2].name == "task_level3"

    def test_create_multiple_conditional_blueprints(self, tmp_path):
        """Test workflow with multiple conditional blueprint references."""
        blueprint_dir = tmp_path / "blueprints"
        blueprint_dir.mkdir()
        
        bp1 = blueprint_dir / "conditional1.yaml"
        bp1.write_text("""tasks:
  - name: conditional_task1
    args:
      enabled: true
""")
        
        bp2 = blueprint_dir / "conditional2.yaml"
        bp2.write_text("""tasks:
  - name: conditional_task2
    args:
      enabled: false
""")
        
        blueprints_catalog = {"conditional1": bp1, "conditional2": bp2}
        vars_dir = tmp_path / "vars"
        vars_dir.mkdir()
        
        workflow_dict = {
            "workflow": {
                "name": "multiple_conditionals",
                "vars": {"feature1": True, "feature2": False},
                "tasks": [
                    {"blueprint": "conditional1", "if": "{{ feature1 }}"},
                    {"blueprint": "conditional2", "if": "{{ feature2 }}"}
                ]
            }
        }
        
        workflow = WorkflowModel.create(
            workflow_dict,
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=None,
            workflow_roots=[str(tmp_path)]
        )
        
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].name == "conditional_task1"