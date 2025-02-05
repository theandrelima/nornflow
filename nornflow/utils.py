import yaml
from typing import Dict, Union
from constants import TRUTHY, FALSY


def read_yaml_file(file_path: str) -> Dict:
    """
    Reads a YAML file and returns its contents as a dictionary.

    Args:
        file_path (str): Path to the YAML file.

    Returns:
        Dict: Dictionary containing the YAML file contents.
    """
    print(f"Reading YAML file: {file_path}")
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)
    
    
def is_truthy(value: Union[str, None]) -> bool:
    """
    Checks if a value is truthy.

    Args:
        value (str): Value to check.

    Returns:
        bool: True if the value is truthy, False otherwise.
    """
    if not value:
        return False
    
    return value.lower() in TRUTHY

def is_falsy(value: Union[str, None]) -> bool:
    """
    Checks if a value is falsy.

    Args:
        value (str): Value to check.

    Returns:
        bool: True if the value is falsy, False otherwise.
    """
    if not value:
        return True
    
    return value.lower() in FALSY