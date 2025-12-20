"""Tests for failure handling strategies (skip-failed, fail-fast, run-all)."""

from unittest.mock import MagicMock, patch

import pytest

from nornflow import NornFlow, NornFlowBuilder
from nornflow.builtins.processors import (
    DefaultNornFlowProcessor,
    NornFlowFailureStrategyProcessor,
)
from nornflow.constants import FailureStrategy
from nornflow.models import WorkflowModel
from nornflow.settings import NornFlowSettings


class TestFailureStrategyConstants:
    """Test FailureStrategy enum and normalization."""

    def test_failure_strategy_enum_values(self):
        """Test that FailureStrategy enum has expected values."""
        assert FailureStrategy.SKIP_FAILED == "skip-failed"
        assert FailureStrategy.FAIL_FAST == "fail-fast"
        assert FailureStrategy.RUN_ALL == "run-all"

    def test_failure_strategy_from_string(self):
        """Test creating FailureStrategy from string values."""
        assert FailureStrategy("skip-failed") == FailureStrategy.SKIP_FAILED
        assert FailureStrategy("fail-fast") == FailureStrategy.FAIL_FAST
        assert FailureStrategy("run-all") == FailureStrategy.RUN_ALL

    def test_failure_strategy_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            FailureStrategy("invalid-strategy")


class TestDefaultNornFlowProcessor:
    """Test DefaultNornFlowProcessor statistics and timing."""

    def test_processor_initialization(self):
        """Test processor initialization with default values."""
        processor = DefaultNornFlowProcessor()
        assert processor.task_count == 0
        assert processor.task_executions == 0
        assert processor.tasks_completed == 0
        assert processor.successful_executions == 0
        assert processor.failed_executions == 0
        assert processor.workflow_start_time is None
        assert processor.print_summary_after_each_task is False

    def test_task_started_sets_workflow_start_time(self):
        """Test that first task started sets workflow start time."""
        processor = DefaultNornFlowProcessor()
        mock_task = MagicMock()
        mock_task.name = "test_task"
        
        with patch("builtins.print"):
            processor.task_started(mock_task)
        
        assert processor.workflow_start_time is not None
        assert processor.task_count == 1

    def test_task_instance_started_increments_executions(self):
        """Test that task_instance_started increments execution count."""
        processor = DefaultNornFlowProcessor()
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_host = MagicMock()
        mock_host.name = "test_host"
        
        processor.task_instance_started(mock_task, mock_host)

    def test_task_instance_completed_success(self):
        """Test task_instance_completed with successful result."""
        processor = DefaultNornFlowProcessor()
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_task.host = MagicMock()
        mock_task.host.hostname = "test_hostname"
        mock_host = MagicMock()
        mock_host.name = "test_host"
        mock_result = MagicMock()
        mock_result.failed = False
        mock_result.result = "Success output"
        
        processor.task_instance_started(mock_task, mock_host)
        
        with patch("builtins.print"):
            processor.task_instance_completed(mock_task, mock_host, mock_result)

    def test_task_instance_completed_failure(self):
        """Test task_instance_completed with failed result."""
        processor = DefaultNornFlowProcessor()
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_task.host = MagicMock()
        mock_task.host.hostname = "test_hostname"
        mock_host = MagicMock()
        mock_host.name = "test_host"
        mock_result = MagicMock()
        mock_result.failed = True
        mock_result.result = "Error output"
        
        processor.task_instance_started(mock_task, mock_host)
        
        with patch("builtins.print"):
            processor.task_instance_completed(mock_task, mock_host, mock_result)

    def test_task_completed_increments_count(self):
        """Test that task_completed increments tasks_completed."""
        processor = DefaultNornFlowProcessor()
        mock_task = MagicMock()
        mock_result = MagicMock()
        
        processor.task_completed(mock_task, mock_result)
        
        assert processor.tasks_completed == 1

    @patch("builtins.print")
    def test_print_workflow_summary_no_executions(self, mock_print):
        """Test print_workflow_summary when no tasks executed."""
        processor = DefaultNornFlowProcessor()
        
        processor.print_workflow_summary()
        
        mock_print.assert_not_called()

    @patch("builtins.print")
    def test_print_workflow_summary_with_statistics(self, mock_print):
        """Test print_workflow_summary displays correct statistics."""
        processor = DefaultNornFlowProcessor()
        
        mock_task = MagicMock()
        mock_task.name = "test_task"
        
        with patch("builtins.print"):
            processor.task_started(mock_task)
        
        processor.task_executions = 10
        processor.successful_executions = 7
        processor.failed_executions = 3
        processor.tasks_completed = 2
        
        processor.print_workflow_summary()
        
        assert mock_print.called
        call_args = [str(call) for call in mock_print.call_args_list]
        summary_output = " ".join(call_args)
        
        assert "EXECUTION SUMMARY" in summary_output
        assert "70.0%" in summary_output or "30.0%" in summary_output


