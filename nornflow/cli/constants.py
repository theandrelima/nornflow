from pathlib import Path
from nornflow.vars.constants import VARS_DIR_DEFAULT, DEFAULTS_FILENAME

# Directory where the user is running the CLI from
CWD = Path.cwd()

# Runtime directories and files (relative to user's current working directory)
NORNIR_DEFAULT_CONFIG_DIR = CWD / "nornir_configs"
TASKS_DIR = CWD / "tasks"
WORKFLOWS_DIR = CWD / "workflows"
FILTERS_DIR = CWD / "filters"
NORNFLOW_SETTINGS = CWD / "nornflow.yaml"
DEFAULT_VARS_DIR = CWD / VARS_DIR_DEFAULT

# NornFlow's samples directory
NORNFLOW_SAMPLES_DIR = Path(__file__).parent / "samples"

# Package sample files (always relative to the CLI package)
HELLO_WORLD_TASK_FILE = NORNFLOW_SAMPLES_DIR / "hello_world.py"
GREET_USER_TASK_FILE = NORNFLOW_SAMPLES_DIR / "greet_user.py"
SAMPLE_WORKFLOW_FILE = NORNFLOW_SAMPLES_DIR / "hello_world.yaml"
SAMPLE_NORNFLOW_FILE = NORNFLOW_SAMPLES_DIR / "nornflow.yaml"
SAMPLE_NORNIR_CONFIGS_DIR = NORNFLOW_SAMPLES_DIR / "nornir_configs"
SAMPLE_VARS_FILE = NORNFLOW_SAMPLES_DIR / DEFAULTS_FILENAME

# Table rendering parameters
DESCRIPTION_FIRST_SENTENCE_LENGTH = 100
