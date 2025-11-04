#!/usr/bin/env python3
"""
Webpage Scraper - Scrape content from URLs using self-hosted Firecrawl API.

This script reads JSON files from an input directory, extracts URLs,
scrapes each URL using self-hosted Firecrawl API (localhost:3002), and saves content as markdown files.
No API key required since authentication is disabled in self-hosted setup.
"""

import argparse
import os
import sys
import logging
from pathlib import Path
from typing import List
import asyncio
import requests
import json

from .file_finder import find_json_files, validate_directory
from .json_parser import extract_urls_from_json_file

# Use the global logger configuration
logger = logging.getLogger(__name__)


def create_output_path(input_file: str, url: str, input_dir: str, output_dir: str) -> str:
    """
    Create the output path for scraped content, mirroring the input structure.

    Args:
        input_file (str): Path to the input JSON file.
        url (str): The URL being scraped.
        input_dir (str): The input directory.
        output_dir (str): The output directory.

    Returns:
        str: The output path for the scraped content.
    """
    # Get relative path from input directory
    rel_path = os.path.relpath(input_file, input_dir)

    # Remove .json extension and create directory structure
    rel_dir = os.path.splitext(rel_path)[0]

    # Create a safe filename from URL
    url_filename = create_safe_filename(url)

    # Combine paths
    output_subdir = os.path.join(output_dir, rel_dir)
    output_path = os.path.join(output_subdir, f"{url_filename}.md")

    return output_path


def create_safe_filename(url: str) -> str:
    """
    Create a safe filename from a URL.

    Args:
        url (str): The URL to convert.

    Returns:
        str: A safe filename.
    """
    # Remove protocol and replace special characters
    filename = url.replace("https://", "").replace("http://", "")
    filename = filename.replace("/", "_").replace("?", "_").replace("&", "_")
    filename = filename.replace(":", "_").replace("=", "_").replace(".", "_")

    # Limit length and ensure it's not empty
    filename = filename[:100] if len(filename) > 100 else filename
    return filename or "content"


