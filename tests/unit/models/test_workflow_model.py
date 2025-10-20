"""Tests for WorkflowModel."""

import pytest

from nornflow.constants import FailureStrategy
from nornflow.exceptions import WorkflowError
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
                "tasks": [{"name": "dummy_task"}],  # Add required tasks
                "inventory_filters": {"key": ["list", "of", "items"]}
            }
        })
        # Lists are converted to tuples for hashability
        assert workflow.inventory_filters["key"] == ("list", "of", "items")

    def test_validate_processors(self):
        """Test processors validation."""
        workflow = WorkflowModel.create({
            "workflow": {
                "name": "test",
                "tasks": [{"name": "dummy_task"}],  # Add required tasks
                "processors": [{"class": "MyProcessor", "args": {}}]  # Only 1 processor allowed
            }
        })
        assert len(workflow.processors) == 1
        assert isinstance(workflow.processors, tuple)

    def test_validate_vars(self):
        """Test vars validation."""
        workflow = WorkflowModel.create({
            "workflow": {
                "name": "test",
                "tasks": [{"name": "dummy_task"}],  # Add required tasks
                "vars": {"key": ["list", "values"]}
            }
        })
        # Lists are converted to tuples for hashability
        assert workflow.vars["key"] == ("list", "values")

    def test_empty_optional_fields(self):
        """Test workflow with minimal required fields."""
        workflow_dict = {
            "workflow": {
                "name": "minimal",
                "tasks": [{"name": "dummy_task"}]  # Add required tasks
            }
        }
        workflow = WorkflowModel.create(workflow_dict)
        assert workflow.name == "minimal"
        assert len(workflow.tasks) == 1
        assert workflow.inventory_filters is None
        assert workflow.processors is None
        assert workflow.vars is None

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
                    {"class": "Processor1"}  # Only 1 processor allowed
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
        assert len(workflow.processors) == 1  # Only 1 processor allowed
        assert workflow.vars["var1"] == "value1"
        assert workflow.vars["var2"] == ("a", "b", "c")
        assert workflow.failure_strategy == FailureStrategy.FAIL_FAST