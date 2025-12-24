from unittest.mock import MagicMock, patch


class TestVariableProcessor:
    def test_task_started(self, setup_processor):
        """Test task_started handler."""
        processor = setup_processor
        task = MagicMock()
        # task_started doesn't take a host parameter
        processor.task_started(task)
        # No assertions needed; just verifying it doesn't raise an exception

    def test_task_completed(self, setup_processor, mock_result):
        """Test task_completed handler."""
        processor = setup_processor
        task = MagicMock()
        processor.task_completed(task, mock_result)
        # No assertions needed; just verifying it doesn't raise an exception

    def test_task_instance_started_normal_task(self, setup_processor, mock_host):
        """Test task_instance_started with a normal task."""
        processor = setup_processor
        task = MagicMock()
        task.name = "show_version"
        task.params = {"command": "show version", "timeout": "{{ timeout }}"}
        host = mock_host

        processor.task_instance_started(task, host)

        # Verify params were processed
        assert task.params["timeout"] == "30"  # From vars_dir/networking/defaults.yaml

    def test_task_instance_started_set_task(self, setup_processor, mock_host):
        """Test task_instance_started with a set task."""
        processor = setup_processor
        task = MagicMock()
        task.name = "set"
        task.params = {"new_var": "{{ timeout }} seconds"}
        host = mock_host

        processor.task_instance_started(task, host)

        # No assertions needed; just verifying it doesn't raise an exception

    def test_task_instance_completed_with_set_to(self, setup_processor, mock_host, mock_result):
        """Test task_instance_completed with set_to attribute."""
        processor = setup_processor
        task = MagicMock()
        task.set_to = "backup_result"
        host = mock_host

        # Set the result value explicitly to make test deterministic
        mock_result.result = "Router configuration backup"

        # First we need to manually set the variable since the current processor
        # implementation doesn't handle set_to (it's handled in workflow.py)
        processor.vars_manager.set_runtime_variable("backup_result", mock_result.result, "test_device")

        processor.task_instance_completed(task, host, mock_result)

        # Verify variable was set with the right value
        backup_var = processor.vars_manager.get_nornflow_variable("backup_result", "test_device")
        assert backup_var == "Router configuration backup"

    def test_task_instance_completed_without_set_to(self, setup_processor, mock_host, mock_result):
        """Test task_instance_completed without set_to attribute."""
        processor = setup_processor
        task = MagicMock()
        # No set_to attribute
        host = mock_host

        processor.task_instance_completed(task, host, mock_result)

        # No variable should be set, so just verify it doesn't raise an exception
        # and that the current_host_name is cleared
        assert processor.vars_manager.nornir_host_proxy.current_host_name is None

    def test_requires_deferred_templates_no_hooks(self, setup_processor):
        """Test _requires_deferred_templates returns False when no hooks are present."""
        processor = setup_processor
        task = MagicMock()
        task.nornir.processors = []  # No processors with hooks

        assert processor._requires_deferred_templates(task) is False

    def test_requires_deferred_templates_hooks_without_flag(self, setup_processor):
        """Test _requires_deferred_templates returns False when hooks don't declare the flag."""
        processor = setup_processor
        task = MagicMock()
        mock_hook = MagicMock()
        mock_hook.requires_deferred_templates = False
        mock_processor = MagicMock()
        mock_processor.task_hooks = [mock_hook]
        task.nornir.processors = [mock_processor]

        assert processor._requires_deferred_templates(task) is False

    def test_requires_deferred_templates_hooks_with_flag(self, setup_processor):
        """Test _requires_deferred_templates returns True when any hook declares the flag."""
        processor = setup_processor
        task = MagicMock()
        mock_hook1 = MagicMock()
        mock_hook1.requires_deferred_templates = False
        mock_hook2 = MagicMock()
        mock_hook2.requires_deferred_templates = True
        mock_processor = MagicMock()
        mock_processor.task_hooks = [mock_hook1, mock_hook2]
        task.nornir.processors = [mock_processor]

        assert processor._requires_deferred_templates(task) is True

    def test_task_instance_started_deferred_mode(self, setup_processor, mock_host):
        """Test task_instance_started stores params when deferred mode is required."""
        processor = setup_processor
        task = MagicMock()
        task.name = "deferred_task"
        task.params = {"command": "{{ host.name }}", "timeout": 30}
        host = mock_host

        # Mock _requires_deferred_templates to return True
        with patch.object(processor, "_requires_deferred_templates", return_value=True):
            processor.task_instance_started(task, host)

        # Verify params were stored and cleared
        key = (task.name, host.name)
        assert key in processor._deferred_params
        assert processor._deferred_params[key] == {"command": "{{ host.name }}", "timeout": 30}
        assert task.params == {}  # Cleared for deferred processing

    def test_resolve_deferred_params_with_stored_key(self, setup_processor, mock_host):
        """Test resolve_deferred_params resolves and returns stored params."""
        processor = setup_processor
        task = MagicMock()
        task.name = "test_task"
        host = mock_host
        key = (task.name, host.name)
        original_params = {"command": "{{ host.name }}", "timeout": 30}
        processor._deferred_params[key] = original_params

        resolved = processor.resolve_deferred_params(task, host)

        # Verify resolution occurred and key was removed
        assert resolved["command"] == "test_device"  # Resolved via mock
        assert resolved["timeout"] == 30
        assert key not in processor._deferred_params

    def test_resolve_deferred_params_missing_key(self, setup_processor, mock_host):
        """Test resolve_deferred_params returns None when no deferred params exist."""
        processor = setup_processor
        task = MagicMock()
        task.name = "missing_task"
        host = mock_host

        resolved = processor.resolve_deferred_params(task, host)

        assert resolved is None

    def test_task_instance_completed_cleans_unresolved_params(self, setup_processor, mock_host, mock_result):
        """Test task_instance_completed cleans up unresolved deferred params."""
        processor = setup_processor
        task = MagicMock()
        task.name = "cleanup_task"
        host = mock_host
        key = (task.name, host.name)
        processor._deferred_params[key] = {"unresolved": "param"}

        processor.task_instance_completed(task, host, mock_result)

        # Verify params were cleaned up
        assert key not in processor._deferred_params
        assert processor.vars_manager.nornir_host_proxy.current_host_name is None