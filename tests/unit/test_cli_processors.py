import pytest
from unittest.mock import patch, MagicMock

from nornflow.cli.run import parse_processors
from tests.unit.test_processors_utils import TestProcessor, TestProcessor2


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


class TestProcessorIntegration:
    """Test processor integration with NornFlowBuilder."""
    
    @patch('nornflow.cli.run.NornFlowBuilder')
    def test_processors_added_to_builder(self, mock_builder):
        """Test that processors from CLI are added to NornFlowBuilder."""
        # Setup the mock
        mock_instance = MagicMock()
        mock_builder.return_value = mock_instance
        mock_instance.with_kwargs.return_value = mock_instance
        
        # Create test processor config
        processors = [{
            "class": "tests.unit.test_processors_utils.TestProcessor",
            "args": {"name": "CLIProcessor"}
        }]
        
        # Call get_nornflow_builder with processors
        from nornflow.cli.run import get_nornflow_builder
        get_nornflow_builder("test_target", {}, {}, False, "", processors)
        
        # Verify with_kwargs was called with processors
        mock_instance.with_kwargs.assert_called_once()
        kwargs = mock_instance.with_kwargs.call_args[1]
        assert 'processors' in kwargs
        assert kwargs['processors'] == processors