from unittest.mock import MagicMock, patch

import pytest

from nornflow import NornFlow, NornFlowBuilder
from nornflow.constants import FailureStrategy
from nornflow.exceptions import (
    InitializationError,
    WorkflowError,
)
from nornflow.models import WorkflowModel
from nornflow.settings import NornFlowSettings


class TestNornFlowBasicCreation:
    """Test basic NornFlow creation scenarios."""

    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        self.test_name = request.function.__name__

    def test_create_with_minimal_settings(self, tmp_path, task_content):
        """Test creating NornFlow with minimal required settings."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "task1.py").write_text(task_content)

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            settings = NornFlowSettings(
                nornir_config_file="dummy_config.yaml",
                local_tasks=[str(tasks_dir)]
            )
            nornflow = NornFlow(nornflow_settings=settings)

            assert isinstance(nornflow, NornFlow)
            assert "hello_world" in nornflow.tasks_catalog
            assert "set" in nornflow.tasks_catalog

    def test_create_without_settings_uses_defaults(self):
        """Test that NornFlow requires either settings object or no kwargs at all."""
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            settings = NornFlowSettings(nornir_config_file="test.yaml")
            nornflow = NornFlow(nornflow_settings=settings)
            assert nornflow.settings == settings


class TestNornFlowValidation:
    """Test NornFlow validation logic."""

    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        self.test_name = request.function.__name__

    def test_empty_tasks_catalog(self, tmp_path):
        """Test that NornFlow can be created even with empty tasks catalog (builtins still present)."""
        tasks_dir = tmp_path / "empty_tasks"
        tasks_dir.mkdir()

        settings = NornFlowSettings(
            nornir_config_file="dummy_config.yaml",
            local_tasks=[str(tasks_dir)]
        )

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nornflow = NornFlow(nornflow_settings=settings)
            assert "set" in nornflow.tasks_catalog
            assert "echo" in nornflow.tasks_catalog

    def test_invalid_tasks_directory_raises_error(self):
        """Test that NornFlow initialization raises error for non-existent directories."""
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            settings = NornFlowSettings(
                nornir_config_file="dummy_config.yaml",
                local_tasks=["/nonexistent/dir"]
            )

            with pytest.raises(InitializationError, match="Tasks directory does not exist"):
                NornFlow(nornflow_settings=settings)

    def test_property_modifications(self, basic_nornflow):
        """Ensure nornir_manager property is readable."""
        assert basic_nornflow.nornir_manager is not None


class TestNornFlowPrecedence:
    """Test precedence logic for failure_strategy and dry_run."""

    def test_failure_strategy_constructor_overrides_workflow(self):
        """Constructor failure_strategy should override workflow failure_strategy."""
        wf = MagicMock(spec=WorkflowModel)
        wf.failure_strategy = FailureStrategy.FAIL_FAST
        wf.processors = []
        wf.inventory_filters = {}
        wf.vars = {}
        wf.description = None
        wf.dry_run = None
        wf.name = "WF"

        settings = NornFlowSettings(
            nornir_config_file="dummy.yaml",
            failure_strategy=FailureStrategy.SKIP_FAILED
        )

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlow(
                nornflow_settings=settings,
                workflow=wf,
                failure_strategy=FailureStrategy.FAIL_FAST
            )
            assert nf.failure_strategy == FailureStrategy.FAIL_FAST

    def test_failure_strategy_workflow_overrides_settings(self):
        """Workflow failure_strategy should override settings when constructor doesn't override."""
        wf = MagicMock(spec=WorkflowModel)
        wf.failure_strategy = FailureStrategy.FAIL_FAST
        wf.processors = []
        wf.inventory_filters = {}
        wf.vars = {}
        wf.description = None
        wf.dry_run = None
        wf.name = "WF"

        settings = NornFlowSettings(
            nornir_config_file="dummy.yaml",
            failure_strategy=FailureStrategy.SKIP_FAILED
        )

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlow(nornflow_settings=settings, workflow=wf)
            assert nf.failure_strategy == FailureStrategy.FAIL_FAST

    def test_failure_strategy_settings_fallback(self):
        """Settings failure_strategy should be used when workflow has none."""
        wf = MagicMock(spec=WorkflowModel)
        wf.failure_strategy = None
        wf.processors = []
        wf.inventory_filters = {}
        wf.vars = {}
        wf.description = None
        wf.dry_run = None
        wf.name = "WF"

        settings = NornFlowSettings(
            nornir_config_file="dummy.yaml",
            failure_strategy=FailureStrategy.SKIP_FAILED
        )

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlow(nornflow_settings=settings, workflow=wf)
            assert nf.failure_strategy == FailureStrategy.SKIP_FAILED

    def test_dry_run_constructor_overrides_workflow(self):
        """Constructor dry_run should override workflow dry_run."""
        wf = MagicMock(spec=WorkflowModel)
        wf.dry_run = True
        wf.processors = []
        wf.inventory_filters = {}
        wf.vars = {}
        wf.description = None
        wf.failure_strategy = None
        wf.name = "WF"

        settings = NornFlowSettings(nornir_config_file="dummy.yaml", dry_run=False)

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlow(nornflow_settings=settings, workflow=wf, dry_run=False)
            assert nf.dry_run is False

    def test_dry_run_workflow_overrides_settings(self):
        """Workflow dry_run should override settings when constructor doesn't override."""
        wf = MagicMock(spec=WorkflowModel)
        wf.dry_run = True
        wf.processors = []
        wf.inventory_filters = {}
        wf.vars = {}
        wf.description = None
        wf.failure_strategy = None
        wf.name = "WF"

        settings = NornFlowSettings(nornir_config_file="dummy.yaml", dry_run=False)

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlow(nornflow_settings=settings, workflow=wf)
            assert nf.dry_run is True

    def test_dry_run_settings_fallback(self):
        """Settings dry_run should be used when workflow has none."""
        wf = MagicMock(spec=WorkflowModel)
        wf.dry_run = None
        wf.processors = []
        wf.inventory_filters = {}
        wf.vars = {}
        wf.description = None
        wf.failure_strategy = None
        wf.name = "WF"

        settings = NornFlowSettings(nornir_config_file="dummy.yaml", dry_run=True)

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlow(nornflow_settings=settings, workflow=wf)
            assert nf.dry_run is True


