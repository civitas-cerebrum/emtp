#!/usr/bin/env python3
"""
Webpage Screenshotter - Capture screenshots of URLs from JSON files.

This script reads JSON files from an input directory, extracts URLs,
navigates to each URL using a headless browser, and saves full-page
screenshots as PNG files.
"""

import argparse
import os
import sys
import logging
from pathlib import Path
from typing import List
import queue
import threading
 
from .file_finder import find_json_files, validate_directory
from .json_parser import extract_urls_from_json_file
from .screenshot_capture import ScreenshotCapture
from .image_processor import process_screenshot_for_png


#!/usr/bin/env python3
"""
Webpage Screenshotter - Capture screenshots of URLs from JSON files.

This script reads JSON files from an input directory, extracts URLs,
navigates to each URL using a headless browser, and saves full-page
screenshots as PNG files.
"""

import argparse
import os
import sys
import logging
from pathlib import Path
from typing import List
import queue
import threading
 
from .file_finder import find_json_files, validate_directory
from .json_parser import extract_urls_from_json_file
from .screenshot_capture import ScreenshotCapture
from .image_processor import process_screenshot_for_png

# Configure logging for the module
logger = logging.getLogger(__name__)
if not logger.handlers:
    # Only add handler if not already configured to prevent duplicate messages
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def create_output_path(input_file: str, url: str, input_dir: str, output_dir: str) -> str:
    """
    Create the output path for a screenshot, mirroring the input structure.

    Args:
        input_file (str): Path to the input JSON file.
        url (str): The URL being captured.
        input_dir (str): The input directory.
        output_dir (str): The output directory.

    Returns:
        str: The output path for the screenshot.
    """
    # Get relative path from input directory
    rel_path = os.path.relpath(input_file, input_dir)

    # Remove .json extension and create directory structure
    rel_dir = os.path.splitext(rel_path)[0]

    # Create a safe filename from URL
    url_filename = create_safe_filename(url)

    # Combine paths
    output_subdir = os.path.join(output_dir, rel_dir)
    output_path = os.path.join(output_subdir, f"{url_filename}.png")

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
    return filename or "screenshot"


def worker(q: queue.Queue, input_dir: str, output_dir: str, headless: bool, timeout: int, total_screenshots: List[int]):
    """Worker function to process URLs from the queue."""
    with ScreenshotCapture(headless=headless, timeout=timeout) as capturer:
        while True:
            try:
                item = q.get()
                if item is None:
                    break

                url, json_file = item
                logger.info(f"Attempting to capture screenshot for: {url}")

                try:
                    # Capture screenshot
                    screenshot_bytes = capturer.capture_full_page_screenshot(url)
                    output_path = create_output_path(json_file, url, input_dir, output_dir)
                    process_screenshot_for_png(screenshot_bytes, output_path)
                    logger.info(f"Successfully saved screenshot: {output_path}")

                    total_screenshots.append(1)
                except Exception as e:
                    logger.error(f"Failed to capture screenshot for {url}: {e}")
                finally:
                    q.task_done()
            except queue.Empty:
                continue


def main(input_dir='dataset/acquisition/temp/urls', output_dir='dataset/acquisition/temp/screenshots', timeout=30, verbose: bool = False, headless=True, workers=4): # Added type hint for verbose
    """Main function to run the webpage screenshotter."""

    # Set up logging based on verbose flag
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Validate input directory
    if not validate_directory(input_dir):
        logger.error(f"Input directory does not exist or is not a directory: {input_dir}")
        return

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    logger.info("Starting webpage screenshotter")
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Page load timeout: {timeout} seconds")
    logger.info(f"Headless mode: {headless}")
    logger.info(f"Number of workers: {workers}")

    try:
        # Find all JSON files
        json_files = find_json_files(input_dir)
        logger.info(f"Found {len(json_files)} JSON files in '{input_dir}'")

        if not json_files:
            logger.warning("No JSON files found in input directory. Exiting.")
            return

        # Create a queue and populate it with URLs
        q = queue.Queue()
        total_urls = 0
        for json_file in json_files:
            try:
                urls = extract_urls_from_json_file(json_file)
                for url in urls:
                    q.put((url, json_file))
                    total_urls += 1
            except Exception as e:
                logger.error(f"Error reading JSON file {json_file}: {e}")
        
        logger.info(f"Extracted {total_urls} URLs for screenshot capture.")
        if total_urls == 0:
            logger.warning("No URLs found for screenshot capture. Exiting.")
            return


        total_screenshots = []
        threads = []

        # Create and start worker threads
        for i in range(workers):
            thread = threading.Thread(
                target=worker,
                args=(q, input_dir, output_dir, headless, timeout, total_screenshots),
                name=f"Worker-{i+1}"
            )
            thread.start()
            threads.append(thread)

        # Wait for all tasks to be processed
        q.join()

        # Stop workers
        for _ in range(workers):
            q.put(None)
        for thread in threads:
            thread.join()

        logger.info(f"Webpage screenshotter completed. Total screenshots captured: {len(total_screenshots)}")

    except KeyboardInterrupt:
        logger.info("Webpage screenshotter process interrupted by user.")
    except Exception as e:
        logger.critical(f"An unexpected error occurred in webpage screenshotter: {e}", exc_info=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Capture screenshots of URLs from JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py /path/to/input /path/to/output
  python main.py /path/to/input /path/to/output --verbose
  python main.py /path/to/input /path/to/output --timeout 60
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
        default='dataset/acquisition/temp/screenshots',
        help="Output directory where screenshots will be saved"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout for page loading in seconds (default: 30)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)"
    )

    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run browser in non-headless mode"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )

    args = parser.parse_args()
    main(args.input_dir, args.output_dir, args.timeout, args.verbose, args.headless, args.workers)