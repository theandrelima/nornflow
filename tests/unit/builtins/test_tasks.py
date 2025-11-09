# filepath: test_tasks.py
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from nornir.core.task import Result

from nornflow.builtins.tasks import echo, set, write_file


class TestSetTask:
    def test_set_calls_build_set_task_report(self):
        """set() should call build_set_task_report and return its output in Result."""
        mock_task = MagicMock()
        mock_task.host = MagicMock()
        mock_task.host.name = "test_host"
        
        # Mock the vars_manager with required methods
        mock_vars_manager = MagicMock()
        mock_vars_manager.resolve_data.return_value = "resolved_value"
        
        with patch("nornflow.builtins.tasks.get_task_vars_manager", return_value=mock_vars_manager) as mock_get_vars:
            with patch("nornflow.builtins.tasks.build_set_task_report", return_value="REPORT") as mock_report:
                res: Result = set(mock_task, foo="bar")
                
                # Verify get_task_vars_manager was called
                mock_get_vars.assert_called_once_with(mock_task)
                
                # Verify vars_manager methods were called
                mock_vars_manager.resolve_data.assert_called_once_with("bar", "test_host")
                mock_vars_manager.set_runtime_variable.assert_called_once_with("foo", "resolved_value", "test_host")
                
                # Verify build_set_task_report was called and result returned
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
        # parent doesn't exist so would_create_dirs should be True
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

        # First write (mkdir True default)
        res1: Result = write_file(mock_task, filename=str(target), content=content1, append=False, mkdir=True)
        assert res1.failed is False
        assert res1.changed is True
        assert target.exists()
        assert target.read_text(encoding="utf-8") == content1

        # Append
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
        # Ensure parent does not exist
        if target.parent.exists():
            for p in target.parent.rglob("*"):
                if p.is_file():
                    p.unlink()
            target.parent.rmdir()

        res: Result = write_file(mock_task, filename=str(target), content="x", append=False, mkdir=False)
        assert res.failed is True
        assert hasattr(res, "exception")
        assert isinstance(res.exception, Exception)
    