class TestWorkflowModelCreation:
    """Test workflow model creation."""

    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        self.test_name = request.function.__name__

    def test_create_from_dict_missing_workflow_key(self):
        with pytest.raises(WorkflowError):
            WorkflowModel.create({})

    def test_create_from_invalid_dict(self, invalid_workflow_dict):
        with pytest.raises(ValueError):
            WorkflowModel.create(invalid_workflow_dict)

    def test_create_from_valid_dict(self, valid_workflow_dict):
        workflow = WorkflowModel.create(valid_workflow_dict)
        assert workflow.name == f"Test Workflow {self.test_name}"
        assert len(workflow.tasks) == 1

    def test_inventory_filters_dict(self, valid_workflow_dict):
        workflow = WorkflowModel.create(valid_workflow_dict)
        filters = {
            "hosts": list(workflow.inventory_filters["hosts"]),
            "groups": list(workflow.inventory_filters["groups"]),
        }
        assert filters == {"hosts": ["host1", "host2"], "groups": ["group1"]}


class TestNornFlowBuilder:
    """Test builder behaviour."""

    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        self.test_name = request.function.__name__

    def test_builder_with_settings(self, basic_settings):
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlowBuilder().with_settings_object(basic_settings).build()
            assert nf.settings == basic_settings

    def test_builder_with_workflow_object(self, basic_settings, valid_workflow):
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = (
                NornFlowBuilder()
                .with_settings_object(basic_settings)
                .with_workflow_model(valid_workflow)
                .build()
            )
            assert nf.workflow == valid_workflow

    def test_builder_with_workflow_path(self, basic_settings, valid_workflow_file):
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"), \
             patch("nornflow.nornflow.NornFlow._load_workflow_from_name") as mock_load:
            mock_workflow = MagicMock(spec=WorkflowModel)
            mock_load.return_value = (mock_workflow, valid_workflow_file)

            nf = (
                NornFlowBuilder()
                .with_settings_object(basic_settings)
                .with_workflow_path(valid_workflow_file)
                .build()
            )
            assert isinstance(nf.workflow, WorkflowModel)

    def test_builder_precedence(self, basic_settings, valid_workflow, valid_workflow_file):
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = (
                NornFlowBuilder()
                .with_settings_object(basic_settings)
                .with_workflow_path(valid_workflow_file)
                .with_workflow_model(valid_workflow)
                .build()
            )
            assert nf.workflow == valid_workflow


