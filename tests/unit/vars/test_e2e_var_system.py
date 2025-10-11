"""End-to-end tests that exercise NornFlow variable-resolution and processor flow."""

from unittest.mock import MagicMock

import pytest

from nornflow.vars.exceptions import VariableError
from nornflow.vars.processors import NornFlowVariableProcessor


class TestVariableE2E:
    """Validate complete variable-resolution flows."""

    def test_complete_variable_resolution(self, setup_manager) -> None:
        """Ensure variables from every precedence tier resolve correctly."""
        manager = setup_manager

        template = """
        Backup Configuration:
          Host: {{ host.name }} ({{ host.hostname }})
          Platform: {{ host.platform }}
          Location: {{ host.data.location.building }}

          Settings:
            Backup Type: {{ backup_type }}
            Backup Server: {{ backup_server | default('unknown') }}
            Retention: {{ retention_days | default(0) }} days
            Timeout: {{ timeout }} seconds
            Credentials: {{ credentials_file }}
            Dry Run: {{ dry_run }}

          Status: {{ command_output }}
        """

        rendered = manager.resolve_string(template, "test_device")

        assert "Host: test_device (192.168.1.1)" in rendered
        assert "Platform: ios" in rendered
        assert "Location: HQ" in rendered
        assert "Backup Type: full" in rendered
        assert "Timeout: 30 seconds" in rendered
        assert "Credentials: /etc/cli_credentials.yaml" in rendered  # CLI overrides env
        assert "Dry Run: True" in rendered
        assert "Status: Config backup complete" in rendered

    def test_variable_processor_integration(
        self,
        setup_processor: NornFlowVariableProcessor,
        mock_host,
        mock_result,
    ) -> None:
        """Verify processor resolves params and stores runtime variables."""
        processor = setup_processor
        host = mock_host

        task = MagicMock()
        task.name = "my_task"
        task.params = {
            "command": "show run | include {{ host.name }}",
            "timeout": "{{ timeout }}",
        }

        # Resolve parameters at task start
        processor.task_instance_started(task, host)
        assert task.params["command"] == "show run | include test_device"
        assert task.params["timeout"] == "30"

        # Emulate workflow: store result under a runtime variable
        task.set_to = "backup_result"
        processor.vars_manager.set_runtime_variable(task.set_to, mock_result, host.name)

        # Run completion hook
        processor.task_instance_completed(task, host, mock_result)

        stored = processor.vars_manager.get_nornflow_variable("backup_result", host.name)
        assert stored.result == "Router configuration backup"

        with pytest.raises(VariableError):
            processor.vars_manager.get_nornflow_variable("nonexistent_var", host.name)
