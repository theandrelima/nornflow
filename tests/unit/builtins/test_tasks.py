import builtins
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from nornir.core.task import Result

from nornflow.builtins.processors.default_processor import DefaultNornFlowProcessor
from nornflow.builtins.tasks import _countdown, _prompt_enter, echo, pause, write_file
from nornflow.builtins.tasks import set as set_task


class TestSetTask:
    def test_set_calls_build_set_task_report(self):
        """set() should call build_set_task_report and return its output in Result."""
        mock_task = MagicMock()
        mock_task.host = MagicMock()
        mock_task.host.name = "test_host"

        mock_vars_manager = MagicMock()
        mock_vars_manager.resolve_data.return_value = "resolved_value"

        with patch("nornflow.builtins.tasks.get_task_vars_manager", return_value=mock_vars_manager) as mock_get_vars:
            with patch("nornflow.builtins.tasks.build_set_task_report", return_value="REPORT") as mock_report:
                res: Result = set_task(mock_task, foo="bar")

                mock_get_vars.assert_called_once_with(mock_task)

                mock_vars_manager.resolve_data.assert_called_once_with("bar", "test_host")
                mock_vars_manager.set_runtime_variable.assert_called_once_with("foo", "resolved_value", "test_host")

                mock_report.assert_called_once_with(mock_task, {"foo": "bar"})
                assert isinstance(res, Result)
                assert res.result == "REPORT"


class TestEchoTask:
    def test_echo_returns_message(self):
        """echo() should return the provided message inside a Result."""
        mock_task = MagicMock()
        mock_task.host = MagicMock()
        msg = "hello"
        res: Result = echo(mock_task, msg=msg)
        assert isinstance(res, Result)
        assert res.result == msg


