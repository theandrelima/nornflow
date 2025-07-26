import pytest
import json


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
        result = setup_manager.resolve_string("{{ 'Router-NYC-001' | regex_replace('\\d+', 'XXX') }}", "test_device")
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
        interfaces = [
            {"name": "Gi0/1", "vlan": 100},
            {"name": "Gi0/2", "vlan": 200}
        ]
        setup_manager.set_runtime_variable("interfaces", interfaces, "test_device")
        
        result = setup_manager.resolve_string("{{ interfaces | json_query('[*].name') }}", "test_device")
        # json_query returns a list which gets stringified
        assert result == "['Gi0/1', 'Gi0/2']"
        
        # Test deep_merge
        defaults = {
            "ntp": {
                "server": "10.0.0.1",
                "source": "Lo0"
            },
            "snmp": {
                "community": "public"
            }
        }
        custom = {
            "ntp": {
                "server": "10.0.0.2"
            }
        }
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
        import random
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