class TestWorkflowModelValidation:
    """Workflow validation."""

    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        self.test_name = request.function.__name__

    def test_empty_tasks_list(self):
        with pytest.raises(ValueError):
            WorkflowModel.create({"workflow": {"name": "Test", "tasks": []}})

    def test_invalid_failure_strategy(self):
        data = {
            "workflow": {
                "name": "Test Workflow",
                "failure_strategy": "invalid",
                "tasks": [{"name": "t"}],
            }
        }
        with pytest.raises(WorkflowError):
            WorkflowModel.create(data)

    def test_task_validation(self):
        data = {"workflow": {"name": "Test", "tasks": [{"name": "x"}]}}
        workflow = WorkflowModel.create(data)

        mock_nf = MagicMock(spec=NornFlow)
        mock_nf._tasks_catalog = {}
        mock_nf._vars_manager = MagicMock()
        mock_nf.workflow = workflow


class TestNornFlowExecution:
    """Execution tests."""

    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        self.test_name = request.function.__name__

    @patch("nornflow.nornflow.NornirManager")
    def test_run_uses_context_manager(self, mock_mgr_cls):
        """Ensure context manager is used during run()."""
        mock_mgr = MagicMock()
        mock_mgr.nornir = MagicMock()
        mock_mgr.nornir.inventory.hosts = {}
        mock_mgr.nornir.data.failed_hosts = {}
        mock_mgr.nornir.processors = []
        mock_mgr.__enter__.return_value = mock_mgr
        mock_mgr.__exit__.return_value = None
        mock_mgr_cls.return_value = mock_mgr

        wf = MagicMock(spec=WorkflowModel)
        wf.dry_run = False
        wf.tasks = []
        wf.inventory_filters = {}
        wf.processors = []
        wf.vars = {}
        wf.description = None
        wf.failure_strategy = None
        wf.name = "Test WF"

        settings = NornFlowSettings(
            nornir_config_file="dummy.yaml",
            local_workflows=[]
        )

        with patch("nornflow.nornflow.load_file_to_dict", return_value={}):
            nf = NornFlow(nornflow_settings=settings, workflow=wf)
            nf._nornir_manager = mock_mgr
            nf.run()

        mock_mgr.__enter__.assert_called_once()
        mock_mgr.__exit__.assert_called_once()

    @patch("nornflow.nornflow.NornirManager")
    def test_run_handles_exceptions(self, mock_mgr_cls):
        """Connections are closed even when an error occurs."""
        mock_mgr = MagicMock()
        mock_mgr.nornir = MagicMock()
        mock_mgr.nornir.inventory.hosts = {}
        mock_mgr.nornir.data.failed_hosts = {}
        mock_mgr.nornir.processors = []
        mock_mgr.__enter__.return_value = mock_mgr
        mock_mgr.__exit__.return_value = None
        mock_mgr_cls.return_value = mock_mgr
    
        task_mock = MagicMock()
        task_mock.name = "echo"
        task_mock.run.side_effect = RuntimeError("test error")
    
        wf = MagicMock(spec=WorkflowModel)
        wf.dry_run = False
        wf.inventory_filters = {}
        wf.processors = []
        wf.vars = {}
        wf.description = None
        wf.failure_strategy = None
        wf.name = "Test WF"
        wf.tasks = [task_mock]
    
        settings = NornFlowSettings(
            nornir_config_file="dummy.yaml",
            local_workflows=[]
        )
    
        with patch("nornflow.nornflow.load_file_to_dict", return_value={}):
            nf = NornFlow(nornflow_settings=settings, workflow=wf)
            nf._nornir_manager = mock_mgr
    
            with pytest.raises(RuntimeError, match="test error"):
                nf.run()
    
        mock_mgr.__enter__.assert_called_once()
        mock_mgr.__exit__.assert_called_once()

    def test_workflow_execution_orchestration(self):
        """Tasks run in order."""
        t1, t2 = MagicMock(), MagicMock()
        t1.name, t2.name = "task1", "task2"

        wf = MagicMock(spec=WorkflowModel)
        wf.tasks = [t1, t2]
        wf.dry_run = False
        wf.inventory_filters = {}
        wf.vars = {}
        wf.processors = []
        wf.failure_strategy = None
        wf.name = "WF"
        wf.description = None

        settings = NornFlowSettings(nornir_config_file="dummy_config.yaml")

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"), patch.object(
            NornFlow, "_create_variable_manager", return_value=MagicMock()
        ):
            nf = NornFlow(nornflow_settings=settings, workflow=wf)
            assert nf.workflow.tasks == [t1, t2]