class TestPauseTask:
    """Test suite for the pause built-in task."""

    @pytest.fixture
    def pause_task(self):
        """Fixture providing a mock task configured for pause tests."""
        task = MagicMock()
        task.name = "pause_task"
        task.host = MagicMock()
        task.host.name = "router1"
        task.nornir = MagicMock()
        task.nornir.processors = []
        return task

    @pytest.fixture
    def mock_default_processor(self):
        """Fixture providing a mock DefaultNornFlowProcessor."""
        processor = MagicMock(spec=DefaultNornFlowProcessor)
        processor._pause_lock_holders = builtins.set()
        return processor

    def test_pause_acquires_output_lock(self, pause_task):
        """pause() must acquire output_lock before any I/O."""
        mock_lock = MagicMock()
        with patch("nornflow.builtins.tasks.output_lock", mock_lock):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=None):
                with patch("builtins.input", return_value=""):
                    pause(pause_task)

        mock_lock.acquire.assert_called_once()

    def test_pause_with_timer_calls_countdown(self, pause_task):
        """When timer > 0, pause delegates to _countdown."""
        with patch("nornflow.builtins.tasks.output_lock", MagicMock()):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=None):
                with patch("nornflow.builtins.tasks._countdown", return_value="Pause completed (5s)") as mock_cd:
                    result = pause(pause_task, timer=5)

        mock_cd.assert_called_once_with("[router1]", 5)
        assert result.result == "Pause completed (5s)"

    def test_pause_without_timer_calls_prompt(self, pause_task):
        """When timer is 0, pause delegates to _prompt_enter."""
        with patch("nornflow.builtins.tasks.output_lock", MagicMock()):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=None):
                with patch("nornflow.builtins.tasks._prompt_enter", return_value="Resumed by user") as mock_prompt:
                    result = pause(pause_task)

        mock_prompt.assert_called_once_with("[router1]")
        assert result.result == "Resumed by user"

    def test_pause_prints_message_when_provided(self, pause_task):
        """When msg is non-empty, pause prints separator + message + separator."""
        with patch("nornflow.builtins.tasks.output_lock", MagicMock()):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=None):
                with patch("builtins.input", return_value=""):
                    with patch("builtins.print") as mock_print:
                        pause(pause_task, msg="Check cables")

        printed = [str(c) for c in mock_print.call_args_list]
        assert any("Check cables" in s for s in printed)
        assert any("=" * 60 in str(c) for c in mock_print.call_args_list)

    def test_pause_does_not_print_when_no_message(self, pause_task):
        """When msg is empty, pause skips the message block entirely."""
        with patch("nornflow.builtins.tasks.output_lock", MagicMock()):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=None):
                with patch("builtins.input", return_value=""):
                    with patch("builtins.print") as mock_print:
                        pause(pause_task, msg="")

        for c in mock_print.call_args_list:
            assert "=" * 60 not in str(c)

    def test_pause_registers_lock_holder_when_processor_found(self, pause_task, mock_default_processor):
        """When DefaultNornFlowProcessor is found, pause registers (task.name, host.name) in _pause_lock_holders."""
        with patch("nornflow.builtins.tasks.output_lock", MagicMock()):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=mock_default_processor):
                with patch("builtins.input", return_value=""):
                    pause(pause_task)

        assert ("pause_task", "router1") in mock_default_processor._pause_lock_holders

    def test_pause_does_not_release_lock_when_processor_found(self, pause_task, mock_default_processor):
        """When processor is found, output_lock is NOT released by pause (processor does it later)."""
        mock_lock = MagicMock()
        with patch("nornflow.builtins.tasks.output_lock", mock_lock):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=mock_default_processor):
                with patch("builtins.input", return_value=""):
                    pause(pause_task)

        mock_lock.release.assert_not_called()

    def test_pause_releases_lock_when_no_processor(self, pause_task):
        """When no processor is found, pause releases output_lock itself."""
        mock_lock = MagicMock()
        with patch("nornflow.builtins.tasks.output_lock", mock_lock):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=None):
                with patch("builtins.input", return_value=""):
                    pause(pause_task)

        mock_lock.release.assert_called_once()

    def test_pause_returns_result_with_host(self, pause_task):
        """pause() always returns a Result bound to the task's host."""
        with patch("nornflow.builtins.tasks.output_lock", MagicMock()):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=None):
                with patch("builtins.input", return_value=""):
                    result = pause(pause_task)

        assert isinstance(result, Result)
        assert result.host is pause_task.host

    def test_pause_with_timer_and_message(self, pause_task):
        """pause() with both msg and timer prints message then runs countdown."""
        with patch("nornflow.builtins.tasks.output_lock", MagicMock()):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=None):
                with patch("nornflow.builtins.tasks._countdown", return_value="Pause completed (10s)") as mock_cd:
                    with patch("builtins.print") as mock_print:
                        result = pause(pause_task, msg="Rebooting", timer=10)

        assert any("Rebooting" in str(c) for c in mock_print.call_args_list)
        mock_cd.assert_called_once_with("[router1]", 10)
        assert result.result == "Pause completed (10s)"

    def test_pause_processor_lookup_uses_correct_type(self, pause_task):
        """pause() passes DefaultNornFlowProcessor as the type to find_processor_by_type."""
        with patch("nornflow.builtins.tasks.output_lock", MagicMock()):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=None) as mock_find:
                with patch("builtins.input", return_value=""):
                    pause(pause_task)

        mock_find.assert_called_once_with(pause_task.nornir.processors, DefaultNornFlowProcessor)

    def test_pause_releases_lock_on_exception(self, pause_task):
        """When an exception occurs during pause, the lock is released and the exception re-raised."""
        mock_lock = MagicMock()
        with patch("nornflow.builtins.tasks.output_lock", mock_lock):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=None):
                with patch("builtins.input", side_effect=KeyboardInterrupt):
                    with pytest.raises(KeyboardInterrupt):
                        pause(pause_task)

        mock_lock.release.assert_called_once()

    def test_pause_cleans_up_lock_holder_on_exception(self, pause_task, mock_default_processor):
        """When an exception occurs with a processor, the lock holder entry is discarded before re-raising."""
        mock_lock = MagicMock()
        with patch("nornflow.builtins.tasks.output_lock", mock_lock):
            with patch("nornflow.builtins.tasks.find_processor_by_type", return_value=mock_default_processor):
                with patch("builtins.input", side_effect=KeyboardInterrupt):
                    with pytest.raises(KeyboardInterrupt):
                        pause(pause_task)

        assert ("pause_task", "router1") not in mock_default_processor._pause_lock_holders
        mock_lock.release.assert_called_once()