class TestNornFlowFailureStrategyProcessor:
    """Test NornFlowFailureStrategyProcessor behavior."""

    def test_processor_initialization_skip_failed(self):
        """Test processor initialization with SKIP_FAILED strategy."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.SKIP_FAILED)
        assert processor.failure_strategy == FailureStrategy.SKIP_FAILED
        assert processor.collected_errors == []
        assert processor.fail_fast_triggered is False
        assert processor.nornir is None

    def test_processor_initialization_fail_fast(self):
        """Test processor initialization with FAIL_FAST strategy."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.FAIL_FAST)
        assert processor.failure_strategy == FailureStrategy.FAIL_FAST

    def test_processor_initialization_run_all(self):
        """Test processor initialization with RUN_ALL strategy."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.RUN_ALL)
        assert processor.failure_strategy == FailureStrategy.RUN_ALL

    def test_task_instance_completed_success(self):
        """Test task_instance_completed with successful result."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.SKIP_FAILED)
        
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_host = MagicMock()
        mock_host.name = "test_host"
        mock_result = MagicMock()
        mock_result.failed = False

        processor.task_instance_completed(mock_task, mock_host, mock_result)

        assert len(processor.collected_errors) == 0
        assert processor.fail_fast_triggered is False

    def test_task_instance_completed_failure_skip_failed(self):
        """Test task_instance_completed with failed result and SKIP_FAILED strategy."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.SKIP_FAILED)
        
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_host = MagicMock()
        mock_host.name = "test_host"
        mock_result = MagicMock()
        mock_result.failed = True
        mock_result.exception = Exception("Test error")

        processor.task_instance_completed(mock_task, mock_host, mock_result)

        assert len(processor.collected_errors) == 1
        assert processor.collected_errors[0] == ("test_task", "test_host", mock_result)
        assert processor.fail_fast_triggered is False

    @patch("builtins.print")
    def test_task_instance_completed_failure_fail_fast(self, mock_print):
        """Test task_instance_completed with failed result and FAIL_FAST strategy."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.FAIL_FAST)
        
        mock_nornir = MagicMock()
        mock_nornir.inventory.hosts = {
            "host1": MagicMock(),
            "host2": MagicMock(),
            "host3": MagicMock(),
        }
        mock_nornir.data.failed_hosts = set()
        processor.nornir = mock_nornir
        
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_host = MagicMock()
        mock_host.name = "test_host"
        mock_result = MagicMock()
        mock_result.failed = True
        mock_result.exception = Exception("Test error")

        processor.task_instance_completed(mock_task, mock_host, mock_result)

        assert processor.fail_fast_triggered is True
        assert len(processor.collected_errors) == 1
        assert "host1" in mock_nornir.data.failed_hosts
        assert "host2" in mock_nornir.data.failed_hosts
        assert "host3" in mock_nornir.data.failed_hosts

    def test_task_instance_completed_failure_run_all(self):
        """Test task_instance_completed with failed result and RUN_ALL strategy."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.RUN_ALL)
        
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_host = MagicMock()
        mock_host.name = "test_host"
        mock_result = MagicMock()
        mock_result.failed = True

        processor.task_instance_completed(mock_task, mock_host, mock_result)

        assert len(processor.collected_errors) == 1
        assert processor.fail_fast_triggered is False

    def test_multiple_failures_collected(self):
        """Test that multiple failures are collected correctly."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.SKIP_FAILED)
        
        for i in range(3):
            mock_task = MagicMock()
            mock_task.name = f"test_task_{i}"
            mock_host = MagicMock()
            mock_host.name = f"test_host_{i}"
            mock_result = MagicMock()
            mock_result.failed = True

            processor.task_instance_completed(mock_task, mock_host, mock_result)

        assert len(processor.collected_errors) == 3

    def test_task_started_run_all_resets_failed_hosts(self):
        """Test that RUN_ALL strategy resets failed hosts on task start."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.RUN_ALL)
        
        mock_nornir = MagicMock()
        mock_nornir.data.reset_failed_hosts = MagicMock()
        processor.nornir = mock_nornir
        
        mock_task = MagicMock()
        mock_task.nornir = mock_nornir
        
        processor.task_started(mock_task)
        
        mock_nornir.data.reset_failed_hosts.assert_called_once()

    def test_task_started_skip_failed_no_reset(self):
        """Test that SKIP_FAILED strategy doesn't reset failed hosts."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.SKIP_FAILED)
        
        mock_nornir = MagicMock()
        mock_nornir.data.reset_failed_hosts = MagicMock()
        processor.nornir = mock_nornir
        
        mock_task = MagicMock()
        mock_task.nornir = mock_nornir
        
        processor.task_started(mock_task)
        
        mock_nornir.data.reset_failed_hosts.assert_not_called()

    @patch("nornflow.builtins.processors.failure_strategy_processor.tabulate")
    @patch("builtins.print")
    def test_print_final_workflow_summary_with_errors(self, mock_print, mock_tabulate):
        """Test print_final_workflow_summary prints error table."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.SKIP_FAILED)
        
        mock_result = MagicMock()
        mock_result.exception = Exception("Test error")
        processor.collected_errors = [
            ("task1", "host1", mock_result),
            ("task2", "host2", mock_result),
        ]

        processor.print_final_workflow_summary()

        mock_tabulate.assert_called_once()
        call_args = mock_tabulate.call_args
        assert call_args[1]["headers"] == ["Task", "Host", "Error"]

    @patch("builtins.print")
    def test_print_final_workflow_summary_no_errors(self, mock_print):
        """Test print_final_workflow_summary with no errors doesn't print table."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.SKIP_FAILED)
        
        processor.print_final_workflow_summary()
        
        mock_print.assert_not_called()


