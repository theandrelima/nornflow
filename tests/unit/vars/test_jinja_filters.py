import pytest
import random

class TestJinjaFilters:
    def test_standard_jinja2_filters(self, setup_manager):
        """Test standard Jinja2 filters."""
        # Test upper
        result = setup_manager.resolve_string("{{ 'test' | upper }}", "test_device")
        assert result == "TEST"

        # Test lower
        result = setup_manager.resolve_string("{{ 'TEST' | lower }}", "test_device")
        assert result == "test"

        # Test default
        result = setup_manager.resolve_string("{{ missing_var | default('default_value') }}", "test_device")
        assert result == "default_value"

        # Test length
        setup_manager.set_runtime_variable("my_list", [1, 2, 3, 4, 5], "test_device")
        result = setup_manager.resolve_string("Length: {{ my_list | length }}", "test_device")
        assert result == "Length: 5"

        # Test join
        setup_manager.set_runtime_variable("my_list", ["a", "b", "c"], "test_device")
        result = setup_manager.resolve_string("{{ my_list | join('-') }}", "test_device")
        assert result == "a-b-c"

    def test_list_operation_filters(self, setup_manager):
        """Test list operation filters from NornFlow."""
        # Test flatten_list - returns a list, which gets stringified
        setup_manager.set_runtime_variable("nested_list", [[1, 2], [3, 4], [5]], "test_device")
        result = setup_manager.resolve_string("{{ nested_list | flatten_list }}", "test_device")
        # The filter returns a list, which Jinja2 converts to string
        assert result == "[1, 2, 3, 4, 5]"

        # Test unique_list
        setup_manager.set_runtime_variable("duplicated_list", [1, 2, 2, 3, 1, 4], "test_device")
        result = setup_manager.resolve_string("{{ duplicated_list | unique_list }}", "test_device")
        assert result == "[1, 2, 3, 4]"

        # Test chunk_list
        setup_manager.set_runtime_variable("long_list", [1, 2, 3, 4, 5], "test_device")
        result = setup_manager.resolve_string("{{ long_list | chunk_list(2) }}", "test_device")
        assert result == "[[1, 2], [3, 4], [5]]"

    def test_string_manipulation_filters(self, setup_manager):
        """Test string manipulation filters."""
        # Test regex_replace
        result = setup_manager.resolve_string(
            "{{ 'Router-NYC-001' | regex_replace('\\d+', 'XXX') }}", "test_device"
        )
        assert result == "Router-NYC-XXX"

        # Test to_snake_case
        result = setup_manager.resolve_string("{{ 'MyVariableName' | to_snake_case }}", "test_device")
        assert result == "my_variable_name"

        # Test to_kebab_case
        result = setup_manager.resolve_string("{{ 'MyVariableName' | to_kebab_case }}", "test_device")
        assert result == "my-variable-name"

    def test_data_operation_filters(self, setup_manager):
        """Test data operation filters."""
        # Test json_query (jmespath)
        interfaces = [{"name": "Gi0/1", "vlan": 100}, {"name": "Gi0/2", "vlan": 200}]
        setup_manager.set_runtime_variable("interfaces", interfaces, "test_device")

        result = setup_manager.resolve_string("{{ interfaces | json_query('[*].name') }}", "test_device")
        # json_query returns a list which gets stringified
        assert result == "['Gi0/1', 'Gi0/2']"

        # Test deep_merge
        defaults = {"ntp": {"server": "10.0.0.1", "source": "Lo0"}, "snmp": {"community": "public"}}
        custom = {"ntp": {"server": "10.0.0.2"}}
        setup_manager.set_runtime_variable("defaults", defaults, "test_device")
        setup_manager.set_runtime_variable("custom", custom, "test_device")

        result = setup_manager.resolve_string("{{ defaults | deep_merge(custom) }}", "test_device")
        # Parse the stringified result back to dict for verification
        result_dict = eval(result.replace("'", '"').replace('u"', '"'))
        assert result_dict["ntp"]["server"] == "10.0.0.2"
        assert result_dict["ntp"]["source"] == "Lo0"
        assert result_dict["snmp"]["community"] == "public"

    def test_utility_filters(self, setup_manager):
        """Test utility filters."""
        # Test random_choice with a seed for predictability
        

        random.seed(42)  # Set seed for predictable results

        setup_manager.set_runtime_variable("options", ["server1", "server2", "server3"], "test_device")
        result = setup_manager.resolve_string("{{ options | random_choice }}", "test_device")
        assert result in ["server1", "server2", "server3"]

    def test_python_wrapper_filters(self, setup_manager):
        """Test Python wrapper filters."""
        # Test enumerate - returns a list of tuples which gets stringified
        setup_manager.set_runtime_variable("items", ["a", "b", "c"], "test_device")
        result = setup_manager.resolve_string("{{ items | enumerate }}", "test_device")
        assert result == "[(0, 'a'), (1, 'b'), (2, 'c')]"

        # Test enumerate with start
        result = setup_manager.resolve_string("{{ items | enumerate(1) }}", "test_device")
        assert result == "[(1, 'a'), (2, 'b'), (3, 'c')]"

        # Test zip
        setup_manager.set_runtime_variable("keys", ["a", "b", "c"], "test_device")
        setup_manager.set_runtime_variable("values", [1, 2, 3], "test_device")
        result = setup_manager.resolve_string("{{ keys | zip(values) }}", "test_device")
        assert result == "[('a', 1), ('b', 2), ('c', 3)]"

        # Test range
        result = setup_manager.resolve_string("{{ 5 | range }}", "test_device")
        assert result == "[0, 1, 2, 3, 4]"

        # Test divmod
        result = setup_manager.resolve_string("{{ 10 | divmod(3) }}", "test_device")
        assert result == "(3, 1)"

        # Test splitx
        result = setup_manager.resolve_string("{{ 'a,b,c,d' | splitx(',', 2) }}", "test_device")
        assert result == "['a', 'b', 'c,d']"


