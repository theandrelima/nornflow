from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from nornflow.cli.run import (
    get_nornflow_builder,
    parse_inventory_filters,
    parse_key_value_pairs,
    parse_processors,
    parse_task_args,
    run,
)
from tests.unit.test_processors_utils import TestProcessor, TestProcessor2


class TestCLIArgumentParsing:
    """Test CLI argument and key-value pair parsing."""

    def test_parse_key_value_pairs_empty(self):
        """Test parsing empty key-value pairs."""
        result = parse_key_value_pairs(None, "test")
        assert result == {}

        result = parse_key_value_pairs("", "test")
        assert result == {}

    def test_parse_key_value_pairs_simple(self):
        """Test parsing simple key-value pairs."""
        result = parse_key_value_pairs("key1=value1, key2=value2", "test")
        assert result == {"key1": "value1", "key2": "value2"}

    def test_parse_key_value_pairs_complex(self):
        """Test parsing complex key-value pairs with various data types."""
        kv_str = "key1='string value', key2=123, key3=True, key4=[1,2,3]"
        result = parse_key_value_pairs(kv_str, "test")
        assert result == {"key1": "string value", "key2": 123, "key3": True, "key4": [1, 2, 3]}

    def test_parse_task_args(self):
        """Test parsing task arguments."""
        args_str = "arg1='value1', arg2=[1,2,3], arg3={'key': 'value'}"
        result = parse_task_args(args_str)
        assert result == {"arg1": "value1", "arg2": [1, 2, 3], "arg3": {"key": "value"}}

    def test_parse_inventory_filters(self):
        """Test parsing inventory filters."""
        filters_str = "platform='ios', vendor='cisco', hosts=['host1', 'host2']"
        result = parse_inventory_filters(filters_str)
        assert result == {"platform": "ios", "vendor": "cisco", "hosts": ["host1", "host2"]}


class TestCLIProcessorParsing:
    """Test CLI processor string parsing functionality."""

    def test_parse_processors_single(self):
        """Test parsing a single processor from CLI string."""
        processor_str = "class='tests.unit.test_processors_utils.TestProcessor',args={'name':'CLIProcessor','verbose':True}"
        result = parse_processors(processor_str)

        assert len(result) == 1
        assert result[0]["class"] == "tests.unit.test_processors_utils.TestProcessor"
        assert result[0]["args"] == {"name": "CLIProcessor", "verbose": True}

    def test_parse_processors_multiple(self):
        """Test parsing multiple processors from CLI string."""
        processor_str = "class='tests.unit.test_processors_utils.TestProcessor',args={'name':'Proc1'};class='tests.unit.test_processors_utils.TestProcessor2',args={'name':'Proc2'}"
        result = parse_processors(processor_str)

        assert len(result) == 2
        assert result[0]["class"] == "tests.unit.test_processors_utils.TestProcessor"
        assert result[0]["args"] == {"name": "Proc1"}
        assert result[1]["class"] == "tests.unit.test_processors_utils.TestProcessor2"
        assert result[1]["args"] == {"name": "Proc2"}

    def test_parse_processors_no_args(self):
        """Test parsing a processor with no args specified."""
        processor_str = "class='tests.unit.test_processors_utils.TestProcessor'"
        result = parse_processors(processor_str)

        assert len(result) == 1
        assert result[0]["class"] == "tests.unit.test_processors_utils.TestProcessor"
        assert result[0]["args"] == {}

    def test_parse_processors_empty(self):
        """Test parsing an empty processor string."""
        result = parse_processors(None)
        assert result == []

        result = parse_processors("")
        assert result == []

    def test_parse_processors_invalid_format(self):
        """Test parsing a processor string with invalid format."""
        processor_str = "invalid_format"
        with pytest.raises(typer.BadParameter):
            parse_processors(processor_str)


