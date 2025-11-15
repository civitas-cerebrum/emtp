#!/usr/bin/env python3
"""
Webpage Scraper - Scrape content from URLs using Firecrawl API.

This script reads JSON files from an input directory, extracts URLs,
scraping each URL using Firecrawl API, and saves content as markdown files.
Supports both local self-hosted instances and external instances with basic auth.
"""

import argparse
import os
import logging
import configparser
from pathlib import Path
from typing import List, Dict, Any
import asyncio
import requests

from .file_finder import find_json_files, validate_directory
from .json_parser import extract_urls_from_json_file

# Use the global logger configuration
logger = logging.getLogger(__name__)


def create_output_path(input_file: str, url: str, input_dir: str, output_dir: str) -> str:
    """
    Creates the full output path for a markdown file based on input file, URL, and directories.
    Ensures a unique and safe filename for the scraped URL content.
    """
    rel_path = os.path.relpath(input_file, input_dir)

    # Remove .json extension and create directory structure
    rel_dir = os.path.splitext(rel_path)[0]

    # Create a safe filename from URL
    url_filename = create_safe_filename(url)

    # Combine paths for markdown
    output_subdir_markdown = os.path.join(output_dir, rel_dir)
    markdown_output_path = os.path.join(output_subdir_markdown, f"{url_filename}.md")

    return markdown_output_path


def create_safe_filename(url: str) -> str:
    """
    Generates a safe filename from a given URL by removing protocol,
    replacing special characters, and limiting length.
    """
    filename = url.replace("https://", "").replace("http://", "")
    filename = filename.replace("/", "_").replace("?", "_").replace("&", "_")
    filename = filename.replace(":", "_").replace("=", "_").replace(".", "_")

    # Limit length and ensure it's not empty
    filename = filename[:100] if len(filename) > 100 else filename
    return filename or "content"


import time

def scrape_urls_batch(urls: List[str], base_url: str = "http://localhost:3002", firecrawl_user: str = None, firecrawl_pass: str = None) -> dict:
    """
    Submits a batch of URLs for scraping to the Firecrawl API and polls for results.
    Handles authentication and returns structured results including successful and failed scrapes.
    """
    successful_results = []
    failed_count = 0
    total_urls = len(urls)

    logger.info(f"Starting batch scrape of {total_urls} URLs using Firecrawl at {base_url}...")

    headers = {"Content-Type": "application/json"}
    if firecrawl_user and firecrawl_pass:
        import base64
        auth_string = f"{firecrawl_user}:{firecrawl_pass}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        headers["Authorization"] = f"Basic {encoded_auth}"
        logger.debug("Using basic authentication for Firecrawl")

    # Step 1: Submit batch scrape job
    try:
        batch_request_body = {
            "urls": urls,
            "formats": ["markdown"]
        }
        batch_response = requests.post(
            f"{base_url}/v2/batch/scrape", # Correct endpoint for batch submission
            json=batch_request_body,
            headers=headers,
            timeout=120
        )
        batch_response.raise_for_status()
        batch_data = batch_response.json()

        if not batch_data.get('success') or 'id' not in batch_data:
            logger.error(f"Failed to submit batch job: {batch_data.get('message', 'Unknown error')}")
            return {"success": 0, "failed": total_urls, "data": []}

        job_id = batch_data['id']
        logger.info(f"Batch job submitted. Job ID: {job_id}. Polling for results...")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error submitting batch job to Firecrawl: {e}")
        return {"success": 0, "failed": total_urls, "data": []}
    except Exception as e:
        logger.error(f"Unexpected error submitting batch job: {e}")
        return {"success": 0, "failed": total_urls, "data": []}

    # Step 2: Poll for job status
    status_url = f"{base_url}/v2/crawl/{job_id}" # Endpoint to check job status and get results
    
    while True:
        try:
            status_response = requests.get(status_url, headers=headers, timeout=60)
            status_response.raise_for_status()
            status_data = status_response.json()

            current_status = status_data.get('status')
            logger.info(f"Batch job {job_id} status: {current_status}")

            if current_status == "completed":
                # Step 3: Process results
                if 'data' in status_data and status_data['data']:
                    for item in status_data['data']:
                        url = item.get('metadata', {}).get('sourceURL')
                        if 'markdown' in item and item['markdown']:
                            formatted_result = {
                                'markdown': item['markdown'],
                                'metadata': item.get('metadata', {
                                    'sourceURL': url,
                                    'title': item.get('metadata', {}).get('title', ''),
                                    'description': item.get('metadata', {}).get('description', ''),
                                    'language': item.get('metadata', {}).get('language', 'en')
                                })
                            }
                            successful_results.append(formatted_result)
                            logger.debug(f"Successfully scraped: {url}")
                        else:
                            failed_count += 1
                            logger.warning(f"No markdown content found for: {url}")
                else:
                    logger.warning(f"Batch job {job_id} completed, but no data received.")
                break # Exit loop if completed
            elif current_status in ["active", "pending", "scraping"]:
                time.sleep(5) # Wait 5 seconds before polling again
            else:
                logger.error(f"Batch job {job_id} failed or returned unexpected status: {current_status}")
                failed_count = total_urls - len(successful_results)
                break

        except requests.exceptions.RequestException as e:
            logger.error(f"Error polling batch job status for {job_id}: {e}")
            failed_count = total_urls - len(successful_results)
            break
        except Exception as e:
            logger.error(f"Unexpected error during batch job status polling: {e}")
            failed_count = total_urls - len(successful_results)
            break

    logger.info(f"Batch scrape completed. Success: {len(successful_results)}, Failed: {failed_count}")

    return {
        "success": len(successful_results),
        "failed": failed_count,
        "data": successful_results
    }



