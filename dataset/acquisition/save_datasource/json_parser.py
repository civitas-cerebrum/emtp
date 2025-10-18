"""
Module for parsing JSON files and extracting URLs.
"""

import json
import os
from typing import List, Dict, Any
from urllib.parse import urlparse


def parse_json_file(file_path: str) -> Dict[str, Any]:
    """
    Parse a JSON file and return its contents as a dictionary.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        Dict[str, Any]: Parsed JSON content.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"JSON file '{file_path}' not found.")

    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            data = json.load(file)
            return data
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in file '{file_path}': {e}")


def extract_urls_from_data(data: Any) -> List[str]:
    """
    Extract URLs from parsed JSON data. This function recursively searches
    through the data structure to find URL strings.

    Args:
        data: The parsed JSON data (dict, list, or primitive).

    Returns:
        List[str]: List of valid URLs found in the data.
    """
    urls = []

    if isinstance(data, dict):
        for key, value in data.items():
            urls.extend(extract_urls_from_data(value))
    elif isinstance(data, list):
        for item in data:
            urls.extend(extract_urls_from_data(item))
    elif isinstance(data, str):
        # Check if the string is a valid URL
        if is_valid_url(data):
            urls.append(data)

    return urls


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL.

    Args:
        url (str): The string to check.

    Returns:
        bool: True if valid URL, False otherwise.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def extract_urls_from_json_file(file_path: str) -> List[tuple]:
    """
    Parse a JSON file and extract all URLs from it, along with PDF detection info.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        List[tuple]: List of (url, is_pdf) tuples found in the JSON file.
    """
    data = parse_json_file(file_path)
    url_info = extract_urls_with_pdf_info(data)
    return list(set(url_info))  # Remove duplicates while preserving order


def extract_urls_with_pdf_info(data: Any) -> List[tuple]:
    """
    Extract URLs from parsed JSON data with PDF detection based on dorks.

    Args:
        data: The parsed JSON data (dict, list, or primitive).

    Returns:
        List[tuple]: List of (url, is_pdf) tuples.
    """
    url_info = []

    if isinstance(data, dict):
        # Check if this dict represents a search result with dorks
        if 'urls' in data and 'dorks' in data:
            dorks = data.get('dorks')
            is_pdf = dorks and isinstance(dorks, str) and dorks.lower().find('filetype:pdf') != -1
            for url in data['urls']:
                if isinstance(url, str) and is_valid_url(url):
                    url_info.append((url, is_pdf))
        else:
            # Recursively search other dict structures
            for key, value in data.items():
                url_info.extend(extract_urls_with_pdf_info(value))
    elif isinstance(data, list):
        for item in data:
            url_info.extend(extract_urls_with_pdf_info(item))
    elif isinstance(data, str):
        # Check if the string is a valid URL (legacy support)
        if is_valid_url(data):
            url_info.append((data, False))  # Assume not PDF for legacy format

    return url_info