class TestExitCodeScenarios:
    """Test exit code calculations for different scenarios."""

    def test_exit_code_zero_all_success(self):
        """Test exit code 0 when all tasks succeed."""
        processor = DefaultNornFlowProcessor()
        processor.task_executions = 10
        processor.successful_executions = 10
        processor.failed_executions = 0
        
        if processor.task_executions > 0 and processor.failed_executions > 0:
            exit_code = int((processor.failed_executions / processor.task_executions) * 100)
        else:
            exit_code = 0
        
        assert exit_code == 0

    def test_exit_code_percentage_partial_failure(self):
        """Test exit code 1-100 for partial failures (failure percentage)."""
        test_cases = [
            (10, 1, 10),
            (10, 5, 50),
            (10, 9, 90),
            (100, 25, 25),
            (20, 3, 15),
        ]
        
        for total, failed, expected_code in test_cases:
            processor = DefaultNornFlowProcessor()
            processor.task_executions = total
            processor.successful_executions = total - failed
            processor.failed_executions = failed
            
            exit_code = int((processor.failed_executions / processor.task_executions) * 100)
            
            assert exit_code == expected_code, f"Expected {expected_code} for {failed}/{total} failures"

    def test_exit_code_100_all_failures(self):
        """Test exit code 100 when all tasks fail."""
        processor = DefaultNornFlowProcessor()
        processor.task_executions = 10
        processor.successful_executions = 0
        processor.failed_executions = 10
        
        exit_code = int((processor.failed_executions / processor.task_executions) * 100)
        
        assert exit_code == 100


class TestCLIFailureStrategyIntegration:
    """Test CLI parameter handling for failure strategies."""

    def test_parse_failure_strategy_valid_values(self):
        """Test parse_failure_strategy with valid values."""
        from nornflow.cli.run import parse_failure_strategy
        
        assert parse_failure_strategy("skip-failed") == FailureStrategy.SKIP_FAILED
        assert parse_failure_strategy("skip_failed") == FailureStrategy.SKIP_FAILED
        assert parse_failure_strategy("fail-fast") == FailureStrategy.FAIL_FAST
        assert parse_failure_strategy("fail_fast") == FailureStrategy.FAIL_FAST
        assert parse_failure_strategy("run-all") == FailureStrategy.RUN_ALL
        assert parse_failure_strategy("run_all") == FailureStrategy.RUN_ALL
        assert parse_failure_strategy(None) is None

    def test_parse_failure_strategy_case_insensitive(self):
        """Test parse_failure_strategy is case-insensitive."""
        from nornflow.cli.run import parse_failure_strategy
        
        assert parse_failure_strategy("SKIP-FAILED") == FailureStrategy.SKIP_FAILED
        assert parse_failure_strategy("Skip-Failed") == FailureStrategy.SKIP_FAILED
        assert parse_failure_strategy("FAIL-FAST") == FailureStrategy.FAIL_FAST
        assert parse_failure_strategy("RUN-ALL") == FailureStrategy.RUN_ALL

    def test_parse_failure_strategy_invalid_value(self):
        """Test parse_failure_strategy raises error for invalid values."""
        from nornflow.cli.run import parse_failure_strategy
        from nornflow.cli.exceptions import CLIRunError
        
        with pytest.raises(CLIRunError):
            parse_failure_strategy("invalid-strategy")