class TestIsSetFilter:
    """Test suite for the is_set Jinja2 filter.

    This filter checks if a variable exists and is not None in the Jinja2 context.
    It supports nested paths using dot notation (e.g., 'my_var.nested.key') and
    host namespace access (e.g., 'host.data.key').
    """

    def test_basic_variable_exists(self, setup_manager):
        """Test that is_set returns True for existing non-None variables."""
        setup_manager.set_runtime_variable("my_var", "value", "test_device")
        result = setup_manager.resolve_string("{{ 'my_var' | is_set }}", "test_device")
        assert result == "True"

    def test_basic_variable_does_not_exist(self, setup_manager):
        """Test that is_set returns False for undefined variables."""
        result = setup_manager.resolve_string("{{ 'nonexistent' | is_set }}", "test_device")
        assert result == "False"

    def test_variable_is_none(self, setup_manager):
        """Test that is_set returns False for variables set to None."""
        setup_manager.set_runtime_variable("my_var", None, "test_device")
        result = setup_manager.resolve_string("{{ 'my_var' | is_set }}", "test_device")
        assert result == "False"

    def test_nested_path_exists(self, setup_manager):
        """Test nested path resolution for existing paths."""
        setup_manager.set_runtime_variable("my_var", {"nested": {"key": "value"}}, "test_device")
        result = setup_manager.resolve_string("{{ 'my_var.nested.key' | is_set }}", "test_device")
        assert result == "True"

    def test_nested_path_partial_exists(self, setup_manager):
        """Test that is_set returns False if any part of the nested path is missing."""
        setup_manager.set_runtime_variable("my_var", {"nested": {}}, "test_device")
        result = setup_manager.resolve_string("{{ 'my_var.nested.key' | is_set }}", "test_device")
        assert result == "False"

    def test_nested_path_root_missing(self, setup_manager):
        """Test that is_set returns False if the root of the nested path is missing."""
        result = setup_manager.resolve_string("{{ 'my_var.nested.key' | is_set }}", "test_device")
        assert result == "False"

    def test_nested_path_with_none_intermediate(self, setup_manager):
        """Test that is_set returns False if an intermediate value in the path is None."""
        setup_manager.set_runtime_variable("my_var", {"nested": None}, "test_device")
        result = setup_manager.resolve_string("{{ 'my_var.nested.key' | is_set }}", "test_device")
        assert result == "False"

    def test_host_namespace_runtime_variable_collision(self, setup_manager):
        """Test that a runtime variable named 'host' does not satisfy host namespace lookups."""
        # Simulate a runtime variable that collides with the host namespace name
        setup_manager.set_runtime_variable("host", {"data": {"key": "value"}}, "test_device")
        result = setup_manager.resolve_string("{{ 'host.data.key' | is_set }}", "test_device")
        assert result == "False"  # Filter resolves "host" as the runtime variable, so host namespace traversal fails

    def test_host_namespace_missing_host(self, setup_manager):
        """Test that is_set returns False if host is not in context."""
        result = setup_manager.resolve_string("{{ 'host.data.key' | is_set }}", "test_device")
        assert result == "False"

    def test_host_namespace_none_host(self, setup_manager):
        """Test that is_set returns False if host is None."""
        setup_manager.set_runtime_variable("host", None, "test_device")
        result = setup_manager.resolve_string("{{ 'host.data.key' | is_set }}", "test_device")
        assert result == "False"

    def test_host_namespace_missing_data(self, setup_manager):
        """Test that is_set returns False if host.data is missing."""
        setup_manager.set_runtime_variable("host", {}, "test_device")
        result = setup_manager.resolve_string("{{ 'host.data.key' | is_set }}", "test_device")
        assert result == "False"

    def test_host_namespace_nested_missing(self, setup_manager):
        """Test nested host data access when key is missing."""
        setup_manager.set_runtime_variable("host", {"data": {"key": {}}}, "test_device")
        result = setup_manager.resolve_string("{{ 'host.data.key.subkey' | is_set }}", "test_device")
        assert result == "False"

    def test_empty_path(self, setup_manager):
        """Test that is_set returns False for empty path strings."""
        result = setup_manager.resolve_string("{{ '' | is_set }}", "test_device")
        assert result == "False"

    def test_none_path(self, setup_manager):
        """Test that is_set returns False for variables set to None."""
        setup_manager.set_runtime_variable("path", None, "test_device")
        result = setup_manager.resolve_string("{{ 'path' | is_set }}", "test_device")
        assert result == "False"

    def test_variable_set_to_non_string(self, setup_manager):
        """Test that is_set returns True for variables set to non-string values."""
        setup_manager.set_runtime_variable("path", 123, "test_device")
        result = setup_manager.resolve_string("{{ 'path' | is_set }}", "test_device")
        assert result == "True"

    def test_jinja2_undefined_variable(self, setup_manager):
        """Test that is_set returns False for Jinja2 Undefined objects."""
        # Undefined variables are not set, so test missing var
        result = setup_manager.resolve_string("{{ 'undefined_var' | is_set }}", "test_device")
        assert result == "False"

    def test_context_resolve_exception(self, setup_manager):
        """Test that is_set returns False if context.resolve raises an exception."""
        # Hard to simulate, but test with invalid path
        result = setup_manager.resolve_string("{{ 'invalid.path' | is_set }}", "test_device")
        assert result == "False"

    def test_workflow_variable_exists(self, setup_manager):
        """Test is_set with workflow-level variables."""
        # Assuming workflow vars are set in manager
        # For test, set as runtime
        setup_manager.set_runtime_variable("workflow_var", "set", "test_device")
        result = setup_manager.resolve_string("{{ 'workflow_var' | is_set }}", "test_device")
        assert result == "True"

    def test_runtime_variable_override(self, setup_manager):
        """Test is_set with runtime variables overriding others."""
        setup_manager.set_runtime_variable("override_var", "runtime", "test_device")
        result = setup_manager.resolve_string("{{ 'override_var' | is_set }}", "test_device")
        assert result == "True"

    def test_nested_runtime_variable(self, setup_manager):
        """Test nested path in runtime variables."""
        setup_manager.set_runtime_variable("nested_var", {"level1": {"level2": "value"}}, "test_device")
        result = setup_manager.resolve_string("{{ 'nested_var.level1.level2' | is_set }}", "test_device")
        assert result == "True"

    def test_zero_and_false_values(self, setup_manager):
        """Test that zero, false, and empty strings are considered set."""
        setup_manager.set_runtime_variable("zero", 0, "test_device")
        setup_manager.set_runtime_variable("false", False, "test_device")
        setup_manager.set_runtime_variable("empty", "", "test_device")
        result_zero = setup_manager.resolve_string("{{ 'zero' | is_set }}", "test_device")
        result_false = setup_manager.resolve_string("{{ 'false' | is_set }}", "test_device")
        result_empty = setup_manager.resolve_string("{{ 'empty' | is_set }}", "test_device")
        assert result_zero == "True"
        assert result_false == "True"
        assert result_empty == "True"

    def test_is_set_with_list_index(self, setup_manager):
        """Test is_set with list indexing."""
        setup_manager.set_runtime_variable("my_list", [1, 2, 3], "test_device")
        result = setup_manager.resolve_string("{{ 'my_list[0]' | is_set }}", "test_device")
        assert result == "False"  # is_set doesn't support indexing, treats as string

    def test_is_set_with_special_characters(self, setup_manager):
        """Test is_set with variable names containing special characters."""
        setup_manager.set_runtime_variable("var-with-dash", "value", "test_device")
        result = setup_manager.resolve_string("{{ 'var-with-dash' | is_set }}", "test_device")
        assert result == "True"

    def test_is_set_case_sensitivity(self, setup_manager):
        """Test is_set is case sensitive for variable names."""
        setup_manager.set_runtime_variable("MyVar", "value", "test_device")
        result = setup_manager.resolve_string("{{ 'myvar' | is_set }}", "test_device")
        assert result == "False"

    def test_host_namespace_exists(self, setup_manager):
        """Test host namespace access when host data exists."""
        result = setup_manager.resolve_string("{{ 'host.name' | is_set }}", "test_device")
        assert result == "True"

    def test_host_namespace_data_exists(self, setup_manager):
        """Test host namespace for existing host data."""
        result = setup_manager.resolve_string("{{ 'host.data.location.building' | is_set }}", "test_device")
        assert result == "True"

    def test_host_namespace_data_missing(self, setup_manager):
        """Test host namespace for missing host data key."""
        result = setup_manager.resolve_string("{{ 'host.data.missing' | is_set }}", "test_device")
        assert result == "False"

    def test_is_set_with_numeric_path(self, setup_manager):
        """Test is_set with path containing numbers."""
        setup_manager.set_runtime_variable("var1", {"2key": "value"}, "test_device")
        result = setup_manager.resolve_string("{{ 'var1.2key' | is_set }}", "test_device")
        assert result == "True"

    def test_is_set_with_underscore_path(self, setup_manager):
        """Test is_set with path containing underscores."""
        setup_manager.set_runtime_variable("my_var", {"sub_key": "value"}, "test_device")
        result = setup_manager.resolve_string("{{ 'my_var.sub_key' | is_set }}", "test_device")
        assert result == "True"


