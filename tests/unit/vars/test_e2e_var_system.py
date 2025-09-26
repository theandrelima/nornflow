from unittest.mock import MagicMock


class TestVariableE2E:
    def test_complete_variable_resolution(self, setup_manager):
        """Test resolving variables from all sources in one template."""
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

        result = manager.resolve_string(template, "test_device")

        # Check that variables from all sources are resolved correctly
        assert "Host: test_device (192.168.1.1)" in result
        assert "Platform: ios" in result
        assert "Location: HQ" in result
        assert "Backup Type: full" in result  # workflow var
        assert "Timeout: 30 seconds" in result  # domain var
        assert "Credentials: /etc/credentials.yaml" in result  # env var
        assert "Dry Run: True" in result  # CLI var
        assert "Status: Config backup complete" in result  # runtime var

    def test_variable_processor_integration(self, setup_processor, mock_host, mock_result):
        """Test the variable processor integrating with task execution."""
        processor = setup_processor
        host = mock_host

        # Create a mock task with template params
        task = MagicMock()
        task.name = "my_task"
        task.params = {"command": "show run | include {{ host.name }}", "timeout": "{{ timeout }}"}

        # Process task start
        processor.task_instance_started(task, host)

        # Verify params were resolved
        assert task.params["command"] == "show run | include test_device"
        assert task.params["timeout"] == "30"

        # Add set_to to the task
        task.set_to = "backup_result"

        # Process task completion
        processor.task_instance_completed(task, host, mock_result)

        # Verify runtime variable was set
        assert (
            processor.vars_manager.get_nornflow_variable("backup_result", host.name).result
            == "Router configuration backup"
        )