class TestNornFlowFailureStrategy:
    """Test NornFlow's failure strategy handling."""
    
    @patch('nornflow.nornflow.load_file_to_dict')
    @patch('nornflow.nornir_manager.InitNornir')
    def test_nornflow_with_explicit_failure_strategy(self, mock_init_nornir, mock_load_file):
        """Test NornFlow initialized with explicit failure strategy."""
        mock_nornir_instance = MagicMock()
        mock_nornir_instance.inventory.hosts = {}
        mock_init_nornir.return_value = mock_nornir_instance
        
        mock_load_file.return_value = {
            'core': {'num_workers': 1},
            'inventory': {'plugin': 'SimpleInventory', 'options': {}}
        }
        
        workflow_model = MagicMock(spec=WorkflowModel)
        workflow_model.failure_strategy = FailureStrategy.SKIP_FAILED
        
        settings = NornFlowSettings(nornir_config_file="mock_config.yaml")
        
        nornflow = NornFlow(
            nornflow_settings=settings,
            workflow=workflow_model,
            failure_strategy=FailureStrategy.FAIL_FAST
        )
        
        assert nornflow.failure_strategy == FailureStrategy.FAIL_FAST
        
    @patch('nornflow.nornflow.load_file_to_dict')
    @patch('nornflow.nornir_manager.InitNornir')
    def test_nornflow_defaults_to_workflow_strategy(self, mock_init_nornir, mock_load_file):
        """Test NornFlow uses workflow's strategy when not explicitly set."""
        mock_nornir_instance = MagicMock()
        mock_nornir_instance.inventory.hosts = {}
        mock_init_nornir.return_value = mock_nornir_instance
        
        mock_load_file.return_value = {
            'core': {'num_workers': 1},
            'inventory': {'plugin': 'SimpleInventory', 'options': {}}
        }
        
        workflow_model = MagicMock(spec=WorkflowModel)
        workflow_model.failure_strategy = FailureStrategy.RUN_ALL
        
        settings = NornFlowSettings(nornir_config_file="mock_config.yaml")
        
        nornflow = NornFlow(
            nornflow_settings=settings,
            workflow=workflow_model
        )
        
        assert nornflow.failure_strategy == FailureStrategy.RUN_ALL
        
    @patch('nornflow.nornir_manager.InitNornir')
    @patch('nornflow.nornflow.load_file_to_dict')
    def test_nornflow_defaults_to_settings_strategy(self, mock_load_file, mock_init_nornir):
        """Test NornFlow uses settings' strategy when workflow doesn't specify one."""
        mock_nornir_instance = MagicMock()
        mock_nornir_instance.inventory.hosts = {}
        mock_init_nornir.return_value = mock_nornir_instance
        
        mock_load_file.return_value = {
            'core': {'num_workers': 1},
            'inventory': {'plugin': 'SimpleInventory', 'options': {}}
        }
        
        settings = NornFlowSettings(
            nornir_config_file='mock_config.yaml',
            failure_strategy=FailureStrategy.FAIL_FAST
        )

        nornflow = NornFlow(nornflow_settings=settings)
        
        assert nornflow.failure_strategy == FailureStrategy.FAIL_FAST


class TestNornFlowBuilderWithFailureStrategy:
    """Test NornFlowBuilder with failure strategy configuration."""

    def test_builder_with_cli_failure_strategy(self):
        """Test builder accepts and passes CLI failure strategy."""
        builder = NornFlowBuilder()
        builder.with_failure_strategy(FailureStrategy.FAIL_FAST)
        
        assert builder._failure_strategy == FailureStrategy.FAIL_FAST
        
        mock_workflow = MagicMock(spec=WorkflowModel)
        mock_workflow.failure_strategy = FailureStrategy.SKIP_FAILED
        
        with patch.object(builder, '_settings', new=MagicMock()):
            builder._workflow = mock_workflow
            
            with patch('nornflow.builder.NornFlow') as mock_nornflow:
                builder.build()
                
                call_kwargs = mock_nornflow.call_args.kwargs
                assert call_kwargs['failure_strategy'] == FailureStrategy.FAIL_FAST

    def test_builder_without_cli_failure_strategy(self):
        """Test builder without CLI failure strategy defaults to None."""
        builder = NornFlowBuilder()
        
        assert builder._failure_strategy is None