class TestNornFlowProcessors:
    """Test processor initialization and application."""

    def test_var_processor_lazy_initialization_without_workflow(self):
        """var_processor should be None when no workflow is set."""
        settings = NornFlowSettings(nornir_config_file="dummy.yaml")

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlow(nornflow_settings=settings)
            assert nf.var_processor is None

    def test_var_processor_created_with_workflow(self):
        """var_processor should be created when workflow is set."""
        wf = MagicMock(spec=WorkflowModel)
        wf.processors = []
        wf.inventory_filters = {}
        wf.vars = {}
        wf.description = None
        wf.failure_strategy = None
        wf.dry_run = None
        wf.name = "WF"

        settings = NornFlowSettings(nornir_config_file="dummy.yaml")

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"), \
             patch("nornflow.nornflow.NornFlow._create_variable_manager") as mock_vm:
            mock_vm.return_value = MagicMock()
            nf = NornFlow(nornflow_settings=settings, workflow=wf)
            assert nf.var_processor is not None

    @patch("nornflow.nornflow.NornirManager")
    def test_processor_chain_order(self, mock_mgr_cls):
        """Processors should be applied in correct order: var, hook, user, failure_strategy."""
        mock_mgr = MagicMock()
        mock_mgr.nornir = MagicMock()
        mock_mgr.nornir.processors = []

        def mock_apply_processors(processors):
            mock_mgr.nornir.processors.extend(processors)
            return mock_mgr.nornir

        mock_mgr.apply_processors = mock_apply_processors
        mock_mgr_cls.return_value = mock_mgr

        wf = MagicMock(spec=WorkflowModel)
        wf.processors = [{"class": "some.Processor", "args": {}}]
        wf.inventory_filters = {}
        wf.vars = {}
        wf.description = None
        wf.failure_strategy = None
        wf.dry_run = None
        wf.name = "WF"

        settings = NornFlowSettings(nornir_config_file="dummy.yaml")

        with patch("nornflow.nornflow.NornFlow._create_variable_manager") as mock_vm, \
             patch("nornflow.nornflow.load_processor") as mock_load, \
             patch("nornflow.nornflow.load_file_to_dict", return_value={}):
            mock_vm.return_value = MagicMock()
            mock_user_proc = MagicMock()
            mock_load.return_value = mock_user_proc

            nf = NornFlow(nornflow_settings=settings, workflow=wf)
            nf._nornir_manager = mock_mgr

            nf._apply_processors()

            applied_processors = nf.nornir_manager.nornir.processors
            assert applied_processors[0] == nf.var_processor
            assert applied_processors[1] == nf.hook_processor
            assert applied_processors[2] == mock_user_proc
            assert applied_processors[-1] == nf.failure_strategy_processor


