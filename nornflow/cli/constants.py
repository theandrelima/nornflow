# ruff: noqa: W291
from pathlib import Path

from nornflow.vars.constants import DEFAULTS_FILENAME

# Directory where the user is running the CLI from
CWD = Path.cwd()

# Default location for NornFlow settings file
NORNFLOW_SETTINGS = CWD / "nornflow.yaml"

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

# Banners
INIT_BANNER = """\n ██████   █████                               ███████████ ████                          
░░██████ ░░███                               ░░███░░░░░░█░░███                          
 ░███░███ ░███   ██████  ████████  ████████   ░███   █ ░  ░███   ██████  █████ ███ █████
 ░███░░███░███  ███░░███░░███░░███░░███░░███  ░███████    ░███  ███░░███░░███ ░███░░███ 
 ░███ ░░██████ ░███ ░███ ░███ ░░░  ░███ ░███  ░███░░░█    ░███ ░███ ░███ ░███ ░███ ░███ 
 ░███  ░░█████ ░███ ░███ ░███      ░███ ░███  ░███  ░     ░███ ░███ ░███ ░░███████████  
 █████  ░░█████░░██████  █████     ████ █████ █████       █████░░██████   ░░████░████   
░░░░░    ░░░░░  ░░░░░░  ░░░░░     ░░░░ ░░░░░ ░░░░░       ░░░░░  ░░░░░░     ░░░░ ░░░░    
                                                                                      """
