from types import ModuleType
from typing import Literal
from unittest.mock import Mock, patch

import pytest
from nornir.core.inventory import Host
from nornir.core.processor import Processor
from nornir.core.task import AggregatedResult, MultiResult, Result, Task
from pydantic_serdes.custom_collections import HashableDict

from nornflow.constants import FailureStrategy
from nornflow.exceptions import CoreError, ProcessorError, ResourceError, WorkflowError
from nornflow.utils import (
    check_for_jinja2_recursive,
    convert_lists_to_tuples,
    format_variable_value,
    get_file_content_hash,
    import_module_from_path,
    import_modules_recursively,
    is_nornir_filter,
    is_nornir_task,
    is_yaml_file,
    load_processor,
    normalize_failure_strategy,
    print_workflow_overview,
    process_filter,
)


class TestGetFileContentHash:
    """Tests for get_file_content_hash function."""

    def test_hash_basic_yaml_file(self, tmp_path):
        """Test hashing basic YAML file."""
        test_file = tmp_path / "test.yaml"
        test_file.write_text("key: value\nlist:\n  - item1\n  - item2")

        file_hash = get_file_content_hash(test_file)

        assert isinstance(file_hash, str)
        assert len(file_hash) == 16

    def test_hash_consistency(self, tmp_path):
        """Test same content produces same hash."""
        test_file = tmp_path / "test.yaml"
        test_file.write_text("key: value")

        hash1 = get_file_content_hash(test_file)
        hash2 = get_file_content_hash(test_file)

        assert hash1 == hash2

    def test_hash_different_content(self, tmp_path):
        """Test different content produces different hashes."""
        file1 = tmp_path / "file1.yaml"
        file2 = tmp_path / "file2.yaml"

        file1.write_text("key: value1")
        file2.write_text("key: value2")

        hash1 = get_file_content_hash(file1)
        hash2 = get_file_content_hash(file2)

        assert hash1 != hash2

    def test_hash_nonexistent_file(self, tmp_path):
        """Test error for nonexistent file."""
        nonexistent = tmp_path / "nonexistent.yaml"

        with pytest.raises(ResourceError, match="Failed to hash file content"):
            get_file_content_hash(nonexistent)

    def test_hash_yaml_normalization(self, tmp_path):
        """Test YAML formatting differences produce same hash."""
        file1 = tmp_path / "file1.yaml"
        file2 = tmp_path / "file2.yaml"

        file1.write_text("key: value\nlist: [1, 2, 3]")
        file2.write_text("key: value\nlist:\n  - 1\n  - 2\n  - 3")

        hash1 = get_file_content_hash(file1)
        hash2 = get_file_content_hash(file2)

        assert hash1 == hash2

    def test_hash_invalid_yaml(self, tmp_path):
        """Test error for invalid YAML content."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("key: value\n  invalid: indentation")

        with pytest.raises(ResourceError, match="Failed to hash file content"):
            get_file_content_hash(invalid_file)

    def test_hash_complex_yaml(self, tmp_path):
        """Test hashing complex YAML structures."""
        test_file = tmp_path / "complex.yaml"
        test_file.write_text("""
nested:
  deep:
    level: 3
    items:
      - name: item1
        value: 100
      - name: item2
        value: 200
mapping:
  a: 1
  b: 2
""")

        file_hash = get_file_content_hash(test_file)

        assert isinstance(file_hash, str)
        assert len(file_hash) == 16

    def test_hash_empty_file(self, tmp_path):
        """Test hashing empty YAML file."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        file_hash = get_file_content_hash(empty_file)

        assert isinstance(file_hash, str)
        assert len(file_hash) == 16


class TestNormalizeFailureStrategy:
    """Tests for normalize_failure_strategy function."""

    def test_normalize_from_string(self):
        """Test normalizing from string value."""
        result = normalize_failure_strategy("skip-failed", WorkflowError)
        assert result == FailureStrategy.SKIP_FAILED

    def test_normalize_from_enum(self):
        """Test normalizing from enum value."""
        result = normalize_failure_strategy(FailureStrategy.FAIL_FAST, WorkflowError)
        assert result == FailureStrategy.FAIL_FAST

    def test_normalize_invalid_string(self):
        """Test error for invalid string value."""
        with pytest.raises(WorkflowError, match="Invalid failure strategy"):
            normalize_failure_strategy("invalid-strategy", WorkflowError)

    def test_normalize_invalid_type(self):
        """Test error for invalid type."""
        with pytest.raises(WorkflowError, match="Invalid failure strategy type"):
            normalize_failure_strategy(123, WorkflowError)

    def test_normalize_with_different_exception(self):
        """Test using different exception class."""
        with pytest.raises(ProcessorError, match="Invalid failure strategy"):
            normalize_failure_strategy("invalid", ProcessorError)

    def test_normalize_all_valid_strategies(self):
        """Test normalizing all valid strategy strings."""
        for strategy in FailureStrategy:
            result = normalize_failure_strategy(strategy.value, WorkflowError)
            assert result == strategy