class TestFailFastBehavior:
    """Test FAIL_FAST specific behavior."""

    @patch("builtins.print")
    def test_fail_fast_adds_all_hosts_to_failed(self, mock_print):
        """Test that FAIL_FAST adds all hosts to failed_hosts immediately."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.FAIL_FAST)
        
        mock_nornir = MagicMock()
        mock_nornir.inventory.hosts = {
            "host1": MagicMock(),
            "host2": MagicMock(),
            "host3": MagicMock(),
            "host4": MagicMock(),
        }
        mock_nornir.data.failed_hosts = set()
        processor.nornir = mock_nornir
        
        mock_task = MagicMock()
        mock_task.name = "failing_task"
        mock_host = MagicMock()
        mock_host.name = "host2"
        mock_result = MagicMock()
        mock_result.failed = True
        mock_result.exception = Exception("Connection timeout")

        processor.task_instance_completed(mock_task, mock_host, mock_result)

        assert len(mock_nornir.data.failed_hosts) == 4
        assert all(
            host in mock_nornir.data.failed_hosts 
            for host in ["host1", "host2", "host3", "host4"]
        )

    @patch("builtins.print")
    def test_fail_fast_only_triggers_once(self, mock_print):
        """Test that FAIL_FAST only triggers on first failure."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.FAIL_FAST)
        
        mock_nornir = MagicMock()
        mock_nornir.inventory.hosts = {"host1": MagicMock(), "host2": MagicMock()}
        mock_nornir.data.failed_hosts = set()
        processor.nornir = mock_nornir
        
        mock_task = MagicMock()
        mock_task.name = "test_task"
        
        for i in range(3):
            mock_host = MagicMock()
            mock_host.name = f"host{i}"
            mock_result = MagicMock()
            mock_result.failed = True
            mock_result.exception = Exception(f"Error {i}")
            
            processor.task_instance_completed(mock_task, mock_host, mock_result)
        
        assert processor.fail_fast_triggered is True
        assert len(processor.collected_errors) == 3


class TestRunAllBehavior:
    """Test RUN_ALL specific behavior."""

    def test_run_all_resets_failed_hosts_each_task(self):
        """Test that RUN_ALL resets failed hosts before each task."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.RUN_ALL)
        
        mock_nornir = MagicMock()
        mock_nornir.data.reset_failed_hosts = MagicMock()
        processor.nornir = mock_nornir
        
        for i in range(3):
            mock_task = MagicMock()
            mock_task.name = f"task_{i}"
            mock_task.nornir = mock_nornir
            
            processor.task_started(mock_task)
        
        assert mock_nornir.data.reset_failed_hosts.call_count == 3

    def test_run_all_collects_all_errors(self):
        """Test that RUN_ALL collects errors from all tasks."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.RUN_ALL)
        
        mock_nornir = MagicMock()
        processor.nornir = mock_nornir
        
        for task_num in range(3):
            for host_num in range(2):
                mock_task = MagicMock()
                mock_task.name = f"task_{task_num}"
                mock_host = MagicMock()
                mock_host.name = f"host_{host_num}"
                mock_result = MagicMock()
                mock_result.failed = True
                mock_result.exception = Exception(f"Error task{task_num} host{host_num}")
                
                processor.task_instance_completed(mock_task, mock_host, mock_result)
        
        assert len(processor.collected_errors) == 6
        assert processor.fail_fast_triggered is False


class TestSkipFailedBehavior:
    """Test SKIP_FAILED specific behavior."""

    def test_skip_failed_collects_errors_but_continues(self):
        """Test that SKIP_FAILED collects errors without stopping."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.SKIP_FAILED)
        
        for i in range(5):
            mock_task = MagicMock()
            mock_task.name = f"task_{i}"
            mock_host = MagicMock()
            mock_host.name = f"host_{i}"
            mock_result = MagicMock()
            mock_result.failed = True
            mock_result.exception = Exception(f"Error {i}")
            
            processor.task_instance_completed(mock_task, mock_host, mock_result)
        
        assert len(processor.collected_errors) == 5
        assert processor.fail_fast_triggered is False

    def test_skip_failed_does_not_reset_failed_hosts(self):
        """Test that SKIP_FAILED doesn't reset failed hosts between tasks."""
        processor = NornFlowFailureStrategyProcessor(FailureStrategy.SKIP_FAILED)
        
        mock_nornir = MagicMock()
        mock_nornir.data.reset_failed_hosts = MagicMock()
        processor.nornir = mock_nornir
        
        mock_task = MagicMock()
        mock_task.nornir = mock_nornir
        
        processor.task_started(mock_task)
        processor.task_started(mock_task)
        processor.task_started(mock_task)
        
        mock_nornir.data.reset_failed_hosts.assert_not_called()