class TestNornflowBuilderIntegration:
    """Test integration of CLI arguments with NornFlowBuilder."""

    @patch("nornflow.cli.run.NornFlowBuilder")
    def test_get_nornflow_builder_task(self, mock_builder):
        """Test building a NornFlow object for a task execution."""
        mock_instance = MagicMock()
        mock_builder.return_value = mock_instance

        from nornflow.cli.run import get_nornflow_builder

        get_nornflow_builder(
            target="my_task",
            args={"arg1": "value1"},
            inventory_filters={"platform": "ios"},
            settings_file="settings.yaml",
        )

        # Assert that with_settings_path was called with the correct settings file
        mock_instance.with_settings_path.assert_called_once_with("settings.yaml")

        # Assert that with_workflow_dict was called
        mock_instance.with_workflow_dict.assert_called()
        workflow_dict = mock_instance.with_workflow_dict.call_args[0][0]
        assert workflow_dict["workflow"]["tasks"][0]["name"] == "my_task"
        assert workflow_dict["workflow"]["tasks"][0]["args"] == {"arg1": "value1"}

        # Assert that with_cli_filters was called with the correct filters
        mock_instance.with_cli_filters.assert_called_once_with({"platform": "ios"})

    @patch("nornflow.cli.run.NornFlowBuilder")
    @patch("nornflow.cli.run.WorkflowFactory")
    def test_get_nornflow_builder_workflow_path(self, mock_factory, mock_builder):
        """Test building a NornFlow object for a workflow specified by path."""
        mock_instance = MagicMock()
        mock_builder.return_value = mock_instance

        # Create a mock workflow object
        mock_workflow = MagicMock()
        mock_factory.create_from_file.return_value = mock_workflow

        from nornflow.cli.run import get_nornflow_builder

        # Create a dummy workflow file with valid content
        workflow_file = "my_workflow.yaml"
        Path(workflow_file).write_text("workflow:\n  name: Test Workflow\n  tasks:\n    - name: test_task")

        try:
            get_nornflow_builder(
                target=workflow_file,
                args={},
                inventory_filters={"platform": "ios"},
                settings_file="",
            )

            # Assert factory was called with the correct path
            mock_factory.create_from_file.assert_called_once()

            # Assert that with_workflow_object was called with the mock workflow
            mock_instance.with_workflow_object.assert_called_with(mock_workflow)

        finally:
            # Clean up the dummy workflow file
            Path(workflow_file).unlink()

    @patch("nornflow.cli.run.NornFlowBuilder")
    @patch("nornflow.cli.run.Path")
    def test_get_nornflow_builder_workflow_name(self, mock_path, mock_builder):
        """Test building a NornFlow object for a workflow specified by name."""
        mock_instance = MagicMock()
        mock_builder.return_value = mock_instance
        mock_instance.with_workflow_name.return_value = mock_instance

        # Setup mock path instance
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.exists.return_value = False

        from nornflow.cli.run import get_nornflow_builder

        get_nornflow_builder(
            target="my_workflow.yaml",
            args={},
            inventory_filters={"platform": "ios"},
            settings_file="",
        )

        # Assert that with_workflow_name was called with the target
        mock_instance.with_workflow_name.assert_called_with("my_workflow.yaml")

    @patch("nornflow.cli.run.NornFlowBuilder")
    def test_get_nornflow_builder_dry_run(self, mock_builder):
        """Test building a NornFlow object with dry_run enabled."""
        mock_instance = MagicMock()
        mock_builder.return_value = mock_instance

        from nornflow.cli.run import get_nornflow_builder

        get_nornflow_builder(
            target="my_task",
            args={},
            inventory_filters={},
            settings_file="",
        )

        # Assert builder was created (dry_run no longer affects construction)
        mock_builder.assert_called_once()

    @patch("nornflow.cli.run.NornFlowBuilder")
    def test_get_nornflow_builder_no_dry_run(self, mock_builder):
        """Test building a NornFlow object with dry_run disabled."""
        mock_instance = MagicMock()
        mock_builder.return_value = mock_instance

        from nornflow.cli.run import get_nornflow_builder

        get_nornflow_builder(
            target="my_task",
            args={},
            inventory_filters={},
            settings_file="",
        )

        # Assert builder was created (dry_run no longer affects construction)
        mock_builder.assert_called_once()

    @patch("nornflow.cli.run.NornFlowBuilder")
    def test_get_nornflow_builder_settings_file(self, mock_builder):
        """Test building a NornFlow object with a settings file."""
        mock_instance = MagicMock()
        mock_builder.return_value = mock_instance

        from nornflow.cli.run import get_nornflow_builder

        get_nornflow_builder(
            target="my_task",
            args={},
            inventory_filters={},
            settings_file="my_settings.yaml",
        )

        # Assert that with_settings_path was called with the correct settings file
        mock_instance.with_settings_path.assert_called_once_with("my_settings.yaml")

    @patch("nornflow.cli.run.NornFlowBuilder")
    def test_get_nornflow_builder_no_settings_file(self, mock_builder):
        """Test building a NornFlow object without a settings file."""
        mock_instance = MagicMock()
        mock_builder.return_value = mock_instance

        from nornflow.cli.run import get_nornflow_builder

        get_nornflow_builder(
            target="my_task",
            args={},
            inventory_filters={},
            settings_file="",
        )

        # Assert that with_settings_path was not called
        mock_instance.with_settings_path.assert_not_called()


