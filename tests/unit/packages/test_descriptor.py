import pytest
from pydantic import ValidationError

from nornflow.packages.constants import VALID_RESOURCE_TYPES
from nornflow.packages.descriptor import PackageDescriptor


class TestPackageDescriptorCreation:
    """Tests for PackageDescriptor instantiation and field validation."""

    def test_bare_name_no_include(self):
        desc = PackageDescriptor(name="my_package")
        assert desc.name == "my_package"
        assert desc.include is None

    def test_name_is_stripped(self):
        desc = PackageDescriptor(name="  spaced_name  ")
        assert desc.name == "spaced_name"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError, match="Package name cannot be empty"):
            PackageDescriptor(name="")

    def test_whitespace_only_name_raises(self):
        with pytest.raises(ValidationError, match="Package name cannot be empty"):
            PackageDescriptor(name="   ")

    def test_valid_include_list(self):
        desc = PackageDescriptor(name="pkg", include=["tasks", "hooks"])
        assert desc.include == ["tasks", "hooks"]

    def test_empty_include_list_raises(self):
        with pytest.raises(ValidationError, match="non-empty list"):
            PackageDescriptor(name="pkg", include=[])

    def test_invalid_resource_type_in_include_raises(self):
        with pytest.raises(ValidationError, match="Invalid resource type"):
            PackageDescriptor(name="pkg", include=["tasks", "bananas"])

    def test_all_valid_resource_types_accepted(self):
        desc = PackageDescriptor(name="pkg", include=list(VALID_RESOURCE_TYPES))
        assert set(desc.include) == set(VALID_RESOURCE_TYPES)

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError, match="extra"):
            PackageDescriptor(name="pkg", unknown_field="bad")

    def test_include_none_explicitly(self):
        desc = PackageDescriptor(name="pkg", include=None)
        assert desc.include is None

    def test_dotted_package_name(self):
        desc = PackageDescriptor(name="org.company.nornflow_plugin")
        assert desc.name == "org.company.nornflow_plugin"


class TestShouldImport:
    """Tests for PackageDescriptor.should_import()."""

    def test_no_include_imports_everything(self, descriptor_all):
        for rt in VALID_RESOURCE_TYPES:
            assert descriptor_all.should_import(rt) is True

    def test_include_tasks_only_imports_tasks(self, descriptor_tasks_only):
        assert descriptor_tasks_only.should_import("tasks") is True

    def test_include_tasks_only_skips_hooks(self, descriptor_tasks_only):
        assert descriptor_tasks_only.should_import("hooks") is False

    def test_include_tasks_only_skips_workflows(self, descriptor_tasks_only):
        assert descriptor_tasks_only.should_import("workflows") is False

    def test_multiple_includes(self, descriptor_multiple_includes):
        assert descriptor_multiple_includes.should_import("tasks") is True
        assert descriptor_multiple_includes.should_import("hooks") is True
        assert descriptor_multiple_includes.should_import("workflows") is True
        assert descriptor_multiple_includes.should_import("filters") is False
        assert descriptor_multiple_includes.should_import("j2_filters") is False

    def test_unknown_resource_type_returns_false_when_include_set(self, descriptor_tasks_only):
        assert descriptor_tasks_only.should_import("nonexistent") is False

    def test_unknown_resource_type_returns_true_when_no_include(self, descriptor_all):
        assert descriptor_all.should_import("nonexistent") is True


class TestExplicitlyIncludes:
    """Tests for PackageDescriptor.explicitly_includes()."""

    def test_none_include_never_explicit(self, descriptor_all):
        for rt in VALID_RESOURCE_TYPES:
            assert descriptor_all.explicitly_includes(rt) is False

    def test_tasks_only_explicit_for_tasks(self, descriptor_tasks_only):
        assert descriptor_tasks_only.explicitly_includes("tasks") is True

    def test_tasks_only_not_explicit_for_hooks(self, descriptor_tasks_only):
        assert descriptor_tasks_only.explicitly_includes("hooks") is False

    def test_multiple_includes_explicit(self, descriptor_multiple_includes):
        assert descriptor_multiple_includes.explicitly_includes("tasks") is True
        assert descriptor_multiple_includes.explicitly_includes("hooks") is True
        assert descriptor_multiple_includes.explicitly_includes("filters") is False