class TestImportModuleFromPath:
    """Tests for import_module_from_path function."""

    def test_import_valid_module(self, tmp_path):
        """Test importing valid Python module."""
        module_file = tmp_path / "test_module.py"
        module_file.write_text("def test_func():\n    return 'success'")

        module = import_module_from_path("test_module", module_file)

        assert isinstance(module, ModuleType)
        assert hasattr(module, "test_func")
        assert module.test_func() == "success"

    def test_import_nonexistent_file(self, tmp_path):
        """Test error for nonexistent file."""
        nonexistent = tmp_path / "nonexistent.py"

        with pytest.raises(CoreError, match="Failed to import module"):
            import_module_from_path("test", nonexistent)

    def test_import_invalid_syntax(self, tmp_path):
        """Test error for invalid Python syntax."""
        invalid_file = tmp_path / "invalid.py"
        invalid_file.write_text("def invalid syntax")

        with pytest.raises(CoreError, match="Failed to import module"):
            import_module_from_path("invalid", invalid_file)

    def test_import_module_with_class(self, tmp_path):
        """Test importing module containing a class."""
        module_file = tmp_path / "with_class.py"
        module_file.write_text("class TestClass:\n    value = 42")

        module = import_module_from_path("with_class", module_file)

        assert hasattr(module, "TestClass")
        assert module.TestClass.value == 42

    def test_import_module_with_dependencies(self, tmp_path):
        """Test importing module with standard library dependencies."""
        module_file = tmp_path / "with_deps.py"
        module_file.write_text("import json\ndef parse(s):\n    return json.loads(s)")

        module = import_module_from_path("with_deps", module_file)

        assert hasattr(module, "parse")
        assert module.parse('{"key": "value"}') == {"key": "value"}


