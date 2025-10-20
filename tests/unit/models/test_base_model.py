"""Tests for NornFlowBaseModel."""

import pytest

from nornflow.exceptions import TaskError
from nornflow.models import NornFlowBaseModel


class TestNornFlowBaseModel:
    def test_create_with_validation(self):
        """Test model creation with universal validation."""
        class TestModel(NornFlowBaseModel):
            name: str
            _key = ("name",)
            _exclude_from_universal_validations = ("name",)

        model = TestModel.create({"name": "test"})
        assert model.name == "test"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        class TestModel(NornFlowBaseModel):
            name: str
            _key = ("name",)

        with pytest.raises(ValueError):
            TestModel.create({"name": "test", "extra": "field"})

    def test_universal_validation_failure(self):
        """Test universal validation catches Jinja2."""
        class TestModel(NornFlowBaseModel):
            name: str
            _key = ("name",)

        with pytest.raises(TaskError, match="Jinja2"):
            TestModel.create({"name": "{{jinja}}"})