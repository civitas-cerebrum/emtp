"""
Module for finding JSON files in a directory structure.
"""

import os
import glob
from typing import List


def find_json_files(directory: str) -> List[str]:
    """
    Finds all JSON files recursively within a given directory.
    Returns a sorted list of their paths.
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
    Checks if a given path exists and is a directory.
    Returns True if valid, False otherwise.
    """
    return os.path.exists(directory) and os.path.isdir(directory)