"""
Module for parsing JSON files and extracting URLs.
"""

import json
import os
from typing import List, Dict, Any
from urllib.parse import urlparse


def parse_json_file(file_path: str) -> Dict[str, Any]:
    """
    Parses a JSON file and returns its content.
    Raises errors if the file is not found or invalid.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if not os.path.isfile(file_path):
        raise ValueError(f"Path is not a file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file {file_path}: {e}")


def extract_urls_from_data(data: Any) -> List[str]:
    """
    Recursively extracts URLs from a given data structure.
    Handles dictionaries, lists, and strings.
    """
    urls = []
    if isinstance(data, dict):
        for value in data.values():
            urls.extend(extract_urls_from_data(value))
    elif isinstance(data, list):
        for item in data:
            urls.extend(extract_urls_from_data(item))
    elif isinstance(data, str):
        if is_valid_url(data):
            urls.append(data)
    return urls


def is_valid_url(url: str) -> bool:
    """
    Checks if a given string is a valid URL.
    Returns True if valid, False otherwise.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def extract_urls_from_json_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts URLs and associated metadata from a JSON file.
    Handles a specific input JSON structure and removes duplicate URLs.
    """
    data = parse_json_file(file_path)
    extracted_urls_with_metadata = []

    # The data is a list of dictionaries, where each dict has 'category', 'question', 'urls'
    if isinstance(data, list):
        for entry in data:
            category_name = entry.get("category", "Uncategorized")
            question = entry.get("question")
            urls = entry.get("urls", [])

            for url in urls:
                if url and is_valid_url(url):
                    extracted_urls_with_metadata.append({
                        "url": url,
                        "categoryName": category_name,
                        "question": question,
                        "is_pdf": False # Assuming URLs from search are not PDFs
                    })
    else:
        # Fallback for old/unexpected format (dict with categories as keys)
        for category_name, entries in data.items():
            for entry in entries:
                url = entry.get("url")
                question = entry.get("question")
                is_pdf = entry.get("is_pdf", False) # Default to False if not specified

                if url and is_valid_url(url):
                    extracted_urls_with_metadata.append({
                        "url": url,
                        "categoryName": category_name,
                        "question": question,
                        "is_pdf": is_pdf
                    })
    
    # Remove duplicates based on URL
    unique_urls_dict = {item["url"]: item for item in extracted_urls_with_metadata}
    return list(unique_urls_dict.values())


def extract_urls_with_pdf_info(data: Any) -> List[tuple]:
    """
    Extracts URLs and PDF information from raw data.
    Returns a list of tuples containing URL details.
    """
    urls_with_pdf = []
    if isinstance(data, dict):
        # Check if this dict itself represents a URL entry
        url = data.get("url")
        is_pdf = data.get("is_pdf", False)
        if url and is_valid_url(url):
            urls_with_pdf.append((url, is_pdf))
        
        # Recursively check values
        for value in data.values():
            urls_with_pdf.extend(extract_urls_with_pdf_info(value))
            
    elif isinstance(data, list):
        for item in data:
            urls_with_pdf.extend(extract_urls_with_pdf_info(item))
            
    # For strings, only add if it's a valid URL and assume not PDF
    elif isinstance(data, str) and is_valid_url(data):
        urls_with_pdf.append((data, False)) # Default to not PDF for raw URLs

    return urls_with_pdf