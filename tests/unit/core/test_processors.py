from unittest.mock import MagicMock, patch

import pytest

from nornflow.exceptions import ProcessorError
from nornflow.models import WorkflowModel
from nornflow import NornFlow
from nornflow.utils import load_processor
from tests.unit.core.test_processors_utils import TestProcessor, TestProcessor2


class TestProcessorLoading:
    """Test processor loading functionality."""

    def test_load_processor(self, test_processor_config):
        """Test loading a processor from a configuration dictionary."""
        processor = load_processor(test_processor_config)
        assert isinstance(processor, TestProcessor)
        assert processor.name == "ConfiguredProcessor"
        assert processor.verbose is True

    def test_load_processor_without_args(self):
        """Test loading a processor with no arguments."""
        config = {"class": "tests.unit.core.test_processors_utils.TestProcessor"}
        processor = load_processor(config)
        assert isinstance(processor, TestProcessor)
        assert processor.name == "TestProcessor"  # Default value

    def test_load_processor_with_empty_args(self):
        """Test loading a processor with empty args dict."""
        config = {"class": "tests.unit.core.test_processors_utils.TestProcessor", "args": {}}
        processor = load_processor(config)
        assert isinstance(processor, TestProcessor)
        assert processor.name == "TestProcessor"  # Default value

    def test_load_invalid_processor(self):
        """Test loading a processor with an invalid class path."""
        config = {"class": "nonexistent.processor.Class", "args": {}}
        with pytest.raises(ProcessorError):
            load_processor(config)


class TestNornFlowProcessors:
    """Test NornFlow processor management."""

    @patch("nornflow.nornflow.NornFlow._load_tasks_catalog")
    @patch("nornflow.nornflow.NornFlow._load_workflows_catalog")
    @patch("nornflow.nornflow.NornFlow._load_filters_catalog")
    @patch("nornflow.nornir_manager.InitNornir")
    def test_load_kwargs_processors(self, mock_init_nornir, mock_filters, mock_workflows, mock_tasks):
        """Test loading processors from kwargs."""
        # Setup
        mock_nornir = MagicMock()
        mock_init_nornir.return_value = mock_nornir

        # Create settings with no processors
        settings = MagicMock()
        settings.processors = None
        
        # Mock the nornir config file check to avoid file not found errors
        settings.nornir_config_file = None

        # Create kwargs with processors
        kwargs_processors = [
            {
                "class": "tests.unit.core.test_processors_utils.TestProcessor",
                "args": {"name": "KwargsProcessor", "priority": 1},
            }
        ]

        # Create NornFlow with kwargs processors and bypass initialization
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nornflow = NornFlow(nornflow_settings=settings, processors=kwargs_processors)

            # Verify processors were loaded correctly
            assert len(nornflow.processors) == 1
            assert isinstance(nornflow.processors[0], TestProcessor)
            assert nornflow.processors[0].name == "KwargsProcessor"
            assert nornflow.processors[0].priority == 1


class TestProcessorPrecedence:
    """Test processor precedence rules."""

    @patch("nornflow.nornir_manager.InitNornir")
    def test_kwargs_override_workflow_processors(self, mock_init_nornir):
        """Test that kwargs processors override workflow model processors."""
        # Setup
        mock_nornir = MagicMock()
        mock_init_nornir.return_value = mock_nornir

        # Create settings
        settings = MagicMock()
        settings.processors = None
        settings.nornir_config_file = None  # Avoid file not found errors
        settings.dry_run = False

        # Create workflow with processors - must include at least one task
        workflow_dict = {
            "workflow": {
                "name": "Test",
                "tasks": [{"name": "dummy_task", "args": {"arg1": "value1"}}],
                "processors": [
                    {
                        "class": "tests.unit.core.test_processors_utils.TestProcessor",
                        "args": {"name": "WorkflowProc"},
                    }
                ],
            }
        }

        # Create the workflow model
        with patch("nornflow.models.WorkflowModel.create") as mock_create:
            # Configure the mock workflow
            workflow_model = MagicMock(spec=WorkflowModel)
            workflow_model.processors = [
                {"class": "tests.unit.core.test_processors_utils.TestProcessor", "args": {"name": "WorkflowProc"}}
            ]
            workflow_model.dry_run = False
            mock_create.return_value = workflow_model

            # Create kwargs processors
            kwargs_processors = [
                {"class": "tests.unit.core.test_processors_utils.TestProcessor2", "args": {"name": "KwargsProc"}}
            ]

            # Create NornFlow with both workflow and processors
            with patch("nornflow.nornflow.NornFlow._load_tasks_catalog"), \
                 patch("nornflow.nornflow.NornFlow._load_workflows_catalog"), \
                 patch("nornflow.nornflow.NornFlow._load_filters_catalog"), \
                 patch("nornflow.nornflow.NornFlow._initialize_nornir"):
                
                nornflow = NornFlow(
                    nornflow_settings=settings, 
                    workflow=workflow_model, 
                    processors=kwargs_processors
                )

                # Set up missing attributes that would normally be created by the mocked methods
                nornflow._tasks_catalog = {"dummy_task": MagicMock()}
                nornflow._workflows_catalog = {}
                nornflow._filters_catalog = {}
                
                # Mock necessary components for running
                mock_runner = MagicMock()
                nornflow._runner = mock_runner
                
                # Mock _vars_manager which is now needed
                mock_vars_manager = MagicMock()
                nornflow._vars_manager = mock_vars_manager
                
                # Verify that kwargs processors took precedence over workflow processors
                assert len(nornflow.processors) == 1
                assert isinstance(nornflow.processors[0], TestProcessor2)
                assert nornflow.processors[0].name == "KwargsProc"