class TestProcessorIntegration:
    """Test processor integration with NornFlowBuilder."""

    @patch("nornflow.cli.run.NornFlowBuilder")
    def test_processors_added_to_builder(self, mock_builder):
        """Test that processors from CLI are added to NornFlowBuilder."""
        # Setup the mock
        mock_instance = MagicMock()
        mock_builder.return_value = mock_instance

        # Create test processor config
        processors = [
            {"class": "tests.unit.test_processors_utils.TestProcessor", "args": {"name": "CLIProcessor"}}
        ]

        # Call get_nornflow_builder with processors
        from nornflow.cli.run import get_nornflow_builder

        get_nornflow_builder("test_target", {}, {}, "", processors)

        # Verify with_processors was called with the processors
        mock_instance.with_processors.assert_called_once_with(processors)

    @patch("nornflow.cli.run.NornFlowBuilder")
    def test_multiple_processors_added_to_builder(self, mock_builder):
        """Test that multiple processors from CLI are added to NornFlowBuilder."""
        # Setup the mock
        mock_instance = MagicMock()
        mock_builder.return_value = mock_instance

        # Create test processor configs
        processors = [
            {"class": "tests.unit.test_processors_utils.TestProcessor", "args": {"name": "Processor1"}},
            {"class": "tests.unit.test_processors_utils.TestProcessor2", "args": {"name": "Processor2"}},
        ]

        # Call get_nornflow_builder with processors
        from nornflow.cli.run import get_nornflow_builder

        get_nornflow_builder("test_target", {}, {}, "", processors)

        # Verify with_processors was called with the processors
        mock_instance.with_processors.assert_called_once_with(processors)


class TestCLIWorkflowOverrides:
    """Test CLI overrides for workflow settings."""

    @patch("nornflow.cli.run.NornFlowBuilder")
    @patch("nornflow.cli.run.WorkflowFactory")
    def test_inventory_filters_override(self, mock_factory, mock_builder):
        """Test that CLI inventory filters override those in workflow file."""
        mock_instance = MagicMock()
        mock_builder.return_value = mock_instance

        # Create a mock workflow object with workflow_dict attribute
        mock_workflow = MagicMock()
        mock_workflow.workflow_dict = {"workflow": {"inventory_filters": {"original": "value"}}}
        mock_factory.create_from_file.return_value = mock_workflow

        from nornflow.cli.run import get_nornflow_builder

        # Create a dummy workflow file
        workflow_file = "override_test.yaml"
        Path(workflow_file).write_text("workflow:\n  name: Test\n  inventory_filters:\n    original: value")

        try:
            # Call with CLI inventory filters
            get_nornflow_builder(
                target=workflow_file,
                args={},
                inventory_filters={"platform": "ios", "vendor": "cisco"},
                settings_file="",
            )

            # Check that WorkflowFactory.create_from_file was called with a Path object
            mock_factory.create_from_file.assert_called_once()
            # Get the actual call args
            call_args = mock_factory.create_from_file.call_args[0]
            # Verify it's a Path object with the right value
            assert isinstance(call_args[0], Path)
            assert call_args[0].name == workflow_file

            # Assert that with_workflow_object was called with the workflow
            mock_instance.with_workflow_object.assert_called_once_with(mock_workflow)

            # Assert that with_cli_filters was called with the correct filters
            mock_instance.with_cli_filters.assert_called_once_with({"platform": "ios", "vendor": "cisco"})
        finally:
            if Path(workflow_file).exists():
                Path(workflow_file).unlink()