async def scrape_urls_batch(urls: List[str], api_key: str = None) -> dict:
    """
    Scrape multiple URLs using self-hosted Firecrawl API.

    Args:
        urls (List[str]): List of URLs to scrape.
        api_key (str): Not used in self-hosted setup (authentication disabled).

    Returns:
        dict: Batch scraping results with success/failure counts and data.
    """
    base_url = "http://localhost:3002"
    successful_results = []
    failed_count = 0

    logger.info(f"Starting batch scrape of {len(urls)} URLs using self-hosted Firecrawl...")

    for url in urls:
        try:
            # Make direct HTTP request to self-hosted Firecrawl
            response = requests.post(
                f"{base_url}/v1/scrape",
                json={
                    "url": url,
                    "formats": ["markdown"]
                },
                headers={
                    "Content-Type": "application/json"
                },
                timeout=30  # 30 second timeout
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success') and 'data' in result:
                    data = result['data']
                    if 'markdown' in data and data['markdown']:
                        # Format the result to match the expected structure
                        formatted_result = {
                            'markdown': data['markdown'],
                            'metadata': data.get('metadata', {
                                'sourceURL': url,
                                'title': data.get('metadata', {}).get('title', ''),
                                'description': data.get('metadata', {}).get('description', ''),
                                'language': data.get('metadata', {}).get('language', 'en')
                            })
                        }
                        successful_results.append(formatted_result)
                        logger.debug(f"Successfully scraped: {url}")
                    else:
                        failed_count += 1
                        logger.warning(f"No markdown content found for: {url}")
                else:
                    failed_count += 1
                    logger.warning(f"API returned unsuccessful response for: {url}")
            else:
                failed_count += 1
                logger.warning(f"HTTP {response.status_code} for URL {url}: {response.text}")

        except requests.exceptions.RequestException as e:
            failed_count += 1
            logger.error(f"Request failed for {url}: {e}")
        except Exception as e:
            failed_count += 1
            logger.error(f"Unexpected error scraping {url}: {e}")

    logger.info(f"Batch scrape completed. Success: {len(successful_results)}, Failed: {failed_count}")

    return {
        "success": len(successful_results),
        "failed": failed_count,
        "data": successful_results
    }


async def main_async(input_dir='dataset/acquisition/temp/urls', output_dir='dataset/acquisition/temp/datasources', verbose: bool = False):
    """Main asynchronous function to run the webpage scraper using self-hosted Firecrawl."""

    # Set up logging based on verbose flag
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Validate input directory
    if not validate_directory(input_dir):
        logger.error(f"Input directory does not exist or is not a directory: {input_dir}")
        return {"success": 0, "failed": 0, "data": []}

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    logger.debug("Starting self-hosted Firecrawl webpage scraper")
    logger.debug(f"Input directory: {input_dir}")
    logger.debug(f"Output directory: {output_dir}")

    try:
        # Find all JSON files
        json_files = find_json_files(input_dir)
        logger.debug(f"Found {len(json_files)} JSON files in '{input_dir}'")

        if not json_files:
            logger.warning("No JSON files found in input directory. Exiting.")
            return {"success": 0, "failed": 0, "data": []}

        # Collect all URLs from all JSON files
        all_urls = []
        url_to_file_mapping = {}  # Track which file each URL came from

        for json_file in json_files:
            try:
                url_info_list = extract_urls_from_json_file(json_file)
                for url, is_pdf in url_info_list:
                    # For now, we'll scrape all URLs. PDFs might need special handling
                    if not is_pdf:  # Skip PDFs for now as Firecrawl handles web content
                        all_urls.append(url)
                        url_to_file_mapping[url] = json_file
                    else:
                        logger.info(f"Skipping PDF URL (not supported by Firecrawl batch scraping): {url}")
            except Exception as e:
                logger.error(f"Error reading JSON file {json_file}: {e}")

        logger.debug(f"Extracted {len(all_urls)} URLs for content scraping.")
        if not all_urls:
            logger.warning("No URLs found for content scraping. Exiting.")
            return {"success": 0, "failed": 0, "data": []}

        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(all_urls))
        if len(unique_urls) < len(all_urls):
            logger.info(f"Removed {len(all_urls) - len(unique_urls)} duplicate URLs")

        # Perform batch scraping
        batch_result = await scrape_urls_batch(unique_urls)

        # Save successful results to files
        saved_count = 0
        for result in batch_result["data"]:
            try:
                url = result.get('metadata', {}).get('sourceURL', '')
                if not url:
                    continue

                # Find which input file this URL came from
                input_file = url_to_file_mapping.get(url, json_files[0])  # Fallback to first file

                # Create output path
                output_path = create_output_path(input_file, url, input_dir, output_dir)
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                # Save markdown content
                with open(output_path, "w", encoding='utf-8') as f:
                    f.write(result.get('markdown', ''))

                logger.debug(f"Successfully saved content: {output_path}")
                saved_count += 1

            except Exception as e:
                logger.error(f"Failed to save content for URL {url}: {e}")

        logger.info(f"Self-hosted Firecrawl scraper completed. Total URLs processed: {len(unique_urls)}, Successfully saved: {saved_count}")

        return {
            "success": saved_count,
            "failed": len(unique_urls) - saved_count,
            "data": batch_result["data"]
        }

    except Exception as e:
        logger.critical(f"An unexpected error occurred in Firecrawl scraper: {e}", exc_info=True)
        return {"success": 0, "failed": 0, "data": []}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape content from URLs using self-hosted Firecrawl API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
   python main.py /path/to/input /path/to/output
   python main.py /path/to/input /path/to/output --verbose

Requirements:
   Self-hosted Firecrawl instance running on localhost:3002
   No API key required (authentication disabled in self-hosted setup)
        """
    )

    parser.add_argument(
        "input_dir",
        nargs='?',
        default='dataset/acquisition/temp/urls',
        help="Input directory containing JSON files with URLs"
    )

    parser.add_argument(
        "output_dir",
        nargs='?',
        default='dataset/acquisition/temp/datasources',
        help="Output directory where scraped content will be saved"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()
    result = asyncio.run(main_async(args.input_dir, args.output_dir, args.verbose))
    print(f"Scraping completed: {result['success']} successful, {result['failed']} failed")