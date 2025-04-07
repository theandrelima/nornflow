import pytest
from unittest.mock import patch, MagicMock

from nornflow.exceptions import ProcessorError
from nornflow.utils import load_processor
from nornflow.nornflow import NornFlow
from nornflow.workflow import WorkflowFactory
from tests.unit.test_processors_utils import TestProcessor, TestProcessor2


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
        config = {
            "class": "tests.unit.test_processors_utils.TestProcessor"
        }
        processor = load_processor(config)
        assert isinstance(processor, TestProcessor)
        assert processor.name == "TestProcessor"  # Default value
        
    def test_load_processor_with_empty_args(self):
        """Test loading a processor with empty args dict."""
        config = {
            "class": "tests.unit.test_processors_utils.TestProcessor",
            "args": {}
        }
        processor = load_processor(config)
        assert isinstance(processor, TestProcessor)
        assert processor.name == "TestProcessor"  # Default value
        
    def test_load_invalid_processor(self):
        """Test loading a processor with an invalid class path."""
        config = {
            "class": "nonexistent.processor.Class",
            "args": {}
        }
        with pytest.raises(ProcessorError):
            load_processor(config)


class TestNornFlowProcessors:
    """Test NornFlow processor management."""
    
    @patch('nornflow.nornflow.NornFlow._load_tasks_catalog')
    @patch('nornflow.nornflow.NornFlow._load_workflows_catalog')  
    @patch('nornflow.nornflow.NornFlow._load_filters_catalog')
    @patch('nornflow.nornir_manager.InitNornir')
    def test_load_kwargs_processors(self, mock_init, mock_filters, mock_workflows, mock_tasks):
        """Test loading processors from kwargs."""
        # Setup
        mock_nornir = MagicMock()
        mock_init.return_value = mock_nornir
        
        # Create settings with no processors
        settings = MagicMock()
        settings.processors = None
        
        # Create kwargs with processors
        kwargs_processors = [{
            "class": "tests.unit.test_processors_utils.TestProcessor",
            "args": {"name": "KwargsProcessor", "priority": 1}
        }]
        
        # Create NornFlow with kwargs processors
        nornflow = NornFlow(nornflow_settings=settings, processors=kwargs_processors)
        
        # Verify processors were loaded correctly
        assert len(nornflow.processors) == 1
        assert isinstance(nornflow.processors[0], TestProcessor)
        assert nornflow.processors[0].name == "KwargsProcessor"
        assert nornflow.processors[0].priority == 1


class TestProcessorPrecedence:
    """Test processor precedence rules."""
    
    @patch('nornflow.nornir_manager.InitNornir')
    def test_kwargs_override_workflow_processors(self, mock_init):
        """Test that kwargs processors override workflow processors."""
        # Setup
        mock_nornir = MagicMock()
        mock_init.return_value = mock_nornir
        
        # Create settings
        settings = MagicMock()
        settings.processors = None
        settings.nornir_config_file = "dummy_config.yaml"
        settings.dry_run = False
        
        # Create workflow with processors - must include at least one task
        workflow_dict = {"workflow": {
            "name": "Test", 
            "tasks": [{"name": "dummy_task", "args": {"arg1": "value1"}}],
            "processors": [
                {"class": "tests.unit.test_processors_utils.TestProcessor", "args": {"name": "WorkflowProc"}}
            ]
        }}
        
        # Mock the WorkflowFactory and Workflow to avoid validation errors
        with patch('nornflow.workflow.Workflow') as mock_workflow, \
             patch('nornflow.nornflow.NornFlow._load_tasks_catalog'), \
             patch('nornflow.nornflow.NornFlow._load_workflows_catalog'), \
             patch('nornflow.nornflow.NornFlow._load_filters_catalog'):
            
            # Configure the mock workflow
            workflow_instance = MagicMock()
            workflow_instance.processors_config = workflow_dict["workflow"]["processors"]
            mock_workflow.return_value = workflow_instance
            
            # Create the workflow through the factory
            workflow = WorkflowFactory.create_from_dict(workflow_dict)
            
            # Create kwargs processors
            kwargs_processors = [{
                "class": "tests.unit.test_processors_utils.TestProcessor2",
                "args": {"name": "KwargsProc"}
            }]
            
            # Create NornFlow with both
            nornflow = NornFlow(
                nornflow_settings=settings,
                workflow=workflow,
                processors=kwargs_processors
            )
            
            # Set up missing attributes that would normally be created by the mocked methods
            nornflow._tasks_catalog = {"dummy_task": MagicMock()}
            nornflow._workflows_catalog = {}
            nornflow._filters_catalog = {}
            
            # Run NornFlow
            nornflow.run()
            
            # Verify workflow processors were disabled
            assert workflow.processors_config is None