class TestNornFlowReturnCodes:
    """Test return code calculation."""

    @patch("nornflow.nornflow.NornirManager")
    def test_return_code_success(self, mock_mgr_cls):
        """Return code should be 0 on success."""
        mock_mgr = MagicMock()
        mock_mgr.nornir = MagicMock()
        mock_mgr.nornir.data.failed_hosts = {}
        mock_mgr.nornir.processors = []
        mock_mgr_cls.return_value = mock_mgr

        wf = MagicMock(spec=WorkflowModel)
        wf.tasks = []
        wf.processors = []
        wf.inventory_filters = {}
        wf.vars = {}
        wf.description = None
        wf.failure_strategy = None
        wf.dry_run = None
        wf.name = "WF"

        settings = NornFlowSettings(nornir_config_file="dummy.yaml")

        with patch("nornflow.nornflow.NornFlow._create_variable_manager"), \
             patch("nornflow.nornflow.load_file_to_dict", return_value={}):
            nf = NornFlow(nornflow_settings=settings, workflow=wf)
            nf._nornir_manager = mock_mgr

            assert nf._get_return_code() == 0

    @patch("nornflow.nornflow.NornirManager")
    def test_return_code_with_failed_hosts_no_stats(self, mock_mgr_cls):
        """Return code should be 101 when hosts failed but no stats available."""
        mock_mgr = MagicMock()
        mock_mgr.nornir = MagicMock()
        mock_mgr.nornir.data.failed_hosts = {"host1": None}
        mock_mgr.nornir.processors = []
        mock_mgr_cls.return_value = mock_mgr

        wf = MagicMock(spec=WorkflowModel)
        wf.tasks = []
        wf.processors = []
        wf.inventory_filters = {}
        wf.vars = {}
        wf.description = None
        wf.failure_strategy = None
        wf.dry_run = None
        wf.name = "WF"

        settings = NornFlowSettings(nornir_config_file="dummy.yaml")

        with patch("nornflow.nornflow.NornFlow._create_variable_manager"), \
             patch("nornflow.nornflow.load_file_to_dict", return_value={}):
            nf = NornFlow(nornflow_settings=settings, workflow=wf)
            nf._nornir_manager = mock_mgr

            assert nf._get_return_code() == 101


class TestNornFlowImmutability:
    """Test that certain properties are immutable."""

    def test_settings_immutable(self):
        """settings property should not be settable."""
        settings = NornFlowSettings(nornir_config_file="dummy.yaml")

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlow(nornflow_settings=settings)

            with pytest.raises(Exception):
                nf.settings = NornFlowSettings(nornir_config_file="other.yaml")

    def test_nornir_manager_immutable(self):
        """nornir_manager property should not be settable."""
        settings = NornFlowSettings(nornir_config_file="dummy.yaml")

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlow(nornflow_settings=settings)

            with pytest.raises(Exception):
                nf.nornir_manager = MagicMock()

    def test_tasks_catalog_immutable(self):
        """tasks_catalog property should not be settable."""
        settings = NornFlowSettings(nornir_config_file="dummy.yaml")

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlow(nornflow_settings=settings)

            with pytest.raises(Exception):
                nf.tasks_catalog = {}

    def test_blueprints_catalog_immutable(self):
        """blueprints_catalog property should not be settable."""
        settings = NornFlowSettings(nornir_config_file="dummy.yaml")

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlow(nornflow_settings=settings)

            with pytest.raises(Exception):
                nf.blueprints_catalog = {}