class TestCustomFilters:
    """Test suite for additional custom Jinja2 filters not covered elsewhere."""

    def test_regex_replace_basic(self, setup_manager):
        """Test basic regex replacement."""
        result = setup_manager.resolve_string("{{ 'abc123def' | regex_replace('123', 'XYZ') }}", "test_device")
        assert result == "abcXYZdef"

    def test_regex_replace_no_match(self, setup_manager):
        """Test regex replacement when pattern doesn't match."""
        result = setup_manager.resolve_string("{{ 'abcdef' | regex_replace('123', 'XYZ') }}", "test_device")
        assert result == "abcdef"

    def test_to_snake_case_basic(self, setup_manager):
        """Test basic snake_case conversion."""
        result = setup_manager.resolve_string("{{ 'MyVariableName' | to_snake_case }}", "test_device")
        assert result == "my_variable_name"

    def test_to_snake_case_already_snake(self, setup_manager):
        """Test snake_case conversion on already snake_case string."""
        result = setup_manager.resolve_string("{{ 'already_snake' | to_snake_case }}", "test_device")
        assert result == "already_snake"

    def test_to_kebab_case_basic(self, setup_manager):
        """Test basic kebab-case conversion."""
        result = setup_manager.resolve_string("{{ 'MyVariableName' | to_kebab_case }}", "test_device")
        assert result == "my-variable-name"

    def test_to_kebab_case_already_kebab(self, setup_manager):
        """Test kebab-case conversion on already kebab-case string."""
        result = setup_manager.resolve_string("{{ 'already-kebab' | to_kebab_case }}", "test_device")
        assert result == "already-kebab"

    def test_json_query_basic(self, setup_manager):
        """Test basic JMESPath query."""
        data = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}
        setup_manager.set_runtime_variable("data", data, "test_device")
        result = setup_manager.resolve_string("{{ data | json_query('users[*].name') }}", "test_device")
        assert result == "['Alice', 'Bob']"

    def test_json_query_invalid_query(self, setup_manager):
        """Test JMESPath query with invalid syntax - raises TemplateError."""
        data = {"key": "value"}
        setup_manager.set_runtime_variable("data", data, "test_device")
        with pytest.raises(Exception):  # Expect TemplateError due to uncaught exception
            setup_manager.resolve_string("{{ data | json_query('invalid[') }}", "test_device")

    def test_deep_merge_basic(self, setup_manager):
        """Test basic deep merge of dictionaries."""
        dict1 = {"a": 1, "b": {"c": 2}}
        dict2 = {"b": {"d": 3}, "e": 4}
        setup_manager.set_runtime_variable("dict1", dict1, "test_device")
        setup_manager.set_runtime_variable("dict2", dict2, "test_device")
        result = setup_manager.resolve_string("{{ dict1 | deep_merge(dict2) }}", "test_device")
        expected = "{'a': 1, 'b': {'c': 2, 'd': 3}, 'e': 4}"
        assert result == expected

    def test_deep_merge_empty_dicts(self, setup_manager):
        """Test deep merge with empty dictionaries."""
        dict1 = {}
        dict2 = {"a": 1}
        setup_manager.set_runtime_variable("dict1", dict1, "test_device")
        setup_manager.set_runtime_variable("dict2", dict2, "test_device")
        result = setup_manager.resolve_string("{{ dict1 | deep_merge(dict2) }}", "test_device")
        assert result == "{'a': 1}"

    def test_random_choice_basic(self, setup_manager):
        """Test random choice from list."""
        random.seed(42)  # For predictable results
        choices = ["a", "b", "c"]
        setup_manager.set_runtime_variable("choices", choices, "test_device")
        result = setup_manager.resolve_string("{{ choices | random_choice }}", "test_device")
        assert result in choices

    def test_random_choice_empty_list(self, setup_manager):
        """Test random choice from empty list."""
        setup_manager.set_runtime_variable("empty_list", [], "test_device")
        result = setup_manager.resolve_string("{{ empty_list | random_choice }}", "test_device")
        assert result == "None"

    def test_flatten_list_empty(self, setup_manager):
        """Test flatten_list with empty list."""
        setup_manager.set_runtime_variable("empty", [], "test_device")
        result = setup_manager.resolve_string("{{ empty | flatten_list }}", "test_device")
        assert result == "[]"

    def test_unique_list_empty(self, setup_manager):
        """Test unique_list with empty list."""
        setup_manager.set_runtime_variable("empty", [], "test_device")
        result = setup_manager.resolve_string("{{ empty | unique_list }}", "test_device")
        assert result == "[]"

    def test_chunk_list_single_element(self, setup_manager):
        """Test chunk_list with single element."""
        setup_manager.set_runtime_variable("single", [1], "test_device")
        result = setup_manager.resolve_string("{{ single | chunk_list(2) }}", "test_device")
        assert result == "[[1]]"

    def test_to_snake_case_numbers(self, setup_manager):
        """Test to_snake_case with numbers."""
        result = setup_manager.resolve_string("{{ 'Var123Name' | to_snake_case }}", "test_device")
        assert result == "var123_name"

    def test_json_query_empty_data(self, setup_manager):
        """Test json_query with empty data."""
        setup_manager.set_runtime_variable("empty_data", {}, "test_device")
        result = setup_manager.resolve_string("{{ empty_data | json_query('key') }}", "test_device")
        assert result == "None"

    def test_deep_merge_overwrite(self, setup_manager):
        """Test deep merge overwriting values."""
        dict1 = {"a": 1}
        dict2 = {"a": 2}
        setup_manager.set_runtime_variable("dict1", dict1, "test_device")
        setup_manager.set_runtime_variable("dict2", dict2, "test_device")
        result = setup_manager.resolve_string("{{ dict1 | deep_merge(dict2) }}", "test_device")
        assert result == "{'a': 2}"

    def test_random_choice_single_item(self, setup_manager):
        """Test random_choice with single item."""
        setup_manager.set_runtime_variable("single", ["only"], "test_device")
        result = setup_manager.resolve_string("{{ single | random_choice }}", "test_device")
        assert result == "only"

    def test_enumerate_empty(self, setup_manager):
        """Test enumerate with empty list."""
        setup_manager.set_runtime_variable("empty", [], "test_device")
        result = setup_manager.resolve_string("{{ empty | enumerate }}", "test_device")
        assert result == "[]"

    def test_zip_different_lengths(self, setup_manager):
        """Test zip with lists of different lengths."""
        setup_manager.set_runtime_variable("short", ["a"], "test_device")
        setup_manager.set_runtime_variable("long", [1, 2], "test_device")
        result = setup_manager.resolve_string("{{ short | zip(long) }}", "test_device")
        assert result == "[('a', 1)]"

    def test_range_zero(self, setup_manager):
        """Test range with zero."""
        result = setup_manager.resolve_string("{{ 0 | range }}", "test_device")
        assert result == "[]"

    def test_divmod_by_zero(self, setup_manager):
        """Test divmod by zero - raises ZeroDivisionError."""
        with pytest.raises(Exception):  # Expect ZeroDivisionError or TemplateError
            setup_manager.resolve_string("{{ 10 | divmod(0) }}", "test_device")

    def test_splitx_maxsplit_zero(self, setup_manager):
        """Test splitx with maxsplit 0."""
        result = setup_manager.resolve_string("{{ 'a,b,c' | splitx(',', 0) }}", "test_device")
        assert result == "['a,b,c']"

    def test_regex_replace_with_groups(self, setup_manager):
        """Test regex_replace with capture groups."""
        result = setup_manager.resolve_string("{{ 'abc123def' | regex_replace('(\\d+)', '[\\1]') }}", "test_device")
        assert result == "abc[\x01]def"

    def test_to_snake_case_mixed_case(self, setup_manager):
        """Test to_snake_case with mixed case and numbers."""
        result = setup_manager.resolve_string("{{ 'XMLHttpRequest2' | to_snake_case }}", "test_device")
        assert result == "xml_http_request2"

    def test_to_kebab_case_mixed_case(self, setup_manager):
        """Test to_kebab_case with mixed case."""
        result = setup_manager.resolve_string("{{ 'XMLHttpRequest' | to_kebab_case }}", "test_device")
        assert result == "xml-http-request"

    def test_json_query_nested(self, setup_manager):
        """Test json_query with nested queries."""
        data = {"network": {"devices": [{"ip": "192.168.1.1"}, {"ip": "192.168.1.2"}]}}
        setup_manager.set_runtime_variable("data", data, "test_device")
        result = setup_manager.resolve_string("{{ data | json_query('network.devices[*].ip') }}", "test_device")
        assert result == "['192.168.1.1', '192.168.1.2']"

    def test_deep_merge_nested_overwrite(self, setup_manager):
        """Test deep merge with nested overwrite."""
        dict1 = {"a": {"b": 1, "c": 2}}
        dict2 = {"a": {"b": 3}}
        setup_manager.set_runtime_variable("dict1", dict1, "test_device")
        setup_manager.set_runtime_variable("dict2", dict2, "test_device")
        result = setup_manager.resolve_string("{{ dict1 | deep_merge(dict2) }}", "test_device")
        expected = "{'a': {'b': 3, 'c': 2}}"
        assert result == expected

    def test_random_choice_with_seed(self, setup_manager):
        """Test random_choice predictability with seed."""
        
        random.seed(123)
        choices = ["x", "y", "z"]
        setup_manager.set_runtime_variable("choices", choices, "test_device")
        result = setup_manager.resolve_string("{{ choices | random_choice }}", "test_device")
        assert result in choices

    def test_flatten_list_nested(self, setup_manager):
        """Test flatten_list with deeply nested lists."""
        setup_manager.set_runtime_variable("nested", [[[1, 2]], [3, [4, 5]]], "test_device")
        result = setup_manager.resolve_string("{{ nested | flatten_list }}", "test_device")
        assert result == "[1, 2, 3, 4, 5]"

    def test_unique_list_with_dicts(self, setup_manager):
        """Test unique_list with unhashable types like dicts."""
        setup_manager.set_runtime_variable("list_with_dicts", [{"a": 1}, {"a": 1}, {"b": 2}], "test_device")
        with pytest.raises(Exception):
            setup_manager.resolve_string("{{ list_with_dicts | unique_list }}", "test_device")

    def test_chunk_list_chunk_size_one(self, setup_manager):
        """Test chunk_list with chunk size 1."""
        setup_manager.set_runtime_variable("list", [1, 2, 3], "test_device")
        result = setup_manager.resolve_string("{{ list | chunk_list(1) }}", "test_device")
        assert result == "[[1], [2], [3]]"

    def test_enumerate_with_negative_start(self, setup_manager):
        """Test enumerate with negative start."""
        setup_manager.set_runtime_variable("items", ["a", "b"], "test_device")
        result = setup_manager.resolve_string("{{ items | enumerate(-1) }}", "test_device")
        assert result == "[(-1, 'a'), (0, 'b')]"

    def test_zip_empty_lists(self, setup_manager):
        """Test zip with empty lists."""
        setup_manager.set_runtime_variable("empty1", [], "test_device")
        setup_manager.set_runtime_variable("empty2", [], "test_device")
        result = setup_manager.resolve_string("{{ empty1 | zip(empty2) }}", "test_device")
        assert result == "[]"

    def test_range_negative(self, setup_manager):
        """Test range with negative number."""
        result = setup_manager.resolve_string("{{ -3 | range }}", "test_device")
        assert result == "[]"

    def test_divmod_negative_divisor(self, setup_manager):
        """Test divmod with negative divisor."""
        result = setup_manager.resolve_string("{{ 10 | divmod(-3) }}", "test_device")
        assert result == "(-4, -2)"

    def test_splitx_negative_maxsplit(self, setup_manager):
        """Test splitx with negative maxsplit."""
        result = setup_manager.resolve_string("{{ 'a,b,c' | splitx(',', -1) }}", "test_device")
        assert result == "['a', 'b', 'c']"

    def test_json_query_single_value(self, setup_manager):
        """Test json_query returning a single value."""
        data = {"config": {"timeout": 30}}
        setup_manager.set_runtime_variable("data", data, "test_device")
        result = setup_manager.resolve_string("{{ data | json_query('config.timeout') }}", "test_device")
        assert result == "30"

    def test_deep_merge_with_lists(self, setup_manager):
        """Test deep_merge with lists (should not merge lists)."""
        dict1 = {"a": [1, 2]}
        dict2 = {"a": [3, 4]}
        setup_manager.set_runtime_variable("dict1", dict1, "test_device")
        setup_manager.set_runtime_variable("dict2", dict2, "test_device")
        result = setup_manager.resolve_string("{{ dict1 | deep_merge(dict2) }}", "test_device")
        expected = "{'a': [3, 4]}"  # Overwrites list
        assert result == expected

    def test_random_choice_type_error(self, setup_manager):
        """Test random_choice with non-list input."""
        setup_manager.set_runtime_variable("not_list", "string", "test_device")
        result = setup_manager.resolve_string("{{ not_list | random_choice }}", "test_device")
        assert result in "string"

    def test_flatten_list_mixed_types(self, setup_manager):
        """Test flatten_list with mixed types."""
        setup_manager.set_runtime_variable("mixed", [[1, 2], "string", [3]], "test_device")
        result = setup_manager.resolve_string("{{ mixed | flatten_list }}", "test_device")
        assert result == "[1, 2, 'string', 3]"

    def test_unique_list_mixed_types(self, setup_manager):
        """Test unique_list with mixed types."""
        setup_manager.set_runtime_variable("mixed", [1, "1", 1, 2], "test_device")
        result = setup_manager.resolve_string("{{ mixed | unique_list }}", "test_device")
        assert result == "[1, '1', 2]"

    def test_chunk_list_large_chunk(self, setup_manager):
        """Test chunk_list with chunk size larger than list."""
        setup_manager.set_runtime_variable("small", [1, 2], "test_device")
        result = setup_manager.resolve_string("{{ small | chunk_list(5) }}", "test_device")
        assert result == "[[1, 2]]"

    def test_enumerate_with_large_start(self, setup_manager):
        """Test enumerate with large start value."""
        setup_manager.set_runtime_variable("items", ["a"], "test_device")
        result = setup_manager.resolve_string("{{ items | enumerate(100) }}", "test_device")
        assert result == "[(100, 'a')]"

    def test_zip_three_lists(self, setup_manager):
        """Test zip with three lists."""
        setup_manager.set_runtime_variable("a", [1, 2], "test_device")
        setup_manager.set_runtime_variable("b", ["x", "y"], "test_device")
        setup_manager.set_runtime_variable("c", [True, False], "test_device")
        result = setup_manager.resolve_string("{{ a | zip(b, c) }}", "test_device")
        assert result == "[(1, 'x', True), (2, 'y', False)]"

    def test_range_large_number(self, setup_manager):
        """Test range with large number (but limit for test)."""
        result = setup_manager.resolve_string("{{ 10 | range }}", "test_device")
        assert result == "[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]"

    def test_divmod_large_numbers(self, setup_manager):
        """Test divmod with large numbers."""
        result = setup_manager.resolve_string("{{ 100 | divmod(7) }}", "test_device")
        assert result == "(14, 2)"

    def test_splitx_empty_string(self, setup_manager):
        """Test splitx with empty string."""
        result = setup_manager.resolve_string("{{ '' | splitx(',', 2) }}", "test_device")
        assert result == "['']"

    def test_regex_replace_empty_pattern(self, setup_manager):
        """Test regex_replace with empty pattern."""
        result = setup_manager.resolve_string("{{ 'abc' | regex_replace('', 'X') }}", "test_device")
        assert result == "XaXbXcX"

    def test_to_snake_case_empty_string(self, setup_manager):
        """Test to_snake_case with empty string."""
        result = setup_manager.resolve_string("{{ '' | to_snake_case }}", "test_device")
        assert result == ""

    def test_to_kebab_case_empty_string(self, setup_manager):
        """Test to_kebab_case with empty string."""
        result = setup_manager.resolve_string("{{ '' | to_kebab_case }}", "test_device")
        assert result == ""

    def test_json_query_no_match(self, setup_manager):
        """Test json_query with query that matches nothing."""
        data = {"users": []}
        setup_manager.set_runtime_variable("data", data, "test_device")
        result = setup_manager.resolve_string("{{ data | json_query('users[*].name') }}", "test_device")
        assert result == "[]"

    def test_deep_merge_self_merge(self, setup_manager):
        """Test deep_merge with same dict."""
        dict1 = {"a": 1}
        setup_manager.set_runtime_variable("dict1", dict1, "test_device")
        result = setup_manager.resolve_string("{{ dict1 | deep_merge(dict1) }}", "test_device")
        expected = "{'a': 1}"
        assert result == expected

    def test_is_set_with_none_value(self, setup_manager):
        """Test is_set with None passed directly (not as string)."""
        result = setup_manager.resolve_string("{{ None | is_set }}", "test_device")
        assert result == "False"

    def test_is_set_with_int_value(self, setup_manager):
        """Test is_set with int passed directly."""
        result = setup_manager.resolve_string("{{ 123 | is_set }}", "test_device")
        assert result == "False"

    def test_deep_merge_multiple_levels(self, setup_manager):
        """Test deep merge with multiple nesting levels."""
        dict1 = {"a": {"b": {"c": 1}}}
        dict2 = {"a": {"b": {"d": 2}, "e": 3}}
        setup_manager.set_runtime_variable("dict1", dict1, "test_device")
        setup_manager.set_runtime_variable("dict2", dict2, "test_device")
        result = setup_manager.resolve_string("{{ dict1 | deep_merge(dict2) }}", "test_device")
        expected = "{'a': {'b': {'c': 1, 'd': 2}, 'e': 3}}"
        assert result == expected

    def test_json_query_with_null(self, setup_manager):
        """Test json_query with null values."""
        data = {"key": None}
        setup_manager.set_runtime_variable("data", data, "test_device")
        result = setup_manager.resolve_string("{{ data | json_query('key') }}", "test_device")
        assert result == "None"

    def test_regex_replace_case_sensitive(self, setup_manager):
        """Test regex_replace is case sensitive by default."""
        result = setup_manager.resolve_string("{{ 'ABC' | regex_replace('abc', 'XYZ') }}", "test_device")
        assert result == "ABC"

    def test_to_snake_case_consecutive_caps(self, setup_manager):
        """Test to_snake_case with consecutive capital letters."""
        result = setup_manager.resolve_string("{{ 'XMLParser' | to_snake_case }}", "test_device")
        assert result == "xml_parser"

    def test_to_kebab_case_consecutive_caps(self, setup_manager):
        """Test to_kebab_case with consecutive capital letters."""
        result = setup_manager.resolve_string("{{ 'XMLParser' | to_kebab_case }}", "test_device")
        assert result == "xml-parser"

    def test_chunk_list_zero_chunk_size(self, setup_manager):
        """Test chunk_list with chunk size 0."""
        setup_manager.set_runtime_variable("list", [1, 2, 3], "test_device")
        with pytest.raises(Exception):  # Expect ZeroDivisionError or similar
            setup_manager.resolve_string("{{ list | chunk_list(0) }}", "test_device")

    def test_enumerate_with_zero_start(self, setup_manager):
        """Test enumerate with zero start."""
        setup_manager.set_runtime_variable("items", ["a", "b"], "test_device")
        result = setup_manager.resolve_string("{{ items | enumerate(0) }}", "test_device")
        assert result == "[(0, 'a'), (1, 'b')]"

    def test_zip_single_list(self, setup_manager):
        """Test zip with single list."""
        setup_manager.set_runtime_variable("single", ["a", "b"], "test_device")
        result = setup_manager.resolve_string("{{ single | zip }}", "test_device")
        assert result == "[('a',), ('b',)]"

    def test_range_one(self, setup_manager):
        """Test range with 1."""
        result = setup_manager.resolve_string("{{ 1 | range }}", "test_device")
        assert result == "[0]"

    def test_divmod_exact(self, setup_manager):
        """Test divmod with exact division."""
        result = setup_manager.resolve_string("{{ 10 | divmod(5) }}", "test_device")
        assert result == "(2, 0)"

    def test_splitx_no_separator(self, setup_manager):
        """Test splitx with separator not in string."""
        result = setup_manager.resolve_string("{{ 'abc' | splitx(',', 2) }}", "test_device")
        assert result == "['abc']"

    def test_deep_merge_no_overlap(self, setup_manager):
        """Test deep_merge with no overlapping keys."""
        dict1 = {"a": 1}
        dict2 = {"b": 2}
        setup_manager.set_runtime_variable("dict1", dict1, "test_device")
        setup_manager.set_runtime_variable("dict2", dict2, "test_device")
        result = setup_manager.resolve_string("{{ dict1 | deep_merge(dict2) }}", "test_device")
        expected = "{'a': 1, 'b': 2}"
        assert result == expected

    def test_is_set_with_deeply_nested_none(self, setup_manager):
        """Test is_set with deeply nested None values."""
        setup_manager.set_runtime_variable("deep", {"a": {"b": None}}, "test_device")
        result = setup_manager.resolve_string("{{ 'deep.a.b.c' | is_set }}", "test_device")
        assert result == "False"

    def test_regex_replace_multiple_groups(self, setup_manager):
        """Test regex_replace with multiple capture groups."""
        result = setup_manager.resolve_string("{{ 'a1b2c' | regex_replace('(\\w)(\\d)', '\\2\\1') }}", "test_device")
        assert result == '\x02\x01\x02\x01c'

    def test_flatten_list_with_tuples(self, setup_manager):
        """Test flatten_list with tuples."""
        setup_manager.set_runtime_variable("tuples", [(1, 2), [3, 4]], "test_device")
        result = setup_manager.resolve_string("{{ tuples | flatten_list }}", "test_device")
        assert result == "[(1, 2), 3, 4]"

    def test_unique_list_with_tuples(self, setup_manager):
        """Test unique_list with tuples."""
        setup_manager.set_runtime_variable("tuples", [(1, 2), (1, 2), (3, 4)], "test_device")
        result = setup_manager.resolve_string("{{ tuples | unique_list }}", "test_device")
        assert result == "[(1, 2), (3, 4)]"

    def test_chunk_list_empty_list(self, setup_manager):
        """Test chunk_list with empty list."""
        setup_manager.set_runtime_variable("empty", [], "test_device")
        result = setup_manager.resolve_string("{{ empty | chunk_list(2) }}", "test_device")
        assert result == "[]"

    def test_json_query_with_array_index(self, setup_manager):
        """Test json_query with array indexing."""
        data = {"items": ["a", "b", "c"]}
        setup_manager.set_runtime_variable("data", data, "test_device")
        result = setup_manager.resolve_string("{{ data | json_query('items[1]') }}", "test_device")
        assert result == "b"

    def test_deep_merge_with_none_values(self, setup_manager):
        """Test deep_merge with None values."""
        dict1 = {"a": None}
        dict2 = {"a": 1}
        setup_manager.set_runtime_variable("dict1", dict1, "test_device")
        setup_manager.set_runtime_variable("dict2", dict2, "test_device")
        result = setup_manager.resolve_string("{{ dict1 | deep_merge(dict2) }}", "test_device")
        expected = "{'a': 1}"
        assert result == expected

    def test_sorted_basic(self, setup_manager):
        """Test sorted filter."""
        setup_manager.set_runtime_variable("unsorted", [3, 1, 4, 1, 5], "test_device")
        result = setup_manager.resolve_string("{{ unsorted | sorted }}", "test_device")
        assert result == "[1, 1, 3, 4, 5]"

    def test_reversed_basic(self, setup_manager):
        """Test reversed filter."""
        setup_manager.set_runtime_variable("list", [1, 2, 3], "test_device")
        result = setup_manager.resolve_string("{{ list | reversed }}", "test_device")
        assert result == "[3, 2, 1]"

    def test_strip_basic(self, setup_manager):
        """Test strip filter."""
        result = setup_manager.resolve_string("{{ '  hello  ' | strip }}", "test_device")
        assert result == "hello"

    def test_joinx_basic(self, setup_manager):
        """Test joinx filter."""
        setup_manager.set_runtime_variable("list", ["a", "b", "c"], "test_device")
        result = setup_manager.resolve_string("{{ '-' | joinx(list) }}", "test_device")
        assert result == "a-b-c"

    def test_type_basic(self, setup_manager):
        """Test type filter."""
        result = setup_manager.resolve_string("{{ 'string' | type }}", "test_device")
        assert result == "str"

    def test_any_basic(self, setup_manager):
        """Test any filter."""
        setup_manager.set_runtime_variable("list", [False, True, False], "test_device")
        result = setup_manager.resolve_string("{{ list | any }}", "test_device")
        assert result == "True"

    def test_all_basic(self, setup_manager):
        """Test all filter."""
        setup_manager.set_runtime_variable("list", [True, True, True], "test_device")
        result = setup_manager.resolve_string("{{ list | all }}", "test_device")
        assert result == "True"

    def test_len_basic(self, setup_manager):
        """Test len filter."""
        setup_manager.set_runtime_variable("list", [1, 2, 3], "test_device")
        result = setup_manager.resolve_string("{{ list | len }}", "test_device")
        assert result == "3"