def main(input_dir='dataset/acquisition/temp/urls', output_dir='dataset/acquisition/temp/datasources', verbose: bool = False, force_local: bool = False) -> List[Dict[str, Any]]:
    """
    Main asynchronous function to run the webpage scraper using Firecrawl.
    Orchestrates finding JSON files, extracting URLs, batch scraping, and saving results.
    """

    # Set up logging based on verbose flag
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Read configuration
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Get Firecrawl settings from config
    firecrawl_url = config.get('DEFAULT', 'firecrawl_url', fallback='http://localhost:3002')
    firecrawl_user = config.get('DEFAULT', 'firecrawl_user', fallback='')
    firecrawl_pass = config.get('DEFAULT', 'firecrawl_pass', fallback='')

    # Override with local if forced
    if force_local:
        firecrawl_url = 'http://localhost:3002'
        firecrawl_user = ''
        firecrawl_pass = ''
        logger.info("Forcing local Firecrawl instance usage")

    logger.debug(f"Firecrawl URL: {firecrawl_url}")
    if firecrawl_user:
        logger.debug("Using authentication for Firecrawl")

    # Validate input directory
    if not validate_directory(input_dir):
        logger.error(f"Input directory does not exist or is not a directory: {input_dir}")
        return []

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    logger.debug("Starting Firecrawl webpage scraper")
    logger.debug(f"Input directory: {input_dir}")
    logger.debug(f"Output directory: {output_dir}")

    try:
        # Find all JSON files
        json_files = find_json_files(input_dir)
        logger.debug(f"Found {len(json_files)} JSON files in '{input_dir}'")

        if not json_files:
            logger.warning("No JSON files found in input directory. Exiting.")
            return []

        # Collect all URLs and their associated metadata from all JSON files
        all_urls = []
        # Store full metadata for each URL: {"url": "...", "categoryName": "...", "question": "...", "input_file": "..."}
        url_metadata_mapping = {}
        collected_metadata = [] # Initialize list to collect all metadata

        for json_file in json_files:
            try:
                url_info_list = extract_urls_from_json_file(json_file)
                for item in url_info_list:
                    url = item["url"]
                    is_pdf = item["is_pdf"]
                    if not is_pdf:  # Skip PDFs for now as Firecrawl handles web content
                        all_urls.append(url)
                        url_metadata_mapping[url] = {
                            "categoryName": item["categoryName"],
                            "question": item["question"],
                            "input_file": json_file
                        }
                    else:
                        logger.info(f"Skipping PDF URL (not supported by Firecrawl batch scraping): {url}")
            except Exception as e:
                logger.error(f"Error reading JSON file {json_file}: {e}")

        logger.debug(f"Extracted {len(all_urls)} URLs for content scraping.")
        if not all_urls:
            logger.warning("No URLs found for content scraping. Exiting.")
            return [] # Return empty list if no URLs

        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(all_urls))
        if len(unique_urls) < len(all_urls):
            logger.info(f"Removed {len(all_urls) - len(unique_urls)} duplicate URLs")

        # Perform batch scraping
        batch_result = scrape_urls_batch(unique_urls, firecrawl_url, firecrawl_user, firecrawl_pass)

        # Save successful results to files and collect metadata
        for scraped_data in batch_result["data"]:
            try:
                url = scraped_data.get('metadata', {}).get('sourceURL', '')
                if not url:
                    continue

                # Retrieve full metadata for this URL
                metadata_from_input = url_metadata_mapping.get(url, {})
                input_file = metadata_from_input.get("input_file", json_files[0]) # Fallback

                # Create output path for markdown
                markdown_output_path = create_output_path(input_file, url, input_dir, output_dir)
                Path(markdown_output_path).parent.mkdir(parents=True, exist_ok=True)

                # Save markdown content
                with open(markdown_output_path, "w", encoding='utf-8') as f:
                    f.write(scraped_data.get('markdown', ''))

                logger.debug(f"Successfully saved content: {markdown_output_path}")

                # Prepare metadata for this entry
                entry_metadata = {
                    "categoryName": metadata_from_input.get("categoryName", "Uncategorized"),
                    "question": metadata_from_input.get("question", "No Question"),
                    "contentFilePath": os.path.relpath(markdown_output_path, output_dir), # Relative path to markdown
                    "url": url,
                    "sourceType": "web", # Added to indicate source is from the web
                    "questionCount": 0 # Initial count, to be updated later
                }
                collected_metadata.append(entry_metadata)

            except Exception as e:
                logger.error(f"Failed to save content or collect metadata for URL {url}: {e}")

        logger.info(f"Firecrawl scraper completed. Total URLs processed: {len(unique_urls)}, Successfully scraped: {len(collected_metadata)} URLs.")

        return collected_metadata # Return the list of collected metadata

    except Exception as e:
        logger.critical(f"An unexpected error occurred in Firecrawl scraper: {e}", exc_info=True)
        return [] # Return empty list on critical error


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape content from URLs using Firecrawl API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=""
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

    parser.add_argument(
        "--force-local",
        action="store_true",
        help="Force usage of local Firecrawl instance (localhost:3002) regardless of config"
    )

    args = parser.parse_args()
    result = main(args.input_dir, args.output_dir, args.verbose, args.force_local)
    print(f"Scraping completed: {len(result)} successful entries.")