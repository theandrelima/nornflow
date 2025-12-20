# ruff: noqa: SLF001, T201
from unittest.mock import MagicMock
from nornflow.builtins.hooks import ShushHook


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

    def test_init_with_false_value(self):
        """Test hook initialization with False value."""
        hook = ShushHook(False)
        assert hook.value is False

    def test_init_without_value(self):
        """Test hook initialization without a value defaults to None."""
        hook = ShushHook()
        assert hook.value is None

    def test_init_with_none_value_explicit(self):
        """Test hook initialization with explicit None value."""
        hook = ShushHook(None)
        assert hook.value is None

    def test_init_with_jinja2_expression(self):
        """Test hook initialization with Jinja2 expression."""
        hook = ShushHook("{{ debug_mode }}")
        assert hook.value == "{{ debug_mode }}"

    def test_init_with_jinja2_expression_using_percent(self):
        """Test hook initialization with Jinja2 expression using {% syntax."""
        hook = ShushHook("{% if condition %}true{% endif %}")
        assert hook.value == "{% if condition %}true{% endif %}"

    def test_task_started_does_nothing_when_false(self, mock_task):
        """Test task_started does nothing when value is False."""
        hook = ShushHook(False)

        hook.task_started(mock_task)

        assert not hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')

    def test_task_started_does_nothing_when_none(self, mock_task):
        """Test task_started does nothing when value is None."""
        hook = ShushHook(None)

        hook.task_started(mock_task)

        assert not hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')

    def test_task_started_warns_when_no_compatible_processor(self, capsys, mock_task):
        """Test task_started warns when no processor supports shush hook."""
        hook = ShushHook(True)
        
        mock_task.nornir.processors = []

        hook.task_started(mock_task)

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "no compatible processor found" in captured.out
        assert not hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')

    def test_task_started_warns_when_processor_lacks_support(self, capsys, mock_task, mock_processor_incompatible):
        """Test task_started warns when processor doesn't have supports_shush_hook attribute."""
        hook = ShushHook(True)
        
        mock_task.nornir.processors = [mock_processor_incompatible]

        hook.task_started(mock_task)

        captured = capsys.readouterr()
        assert "Warning: 'shush' hook has no effect - " in captured.out
        assert "no compatible processor found in chain. Outputs are not going to be suppressed." in captured.out
        assert not hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')

    def test_task_started_sets_suppression_marker_with_compatible_processor(self, mock_task, mock_processor_compatible):
        """Test task_started sets suppression marker when compatible processor exists."""
        hook = ShushHook(True)
        
        mock_task.nornir.processors = [mock_processor_compatible]
        
        # Mock the hook's context to include a task_model with canonical_id
        mock_task_model = MagicMock()
        mock_task_model.canonical_id = "test_task"
        hook._current_context = {"task_model": mock_task_model}

        hook.task_started(mock_task)

        assert hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')
        assert isinstance(mock_task.nornir._nornflow_suppressed_tasks, set)
        assert "test_task" in mock_task.nornir._nornflow_suppressed_tasks

    def test_task_started_creates_set_if_not_exists(self, mock_task, mock_processor_compatible):
        """Test task_started creates the suppressed_tasks set if it doesn't exist."""
        hook = ShushHook(True)
        
        mock_task.nornir.processors = [mock_processor_compatible]
        mock_task.name = "task1"
        
        # Mock the hook's context to include a task_model with canonical_id
        mock_task_model = MagicMock()
        mock_task_model.canonical_id = "task1"
        hook._current_context = {"task_model": mock_task_model}

        hook.task_started(mock_task)

        assert hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')
        assert "task1" in mock_task.nornir._nornflow_suppressed_tasks

    def test_task_started_adds_to_existing_set(self, mock_task, mock_processor_compatible):
        """Test task_started adds task name to existing suppressed_tasks set."""
        hook = ShushHook(True)
        
        mock_task.nornir._nornflow_suppressed_tasks = {"task1"}
        mock_task.nornir.processors = [mock_processor_compatible]
        mock_task.name = "task2"
        
        # Mock the hook's context to include a task_model with canonical_id
        mock_task_model = MagicMock()
        mock_task_model.canonical_id = "task2"
        hook._current_context = {"task_model": mock_task_model}

        hook.task_started(mock_task)

        assert "task1" in mock_task.nornir._nornflow_suppressed_tasks
        assert "task2" in mock_task.nornir._nornflow_suppressed_tasks

    def test_task_started_with_multiple_processors_one_compatible(self, mock_task, mock_processor_compatible, mock_processor_incompatible):
        """Test task_started works when one of multiple processors is compatible."""
        hook = ShushHook(True)
        
        mock_task.nornir.processors = [mock_processor_incompatible, mock_processor_compatible]
        
        # Mock the hook's context to include a task_model with canonical_id
        mock_task_model = MagicMock()
        mock_task_model.canonical_id = "test_task"
        hook._current_context = {"task_model": mock_task_model}

        hook.task_started(mock_task)

        assert hasattr(mock_task.nornir, '_nornflow_suppressed_tasks')
        assert "test_task" in mock_task.nornir._nornflow_suppressed_tasks

    def test_task_completed_removes_suppression_marker(self, mock_nornir):
        """Test task_completed removes the task from suppressed_tasks set."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_task.nornir = mock_nornir
        mock_task.nornir._nornflow_suppressed_tasks = {"test_task", "other_task"}
        
        # Mock the hook's context to include a task_model with canonical_id
        mock_task_model = MagicMock()
        mock_task_model.canonical_id = "test_task"
        hook._current_context = {"task_model": mock_task_model}

        hook.task_completed(mock_task, MagicMock())

        assert "test_task" not in mock_task.nornir._nornflow_suppressed_tasks
        assert "other_task" in mock_task.nornir._nornflow_suppressed_tasks

    def test_task_completed_handles_missing_attribute(self, mock_nornir):
        """Test task_completed handles missing _nornflow_suppressed_tasks gracefully."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_task.nornir = mock_nornir

        hook.task_completed(mock_task, MagicMock())

    def test_task_completed_handles_task_not_in_set(self, mock_nornir):
        """Test task_completed handles task not being in the set gracefully."""
        hook = ShushHook(True)
        mock_task = MagicMock()
        mock_task.name = "test_task"
        mock_task.nornir = mock_nornir
        mock_task.nornir._nornflow_suppressed_tasks = {"other_task"}
        
        # Mock the hook's context to include a task_model with canonical_id
        mock_task_model = MagicMock()
        mock_task_model.canonical_id = "test_task"
        hook._current_context = {"task_model": mock_task_model}

        hook.task_completed(mock_task, MagicMock())

        assert "other_task" in mock_task.nornir._nornflow_suppressed_tasks

    def test_validate_string_with_jinja2_markers(self):
        """Test validation passes for string values with Jinja2 markers."""
        from nornflow.models import TaskModel
        
        hook = ShushHook("{{ some_var }}")
        task_model = TaskModel.create({"name": "test_task", "args": {}})
        
        hook.execute_hook_validations(task_model)

    def test_validate_boolean_values(self):
        """Test validation passes for boolean values."""
        from nornflow.models import TaskModel
        
        hook_true = ShushHook(True)
        hook_false = ShushHook(False)
        task_model = TaskModel.create({"name": "test_task", "args": {}})
        
        hook_true.execute_hook_validations(task_model)
        hook_false.execute_hook_validations(task_model)

    def test_get_resolved_value_with_boolean_true(self, mock_task):
        """Test get_resolved_value returns True for boolean True value."""
        hook = ShushHook(True)
        
        result = hook.get_resolved_value(mock_task, as_bool=True, default=False)
        
        assert result is True

    def test_get_resolved_value_with_boolean_false(self, mock_task):
        """Test get_resolved_value returns False for boolean False value."""
        hook = ShushHook(False)
        
        result = hook.get_resolved_value(mock_task, as_bool=True, default=False)
        
        assert result is False

    def test_get_resolved_value_with_none(self, mock_task):
        """Test get_resolved_value returns default for None value."""
        hook = ShushHook(None)
        
        result = hook.get_resolved_value(mock_task, as_bool=True, default=False)
        
        assert result is False

    def test_get_resolved_value_with_jinja2_expression_true(self, mock_task, mock_vars_manager):
        """Test get_resolved_value with Jinja2 expression that evaluates to True."""
        hook = ShushHook("{{ true }}")
        
        # Configure vars_manager to return "true" string when resolving
        mock_vars_manager.resolve_string.return_value = "true"
        
        # Configure hook context
        hook._current_context = {"vars_manager": mock_vars_manager}
        
        # Configure mock task inventory for host extraction
        mock_host = MagicMock()
        mock_host.name = "test_host"
        mock_task.nornir.inventory.hosts = {"test_host": mock_host}
        
        result = hook.get_resolved_value(mock_task, as_bool=True, default=False)
        
        assert result is True
        mock_vars_manager.resolve_string.assert_called_with("{{ true }}", "test_host")

    def test_get_resolved_value_with_jinja2_expression_false(self, mock_task, mock_vars_manager):
        """Test get_resolved_value with Jinja2 expression that evaluates to False."""
        hook = ShushHook("{{ false }}")
        
        # Configure vars_manager to return "false" string when resolving
        mock_vars_manager.resolve_string.return_value = "false"
        
        # Configure hook context
        hook._current_context = {"vars_manager": mock_vars_manager}
        
        # Configure mock task inventory for host extraction
        mock_host = MagicMock()
        mock_host.name = "test_host"
        mock_task.nornir.inventory.hosts = {"test_host": mock_host}
        
        result = hook.get_resolved_value(mock_task, as_bool=True, default=False)
        
        assert result is False
        mock_vars_manager.resolve_string.assert_called_with("{{ false }}", "test_host")

    def test_hook_with_truthy_non_boolean_values(self):
        """Test hook handles truthy non-boolean values correctly."""
        hook = ShushHook("yes")
        assert hook.value == "yes"

    def test_hook_with_falsy_non_boolean_values(self):
        """Test hook handles falsy non-boolean values correctly."""
        hook = ShushHook("")
        assert hook.value == ""

    def test_hook_with_integer_zero(self, mock_task):
        """Test hook with integer 0 (falsy non-boolean)."""
        hook = ShushHook(0)
        
        result = hook.get_resolved_value(mock_task, as_bool=True, default=False)
        
        assert result is False

    def test_hook_with_integer_one(self, mock_task):
        """Test hook with integer 1 (truthy non-boolean)."""
        hook = ShushHook(1)
        
        result = hook.get_resolved_value(mock_task, as_bool=True, default=False)
        
        assert result is True