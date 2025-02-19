from pathlib import Path

# Directory where the user is running the CLI from
CWD = Path.cwd()

# Runtime directories and files (relative to user's current working directory)
NORNIR_DEFAULT_CONFIG_DIR = CWD / "nornir_configs"
TASKS_DIR = CWD / "tasks"
WORKFLOWS_DIR = CWD / "workflows"
NORNFLOW_CONFIG_FILE = CWD / "nornflow.yaml"

# NornFlow's samples directory
NORNFLOW_SAMPLES_DIR = Path(__file__).parent / "samples"

# Package sample files (always relative to the CLI package)
SAMPLE_TASK_FILE = NORNFLOW_SAMPLES_DIR / "hello_world.py"
SAMPLE_WORKFLOW_FILE = NORNFLOW_SAMPLES_DIR / "hello_world.yaml"
SAMPLE_NORNFLOW_FILE = NORNFLOW_SAMPLES_DIR / "nornflow.yaml"
SAMPLE_NORNIR_CONFIGS_DIR = NORNFLOW_SAMPLES_DIR / "nornir_configs"
