# filepath: /Users/andrelima/Personal/portfolio_projects/nornflow/tests/unit/builtins/test_shush_hook.py
from unittest.mock import MagicMock

from nornflow.builtins.hooks import ShushHook


class MockNornir:
    """Simple mock object for Nornir that behaves like a real object for attribute checks."""
    
    def __init__(self):
        self.processors = []


class TestShushHook:
    """Test suite for ShushHook."""

    def test_hook_name_registration(self):
        """Test that hook has correct name for registration."""
        assert ShushHook.hook_name == "shush"

    def test_run_once_per_task_flag(self):
        """Test that hook runs once per task."""
        assert ShushHook.run_once_per_task is True

    def test_init_with_true_value(self):
        """Test hook initialization with True value."""
        hook = ShushHook(True)
        assert hook.value is True
        assert hook.should_suppress is True

    def test_init_with_false_value(self):
        """Test hook initialization with False value."""
        hook = ShushHook(False)
        assert hook.value is False
        assert hook.should_suppress is False

    def test_init_without_value(self):
        """Test hook initialization without a value defaults to False."""
        hook = ShushHook()
        assert hook.value is None
        assert hook.should_suppress is False

    def test_init_with_none_value_explicit(self):
        """Test hook initialization with explicit None value."""
        hook = ShushHook(None)
        assert hook.value is None
        assert hook.should_suppress is False

    def test_task_started_does_nothing_when_false(self):
        """Test task_started does nothing when should_suppress is False."""
        hook = ShushHook(False)
        mock_task = MagicMock()
        mock_task.nornir = MockNornir()

        hook.task_started(mock_task)

        assert not hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')

    def test_task_started_warns_when_no_compatible_processor(self, capsys):
        """Test task_started warns when no processor supports shush hook."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.nornir = MockNornir()
        mock_task.nornir.processors = []

        hook.task_started(mock_task)

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "no compatible processor found" in captured.out
        assert not hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')

    def test_task_started_warns_when_processor_lacks_support(self, capsys):
        """Test task_started warns when processor doesn't have supports_shush_hook attribute."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.nornir = MockNornir()
        
        mock_processor = MagicMock()
        mock_processor.supports_shush_hook = False
        mock_task.nornir.processors = [mock_processor]

        hook.task_started(mock_task)

        captured = capsys.readouterr()
        assert "Warning: 'shush' hook has no effect - " in captured.out
        assert "no compatible processor found in chain. Outputs are not going to be suppressed." in captured.out
        assert not hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')

    def test_task_started_sets_suppression_marker_with_compatible_processor(self):
        """Test task_started sets suppression marker when compatible processor exists."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_task.nornir = MockNornir()
        
        mock_processor = MagicMock()
        mock_processor.supports_shush_hook = True
        mock_task.nornir.processors = [mock_processor]

        hook.task_started(mock_task)

        assert hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')
        assert isinstance(mock_task.nornir._nornflow_suppressed_tasks, set)
        assert "test_task" in mock_task.nornir._nornflow_suppressed_tasks

    def test_task_started_creates_set_if_not_exists(self):
        """Test task_started creates the suppressed_tasks set if it doesn't exist."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.name = "task1"
        mock_task.nornir = MockNornir()
        
        mock_processor = MagicMock()
        mock_processor.supports_shush_hook = True
        mock_task.nornir.processors = [mock_processor]

        hook.task_started(mock_task)

        assert hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')
        assert "task1" in mock_task.nornir._nornflow_suppressed_tasks

    def test_task_started_adds_to_existing_set(self):
        """Test task_started adds task name to existing suppressed_tasks set."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.name = "task2"
        mock_task.nornir = MockNornir()
        mock_task.nornir._nornflow_suppressed_tasks = {"task1"}
        
        mock_processor = MagicMock()
        mock_processor.supports_shush_hook = True
        mock_task.nornir.processors = [mock_processor]

        hook.task_started(mock_task)

        assert "task1" in mock_task.nornir._nornflow_suppressed_tasks
        assert "task2" in mock_task.nornir._nornflow_suppressed_tasks

    def test_task_started_with_multiple_processors_one_compatible(self):
        """Test task_started works when one of multiple processors is compatible."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_task.nornir = MockNornir()
        
        mock_processor1 = MagicMock()
        mock_processor1.supports_shush_hook = False
        
        mock_processor2 = MagicMock()
        mock_processor2.supports_shush_hook = True
        
        mock_task.nornir.processors = [mock_processor1, mock_processor2]

        hook.task_started(mock_task)

        assert hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')
        assert "test_task" in mock_task.nornir._nornflow_suppressed_tasks

    def test_task_completed_removes_suppression_marker(self):
        """Test task_completed removes task from suppression set."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_task.nornir = MockNornir()
        mock_task.nornir._nornflow_suppressed_tasks = {"test_task", "other_task"}
        mock_result = MagicMock()

        hook.task_completed(mock_task, mock_result)

        assert "test_task" not in mock_task.nornir._nornflow_suppressed_tasks
        assert "other_task" in mock_task.nornir._nornflow_suppressed_tasks

    def test_task_completed_handles_missing_attribute(self):
        """Test task_completed handles case when _nornflow_suppressed_tasks doesn't exist."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_task.nornir = MockNornir()
        mock_result = MagicMock()

        hook.task_completed(mock_task, mock_result)

    def test_task_completed_handles_task_not_in_set(self):
        """Test task_completed handles case when task name isn't in the set."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_task.nornir = MockNornir()
        mock_task.nornir._nornflow_suppressed_tasks = {"other_task"}
        mock_result = MagicMock()

        hook.task_completed(mock_task, mock_result)

        assert "other_task" in mock_task.nornir._nornflow_suppressed_tasks

    def test_other_processor_methods_do_nothing(self):
        """Test that other processor methods have no implementation."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_result = MagicMock()

        hook.task_instance_started(mock_task, mock_host)
        hook.task_instance_completed(mock_task, mock_host, mock_result)
        hook.subtask_instance_started(mock_task, mock_host)
        hook.subtask_instance_completed(mock_task, mock_host, mock_result)

    def test_should_execute_respects_run_once_per_task(self):
        """Test that hook respects run_once_per_task setting."""
        hook = ShushHook(True)
        mock_task = MagicMock()

        assert hook.should_execute(mock_task) is True

        assert hook.should_execute(mock_task) is False

        mock_task2 = MagicMock()
        assert hook.should_execute(mock_task2) is True

    def test_hook_with_truthy_non_boolean_values(self):
        """Test hook handles truthy non-boolean values correctly."""
        hook = ShushHook("yes")
        assert hook.should_suppress is True

        hook = ShushHook(1)
        assert hook.should_suppress is True

        hook = ShushHook(["item"])
        assert hook.should_suppress is True

    def test_hook_with_falsy_non_boolean_values(self):
        """Test hook handles falsy non-boolean values correctly."""
        hook = ShushHook("")
        assert hook.should_suppress is False

        hook = ShushHook(0)
        assert hook.should_suppress is False

        hook = ShushHook([])
        assert hook.should_suppress is False

    def test_task_started_processor_check_with_no_attribute(self):
        """Test task_started handles processors without supports_shush_hook attribute."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_task.nornir = MockNornir()
        
        mock_processor = MagicMock(spec=[])
        mock_task.nornir.processors = [mock_processor]

        hook.task_started(mock_task)

        assert not hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')