class TestCLIErrorHandling:
    """Test CLI error handling."""

    @patch("nornflow.cli.run.parse_key_value_pairs")
    def test_parse_error_handling(self, mock_parse):
        """Test error handling in parsing functions."""
        mock_parse.side_effect = ValueError("Invalid syntax")

        with pytest.raises(ValueError):
            parse_task_args("invalid=syntax]")

        with pytest.raises(ValueError):
            parse_inventory_filters("invalid=syntax]")

    @patch("nornflow.cli.run.NornFlowBuilder")
    @patch("nornflow.cli.run.WorkflowFactory")
    def test_missing_workflow_file(self, mock_factory, mock_builder):
        """Test handling of missing workflow file."""
        # Setup mocks
        mock_instance = MagicMock()
        mock_builder.return_value = mock_instance

        # Non-existent path but with yaml extension
        non_existent_file = "does_not_exist.yaml"

        # Mock Path.exists to return False
        with patch("nornflow.cli.run.Path.exists", return_value=False):
            # Should not raise exception, but call with_workflow_name
            get_nornflow_builder(
                target=non_existent_file,
                args={},
                inventory_filters={},
                settings_file="",
            )

            # Verify with_workflow_name was called instead of with_workflow_object
            mock_instance.with_workflow_name.assert_called_with(non_existent_file)


class TestMainCLIFunctionality:
    """Test the main CLI functionality and command execution."""

    @patch("nornflow.cli.run.get_nornflow_builder")
    def test_run_workflow(self, mock_get_builder):
        """Test running a workflow end-to-end."""
        # Setup mocks
        mock_nornflow = MagicMock()
        mock_get_builder.return_value.build.return_value = mock_nornflow

        # Create mock context and context object
        mock_ctx = MagicMock()
        mock_ctx.obj = {"settings": "test_settings.yaml"}

        # Call the actual CLI command function
        run(
            ctx=mock_ctx,
            target="test_workflow.yaml",  # Note the .yaml extension indicating a workflow
            args="arg1=value1",
            hosts=None,
            groups=None,
            inventory_filters="platform=ios",
            processors=None,
            vars=None,
            dry_run=True,
        )

        # Verify sequence of calls
        mock_get_builder.assert_called_once()
        mock_nornflow.run.assert_called_once_with(dry_run=True)

    @patch("nornflow.cli.run.get_nornflow_builder")
    def test_run_task(self, mock_get_builder):
        """Test running a single task end-to-end."""
        # Setup mocks
        mock_nornflow = MagicMock()
        mock_get_builder.return_value.build.return_value = mock_nornflow

        # Create mock context and context object
        mock_ctx = MagicMock()
        mock_ctx.obj = {"settings": ""}

        # Call the actual CLI command function
        run(
            ctx=mock_ctx,
            target="test_task",  # No .yaml extension indicates a task
            args="arg1=value1,arg2=value2",
            hosts=None,
            groups=None,
            inventory_filters="platform=ios,vendor=cisco",
            processors="class='tests.unit.test_processors_utils.TestProcessor',args={'name':'CLIProc'}",
            vars=None,
            dry_run=False,
        )

        # Verify get_nornflow_builder was called with correct params
        mock_get_builder.assert_called_once()
        # Verify run was called with dry_run parameter
        mock_nornflow.run.assert_called_once_with(dry_run=False)


# Prevent pytest from treating TestProcessor classes as test classes
TestProcessor.__test__ = False
TestProcessor2.__test__ = False