class TestImportModulesRecursively:
    """Tests for import_modules_recursively function."""

    def test_import_single_module(self, tmp_path):
        """Test importing single module from directory."""
        module_file = tmp_path / "module1.py"
        module_file.write_text("VALUE = 1")

        with patch("nornflow.utils.Path.cwd", return_value=tmp_path):
            imported = import_modules_recursively(tmp_path)

        assert len(imported) == 1
        assert "module1" in imported[0]

    def test_import_multiple_modules(self, tmp_path):
        """Test importing multiple modules."""
        (tmp_path / "mod1.py").write_text("VALUE = 1")
        (tmp_path / "mod2.py").write_text("VALUE = 2")

        with patch("nornflow.utils.Path.cwd", return_value=tmp_path):
            imported = import_modules_recursively(tmp_path)

        assert len(imported) == 2

    def test_import_nested_modules(self, tmp_path):
        """Test importing modules from nested directories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "root.py").write_text("VALUE = 1")
        (subdir / "nested.py").write_text("VALUE = 2")

        with patch("nornflow.utils.Path.cwd", return_value=tmp_path):
            imported = import_modules_recursively(tmp_path)

        assert len(imported) == 2

    def test_skip_init_files(self, tmp_path):
        """Test that __init__.py files are skipped."""
        (tmp_path / "__init__.py").write_text("# init")
        (tmp_path / "module.py").write_text("VALUE = 1")

        with patch("nornflow.utils.Path.cwd", return_value=tmp_path):
            imported = import_modules_recursively(tmp_path)

        assert len(imported) == 1

    def test_continue_on_import_error(self, tmp_path):
        """Test that import continues on error."""
        (tmp_path / "valid.py").write_text("VALUE = 1")
        (tmp_path / "invalid.py").write_text("def invalid syntax")

        with patch("nornflow.utils.Path.cwd", return_value=tmp_path):
            imported = import_modules_recursively(tmp_path)

        assert len(imported) == 1

    def test_import_deeply_nested(self, tmp_path):
        """Test importing from deeply nested structure."""
        level1 = tmp_path / "level1"
        level2 = level1 / "level2"
        level3 = level2 / "level3"
        level3.mkdir(parents=True)

        (tmp_path / "root.py").write_text("VALUE = 0")
        (level1 / "l1.py").write_text("VALUE = 1")
        (level2 / "l2.py").write_text("VALUE = 2")
        (level3 / "l3.py").write_text("VALUE = 3")

        with patch("nornflow.utils.Path.cwd", return_value=tmp_path):
            imported = import_modules_recursively(tmp_path)

        assert len(imported) == 4

    def test_import_empty_directory(self, tmp_path):
        """Test importing from empty directory."""
        with patch("nornflow.utils.Path.cwd", return_value=tmp_path):
            imported = import_modules_recursively(tmp_path)

        assert len(imported) == 0


class TestIsNornirTask:
    """Tests for is_nornir_task function."""

    def test_valid_nornir_task(self):
        """Test valid Nornir task is recognized."""
        def valid_task(task: Task) -> Result:
            return Result(host=task.host)

        assert is_nornir_task(valid_task)

    def test_task_with_multiresult(self):
        """Test task returning MultiResult."""
        def multi_task(task: Task) -> MultiResult:
            return MultiResult("test")

        assert is_nornir_task(multi_task)

    def test_task_with_aggregated_result(self):
        """Test task returning AggregatedResult."""
        def agg_task(task: Task) -> AggregatedResult:
            return AggregatedResult("test")

        assert is_nornir_task(agg_task)

    def test_missing_task_param(self):
        """Test function without Task parameter."""
        def not_task(host: Host) -> Result:
            return Result(host=host)

        assert not is_nornir_task(not_task)

    def test_wrong_return_type(self):
        """Test function with wrong return type."""
        def wrong_return(task: Task) -> str:
            return "not a result"

        assert not is_nornir_task(wrong_return)

    def test_no_annotations(self):
        """Test function without annotations."""
        def no_annotations(task):
            return None

        assert not is_nornir_task(no_annotations)

    def test_not_callable(self):
        """Test non-callable object."""
        assert not is_nornir_task("not a function")

    def test_task_with_additional_params(self):
        """Test task with additional parameters."""
        def task_with_params(task: Task, param1: str, param2: int) -> Result:
            return Result(host=task.host)

        assert is_nornir_task(task_with_params)

    def test_partial_annotations(self):
        """Test function with partial annotations."""
        def partial(task, other: str) -> Result:
            return Result(host=None)

        assert not is_nornir_task(partial)


class TestIsNornirFilter:
    """Tests for is_nornir_filter function."""

    def test_valid_filter_bool_return(self):
        """Test valid filter with bool return."""
        def valid_filter(host: Host, value: str) -> bool:
            return True

        assert is_nornir_filter(valid_filter)

    def test_valid_filter_literal_return(self):
        """Test valid filter with Literal return."""
        def literal_filter(host: Host) -> Literal[True, False]:
            return True

        assert is_nornir_filter(literal_filter)

    def test_missing_host_param(self):
        """Test function without Host parameter."""
        def no_host(value: str) -> bool:
            return True

        assert not is_nornir_filter(no_host)

    def test_wrong_first_param_type(self):
        """Test function with wrong first parameter type."""
        def wrong_param(task: Task, value: str) -> bool:
            return True

        assert not is_nornir_filter(wrong_param)

    def test_wrong_return_type(self):
        """Test function with wrong return type."""
        def wrong_return(host: Host) -> str:
            return "not bool"

        assert not is_nornir_filter(wrong_return)

    def test_not_callable(self):
        """Test non-callable object."""
        assert not is_nornir_filter("not a function")

    def test_filter_with_multiple_params(self):
        """Test filter with multiple parameters."""
        def multi_param_filter(host: Host, platform: str, site: str) -> bool:
            return True

        assert is_nornir_filter(multi_param_filter)

    def test_filter_host_only(self):
        """Test filter with only host parameter."""
        def host_only(host: Host) -> bool:
            return True

        assert is_nornir_filter(host_only)


class TestProcessFilter:
    """Tests for process_filter function."""

    def test_process_simple_filter(self):
        """Test processing filter with additional params."""
        def test_filter(host: Host, platform: str, groups: list) -> bool:
            return True

        func, params = process_filter(test_filter)

        assert func is test_filter
        assert params == ["platform", "groups"]

    def test_process_filter_host_only(self):
        """Test processing filter with only host param."""
        def simple_filter(host: Host) -> bool:
            return True

        func, params = process_filter(simple_filter)

        assert func is simple_filter
        assert params == []

    def test_process_filter_many_params(self):
        """Test processing filter with many parameters."""
        def complex_filter(host: Host, a: str, b: int, c: bool, d: list) -> bool:
            return True

        func, params = process_filter(complex_filter)

        assert func is complex_filter
        assert params == ["a", "b", "c", "d"]


class TestIsYamlFile:
    """Tests for is_yaml_file function."""

    def test_yaml_extension(self, tmp_path):
        """Test .yaml extension is recognized."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value")

        assert is_yaml_file(yaml_file)

    def test_yml_extension(self, tmp_path):
        """Test .yml extension is recognized."""
        yml_file = tmp_path / "test.yml"
        yml_file.write_text("key: value")

        assert is_yaml_file(yml_file)

    def test_non_yaml_extension(self, tmp_path):
        """Test non-YAML file is rejected."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")

        assert not is_yaml_file(txt_file)

    def test_nonexistent_file(self, tmp_path):
        """Test nonexistent file is rejected."""
        nonexistent = tmp_path / "nonexistent.yaml"

        assert not is_yaml_file(nonexistent)

    def test_directory(self, tmp_path):
        """Test directory is rejected."""
        directory = tmp_path / "test.yaml"
        directory.mkdir()

        assert not is_yaml_file(directory)

    def test_yaml_uppercase(self, tmp_path):
        """Test uppercase YAML extension."""
        yaml_file = tmp_path / "test.YAML"
        yaml_file.write_text("key: value")

        assert not is_yaml_file(yaml_file)

    def test_python_file(self, tmp_path):
        """Test Python file is rejected."""
        py_file = tmp_path / "test.py"
        py_file.write_text("# python")

        assert not is_yaml_file(py_file)


class TestLoadProcessor:
    """Tests for load_processor function."""

    def test_load_valid_processor(self):
        """Test loading valid processor."""
        config = {
            "class": "nornflow.builtins.processors.DefaultNornFlowProcessor",
            "args": {}
        }

        processor = load_processor(config)

        assert hasattr(processor, "task_started")
        assert hasattr(processor, "task_completed")
        assert callable(processor.task_started)

    def test_load_processor_with_args(self):
        """Test loading processor with arguments."""
        mock_processor_class = Mock(return_value=Mock(spec=Processor))

        with patch("nornflow.utils.importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.TestProcessor = mock_processor_class
            mock_import.return_value = mock_module

            config = {
                "class": "test.module.TestProcessor",
                "args": {"arg1": "value1"}
            }

            processor = load_processor(config)

            mock_processor_class.assert_called_once_with(arg1="value1")

    def test_load_processor_missing_class(self):
        """Test error when class is missing."""
        config = {"args": {}}

        with pytest.raises(ProcessorError, match="Missing 'class'"):
            load_processor(config)

    def test_load_processor_invalid_module(self):
        """Test error for invalid module path."""
        config = {"class": "nonexistent.module.Processor"}

        with pytest.raises(ProcessorError, match="Failed to load processor"):
            load_processor(config)

    def test_load_processor_invalid_class(self):
        """Test error for invalid class name."""
        config = {"class": "nornflow.builtins.processors.NonexistentProcessor"}

        with pytest.raises(ProcessorError, match="Failed to load processor"):
            load_processor(config)

    def test_load_processor_no_args(self):
        """Test loading processor without args key."""
        config = {
            "class": "nornflow.builtins.processors.DefaultNornFlowProcessor"
        }

        processor = load_processor(config)

        assert hasattr(processor, "task_started")

    def test_load_processor_instantiation_error(self):
        """Test error during processor instantiation."""
        with patch("nornflow.utils.importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.BadProcessor = Mock(side_effect=ValueError("Bad init"))
            mock_import.return_value = mock_module

            config = {"class": "test.BadProcessor", "args": {}}

            with pytest.raises(ProcessorError, match="Error instantiating processor"):
                load_processor(config)


class TestConvertListsToTuples:
    """Tests for convert_lists_to_tuples function."""

    def test_convert_simple_list(self):
        """Test converting simple list to tuple."""
        input_dict = HashableDict({"myvar": [1, 2, 3]})

        result = convert_lists_to_tuples(input_dict)

        assert result["myvar"] == (1, 2, 3)

    def test_convert_multiple_lists(self):
        """Test converting multiple lists."""
        input_dict = HashableDict({
            "list1": [1, 2],
            "list2": ["a", "b"],
            "not_list": "value"
        })

        result = convert_lists_to_tuples(input_dict)

        assert result["list1"] == (1, 2)
        assert result["list2"] == ("a", "b")
        assert result["not_list"] == "value"

    def test_convert_none_input(self):
        """Test handling None input."""
        result = convert_lists_to_tuples(None)

        assert result is None

    def test_convert_empty_dict(self):
        """Test converting empty dictionary."""
        input_dict = HashableDict({})

        result = convert_lists_to_tuples(input_dict)

        assert result == HashableDict({})

    def test_convert_nested_lists(self):
        """Test that nested lists are not converted."""
        input_dict = HashableDict({"nested": [[1, 2], [3, 4]]})

        result = convert_lists_to_tuples(input_dict)

        assert result["nested"] == ([1, 2], [3, 4])

    def test_convert_mixed_types(self):
        """Test converting dictionary with mixed value types."""
        input_dict = HashableDict({
            "list": [1, 2, 3],
            "string": "value",
            "number": 42,
            "bool": True,
            "none": None
        })

        result = convert_lists_to_tuples(input_dict)

        assert result["list"] == (1, 2, 3)
        assert result["string"] == "value"
        assert result["number"] == 42
        assert result["bool"] is True
        assert result["none"] is None


class TestCheckForJinja2Recursive:
    """Tests for check_for_jinja2_recursive function."""

    def test_valid_string_without_jinja(self):
        """Test string without Jinja2 passes."""
        check_for_jinja2_recursive("plain string", "test")

    def test_detect_jinja_in_string(self):
        """Test Jinja2 in string is detected."""
        with pytest.raises(WorkflowError, match="Jinja2 code found"):
            check_for_jinja2_recursive("{{ variable }}", "test")

    def test_detect_jinja_in_nested_dict(self):
        """Test Jinja2 in nested dict is detected."""
        obj = {"level1": {"level2": "{{ jinja }}"}}

        with pytest.raises(WorkflowError, match="Jinja2 code found"):
            check_for_jinja2_recursive(obj, "test")

    def test_detect_jinja_in_list(self):
        """Test Jinja2 in list is detected."""
        obj = ["plain", "{{ jinja }}", "plain"]

        with pytest.raises(WorkflowError, match="Jinja2 code found"):
            check_for_jinja2_recursive(obj, "test")

    def test_valid_nested_structure(self):
        """Test valid nested structure passes."""
        obj = {
            "key1": "value1",
            "key2": ["item1", "item2"],
            "key3": {"nested": "value"}
        }

        check_for_jinja2_recursive(obj, "test")

    def test_detect_jinja_with_filters(self):
        """Test Jinja2 with filters is detected."""
        with pytest.raises(WorkflowError, match="Jinja2 code found"):
            check_for_jinja2_recursive("{{ var | filter }}", "test")

    def test_valid_curly_braces(self):
        """Test normal curly braces without Jinja2 pass."""
        check_for_jinja2_recursive('{"json": "object"}', "test")

    def test_detect_jinja_statement(self):
        """Test Jinja2 statement is detected."""
        with pytest.raises(WorkflowError, match="Jinja2 code found"):
            check_for_jinja2_recursive("{% for item in items %}{{ item }}{% endfor %}", "test")

    def test_detect_jinja_in_tuple(self):
        """Test Jinja2 in tuple is detected."""
        obj = ("plain", "{{ jinja }}")

        with pytest.raises(WorkflowError, match="Jinja2 code found"):
            check_for_jinja2_recursive(obj, "test")

    def test_valid_with_integers(self):
        """Test integers pass validation."""
        obj = {"numbers": [1, 2, 3, 4, 5]}

        check_for_jinja2_recursive(obj, "test")

    def test_detect_deeply_nested_jinja(self):
        """Test deeply nested Jinja2 is detected."""
        obj = {
            "l1": {
                "l2": {
                    "l3": {
                        "l4": ["value1", "{{ jinja }}"]
                    }
                }
            }
        }

        with pytest.raises(WorkflowError, match="Jinja2 code found"):
            check_for_jinja2_recursive(obj, "test")


class TestFormatVariableValue:
    """Tests for format_variable_value function."""

    def test_format_normal_value(self):
        """Test formatting normal value."""
        result = format_variable_value("myvar", "value")

        assert result == "value"

    def test_format_protected_password(self):
        """Test password is masked."""
        result = format_variable_value("password", "secret123")

        assert result == "********"

    def test_format_protected_token(self):
        """Test token is masked."""
        result = format_variable_value("api_token", "abc123")

        assert result == "********"

    def test_format_protected_secret(self):
        """Test secret is masked."""
        result = format_variable_value("secret_key", "sensitive")

        assert result == "********"

    def test_format_tuple_value(self):
        """Test tuple is formatted as list."""
        result = format_variable_value("myvar", (1, 2, 3))

        assert result == "[1, 2, 3]"

    def test_format_case_insensitive_protection(self):
        """Test protection is case-insensitive."""
        result = format_variable_value("PASSWORD", "secret")

        assert result == "********"

    def test_format_integer(self):
        """Test formatting integer value."""
        result = format_variable_value("count", 42)

        assert result == "42"

    def test_format_boolean(self):
        """Test formatting boolean value."""
        result = format_variable_value("enabled", True)

        assert result == "True"

    def test_format_list_value(self):
        """Test formatting list value."""
        result = format_variable_value("items", ["a", "b", "c"])

        assert result == "['a', 'b', 'c']"

    def test_format_empty_tuple(self):
        """Test formatting empty tuple."""
        result = format_variable_value("empty", ())

        assert result == "[]"

    def test_format_partial_keyword_match(self):
        """Test partial keyword match masks value."""
        result = format_variable_value("my_password_var", "value")

        assert result == "********"


class TestPrintWorkflowOverview:
    """Tests for print_workflow_overview function."""

    @patch("nornflow.utils.Console")
    def test_print_basic_overview(self, mock_console):
        """Test printing basic workflow overview."""
        workflow_model = Mock()
        workflow_model.name = "Test Workflow"
        workflow_model.description = "Test Description"

        print_workflow_overview(
            workflow_model=workflow_model,
            effective_dry_run=False,
            hosts_count=5,
            inventory_filters={},
            workflow_vars={},
            vars={},
            failure_strategy=FailureStrategy.FAIL_FAST
        )

        mock_console.return_value.print.assert_called_once()

    @patch("nornflow.utils.Console")
    def test_print_with_filters(self, mock_console):
        """Test printing overview with inventory filters."""
        workflow_model = Mock()
        workflow_model.name = "Test"
        workflow_model.description = None

        print_workflow_overview(
            workflow_model=workflow_model,
            effective_dry_run=True,
            hosts_count=3,
            inventory_filters={"platform": "ios", "groups": ["core"]},
            workflow_vars={"var1": "value1"},
            vars={"var2": "value2"},
            failure_strategy=None
        )

        mock_console.return_value.print.assert_called_once()

    @patch("nornflow.utils.Console")
    def test_print_with_variables(self, mock_console):
        """Test printing overview with variables."""
        workflow_model = Mock()
        workflow_model.name = "Test"
        workflow_model.description = None

        print_workflow_overview(
            workflow_model=workflow_model,
            effective_dry_run=False,
            hosts_count=1,
            inventory_filters={},
            workflow_vars={"workflow_var": "wf_value"},
            vars={"cli_var": "cli_value"},
            failure_strategy=FailureStrategy.SKIP_FAILED
        )

        mock_console.return_value.print.assert_called_once()

    @patch("nornflow.utils.Console")
    def test_print_no_description(self, mock_console):
        """Test printing overview without description."""
        workflow_model = Mock()
        workflow_model.name = "Simple"
        workflow_model.description = None

        print_workflow_overview(
            workflow_model=workflow_model,
            effective_dry_run=False,
            hosts_count=10,
            inventory_filters={},
            workflow_vars={},
            vars={},
            failure_strategy=FailureStrategy.FAIL_FAST
        )

        mock_console.return_value.print.assert_called_once()

    @patch("nornflow.utils.Console")
    def test_print_with_all_options(self, mock_console):
        """Test printing overview with all options populated."""
        workflow_model = Mock()
        workflow_model.name = "Complete Workflow"
        workflow_model.description = "A comprehensive test"

        print_workflow_overview(
            workflow_model=workflow_model,
            effective_dry_run=True,
            hosts_count=100,
            inventory_filters={
                "platform": "ios",
                "site": "DC1",
                "groups": ["core", "edge"]
            },
            workflow_vars={
                "timeout": 30,
                "retries": 3
            },
            vars={
                "user": "admin",
                "debug": True
            },
            failure_strategy=FailureStrategy.SKIP_FAILED
        )

        mock_console.return_value.print.assert_called_once()