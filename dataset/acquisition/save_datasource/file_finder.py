"""
Module for finding JSON files in a directory structure.
"""

import os
import glob
from typing import List


def find_json_files(directory: str) -> List[str]:
    """
    Recursively find all JSON files in the given directory.

    Args:
        directory (str): The root directory to search in.

    Returns:
        List[str]: List of paths to JSON files found.

    Raises:
        ValueError: If the directory does not exist or is not a directory.
    """
    if not os.path.exists(directory):
        raise ValueError(f"Directory '{directory}' does not exist.")

    if not os.path.isdir(directory):
        raise ValueError(f"'{directory}' is not a directory.")

    # Use glob to find all .json files recursively
    pattern = os.path.join(directory, "**", "*.json")
    json_files = glob.glob(pattern, recursive=True)

    return sorted(json_files)


def validate_directory(directory: str) -> bool:
    """
    Validate that the given path is an existing directory.

    Args:
        directory (str): The directory path to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    return os.path.exists(directory) and os.path.isdir(directory)