class TestCountdown:
    """Test suite for the _countdown helper."""

    def test_countdown_returns_summary_string(self):
        """_countdown returns a summary including the duration."""
        with patch("nornflow.builtins.tasks.time.sleep"):
            with patch("builtins.print"):
                result = _countdown("[host1]", 2)

        assert result == "Pause completed (2s)"

    def test_countdown_sleeps_correct_number_of_times(self):
        """_countdown sleeps once per second for the given duration."""
        with patch("nornflow.builtins.tasks.time.sleep") as mock_sleep:
            with patch("builtins.print"):
                _countdown("[host1]", 3)

        assert mock_sleep.call_count == 3
        for c in mock_sleep.call_args_list:
            assert c == call(1)

    def test_countdown_zero_seconds(self):
        """_countdown with 0 seconds skips the loop entirely."""
        with patch("builtins.print"):
            result = _countdown("[host1]", 0)

        assert result == "Pause completed (0s)"


class TestPromptEnter:
    """Test suite for the _prompt_enter helper."""

    def test_prompt_enter_returns_resumed_message(self):
        """_prompt_enter returns 'Resumed by user' after input."""
        with patch("builtins.input", return_value="") as mock_input:
            result = _prompt_enter("[router1]")

        assert result == "Resumed by user"
        mock_input.assert_called_once_with("[router1] Press Enter to continue...")

    def test_prompt_enter_uses_host_label_in_prompt(self):
        """_prompt_enter includes the host label in the input prompt."""
        with patch("builtins.input", return_value="") as mock_input:
            _prompt_enter("[switch-42]")

        mock_input.assert_called_once_with("[switch-42] Press Enter to continue...")


class TestWriteFileTask:
    def test_missing_filename_returns_failed_result(self):
        """Missing filename should return a failed Result with ValueError."""
        mock_task = MagicMock()
        mock_task.host = MagicMock()
        res: Result = write_file(mock_task, filename="", content="x")
        assert res.failed is True
        assert isinstance(res.exception, ValueError)
        assert "filename argument is required" in str(res.exception)

    def test_missing_content_returns_failed_result(self):
        """Missing content should return a failed Result with ValueError."""
        mock_task = MagicMock()
        mock_task.host = MagicMock()
        res: Result = write_file(mock_task, filename="file.txt", content=None)
        assert res.failed is True
        assert isinstance(res.exception, ValueError)
        assert "content argument is required" in str(res.exception)

    def test_dry_run_returns_report_and_changed_flag(self, tmp_path: Path):
        """When task.is_dry_run() is True, no filesystem changes occur and a dry-run report is returned."""
        mock_task = MagicMock()
        mock_task.host = MagicMock()
        mock_task.is_dry_run.return_value = True

        target = tmp_path / "subdir" / "file.txt"
        content = "hello"
        res: Result = write_file(mock_task, filename=str(target), content=content, append=False, mkdir=True)

        assert isinstance(res, Result)
        assert res.changed is True
        assert isinstance(res.result, dict)
        assert res.result["path"] == str(target)
        assert res.result["dry_run"] is True
        assert res.result["operation"] == "write"
        assert res.result["would_create_dirs"] is True
        assert res.result["content_size_bytes"] == len(content)

    def test_actual_write_and_append(self, tmp_path: Path):
        """Writes create files when not dry-run; append appends to existing files."""
        mock_task = MagicMock()
        mock_task.host = MagicMock()
        mock_task.is_dry_run.return_value = False

        target_dir = tmp_path / "some" / "dir"
        target = target_dir / "file.txt"
        content1 = "first\n"
        content2 = "second\n"

        res1: Result = write_file(mock_task, filename=str(target), content=content1, append=False, mkdir=True)
        assert res1.failed is False
        assert res1.changed is True
        assert target.exists()
        assert target.read_text(encoding="utf-8") == content1

        res2: Result = write_file(mock_task, filename=str(target), content=content2, append=True, mkdir=True)
        assert res2.failed is False
        assert res2.changed is True
        assert target.read_text(encoding="utf-8") == content1 + content2

    def test_mkdir_false_parent_missing_raises_failure(self, tmp_path: Path):
        """If mkdir is False and parent directory is missing, write_file should return a failed Result."""
        mock_task = MagicMock()
        mock_task.host = MagicMock()
        mock_task.is_dry_run.return_value = False

        target = tmp_path / "nope" / "file.txt"
        if target.parent.exists():
            for p in target.parent.rglob("*"):
                if p.is_file():
                    p.unlink()
            target.parent.rmdir()

        res: Result = write_file(mock_task, filename=str(target), content="x", append=False, mkdir=False)
        assert res.failed is True
        assert hasattr(res, "exception")
        assert isinstance(res.exception, Exception)