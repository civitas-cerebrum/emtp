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
import asyncio # Import asyncio
from asyncio import Queue as AsyncQueue # Use asyncio's Queue for async operations
import threading # Still needed for process management of the overall script

from .file_finder import find_json_files, validate_directory
from .json_parser import extract_urls_from_json_file
from .screenshot_capture import ScreenshotCapture
from .image_processor import process_screenshot_for_png

# Use the global logger configuration
logger = logging.getLogger(__name__)

# Reduce verbosity of third-party libraries
# Temporarily increase verbosity of third-party libraries for debugging
logging.getLogger('pydoll').setLevel(logging.INFO) # Changed from CRITICAL
logging.getLogger('pydoll.connection').setLevel(logging.INFO) # Added for more specific connection logging
logging.getLogger('pydoll.browser').setLevel(logging.INFO) # Added for more specific browser logging
logging.getLogger('websockets').setLevel(logging.INFO) # Changed from CRITICAL

# Original suppressions remain for other libraries
logging.getLogger('PIL').setLevel(logging.CRITICAL)
logging.getLogger('multiprocessing').setLevel(logging.CRITICAL)
logging.getLogger('language_tool_python').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.CRITICAL) # Keep asyncio suppressed to avoid its internal debug logs overwhelming output
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('selenium').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.CRITICAL)


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


async def worker(q: AsyncQueue, input_dir: str, output_dir: str, headless: bool, timeout: int, counters: dict):
   """Asynchronous worker function to process URLs from the queue."""
   async with ScreenshotCapture(headless=headless, timeout=timeout) as capturer:
       while True:
           try:
               item = await q.get()
               if item is None: # Sentinel for stopping the worker
                   break

               url, json_file, is_pdf_intended = item # is_pdf_intended means dorks specified filetype:pdf
               
               output_path_base = create_output_path(json_file, url, input_dir, output_dir)
               output_dir_path = Path(output_path_base).parent
               output_dir_path.mkdir(parents=True, exist_ok=True) # Ensure output directory exists

               logger.info(f"Processing URL: {url} (PDF intended: {is_pdf_intended})") # Changed to INFO for better visibility
               capture_successful = False

               if is_pdf_intended:
                   logger.debug(f"Attempting direct PDF download for {url}")
                   try:
                       pdf_bytes = await capturer.download_pdf(url)
                       final_output_path = output_path_base.replace('.png', '.pdf')
                       with open(final_output_path, "wb") as f:
                           f.write(pdf_bytes)
                       logger.info(f"✅ Successfully saved PDF (direct download): {final_output_path}") # Changed to INFO
                       capture_successful = True
                   except Exception as pdf_error:
                       logger.warning(f"⚠️ Failed direct PDF download for {url}: {pdf_error}. Attempting browser print to PDF.") # Changed to WARNING
                       # Fallback to browser print to PDF
                       try:
                           pdf_bytes = await capturer.print_to_pdf(url)
                           final_output_path = output_path_base.replace('.png', '.pdf')
                           with open(final_output_path, "wb") as f:
                               f.write(pdf_bytes)
                           logger.info(f"✅ Successfully saved PDF (browser print): {final_output_path}") # Changed to INFO
                           capture_successful = True
                       except Exception as browser_pdf_error:
                           logger.error(f"❌ Failed browser print to PDF for {url}: {browser_pdf_error}. No PDF saved.") # Changed to ERROR
               
               if not capture_successful and not is_pdf_intended:
                   logger.debug(f"Attempting screenshot capture for {url}")
                   # Capture screenshot if not PDF, or if PDF was not intended and previous attempts failed
                   try:
                       screenshot_bytes = await capturer.capture_full_page_screenshot(url)
                       final_output_path = output_path_base # This will retain the .png extension
                       with open(final_output_path, "wb") as f:
                           f.write(screenshot_bytes)
                       logger.info(f"✅ Successfully saved screenshot: {final_output_path}") # Changed to INFO
                       capture_successful = True
                   except Exception as screenshot_error:
                       logger.error(f"❌ Failed screenshot capture for {url}: {screenshot_error}. No screenshot saved.") # Changed to ERROR

               if capture_successful:
                   counters["success"] += 1
               else: # If capture was not successful, it's a failure
                   counters["failed"] += 1

               q.task_done()
           except asyncio.CancelledError:
               logger.debug(f"Worker cancelled.")
               break
           except Exception as e:
               logger.critical(f"An unexpected error occurred in worker for {url}: {e}", exc_info=True) # Added URL to critical log
               counters["failed"] += 1 # Ensure failure is counted for unexpected errors
               q.task_done()


async def main_async(input_dir='dataset/acquisition/temp/urls', output_dir='dataset/acquisition/temp/screenshots', timeout=30, verbose: bool = False, headless=True, workers=4):
   """Main asynchronous function to run the webpage screenshotter."""

   logger.setLevel(logging.DEBUG if verbose else logging.INFO) # Set up logging based on verbose flag

   if not validate_directory(input_dir):
       logger.error(f"Input directory does not exist or is not a directory: {input_dir}")
       return {"success": 0, "failed": 1}

   Path(output_dir).mkdir(parents=True, exist_ok=True)

   logger.info("Starting webpage screenshotter") # Changed to INFO
   logger.debug(f"Input directory: {input_dir}")
   logger.debug(f"Output directory: {output_dir}")
   logger.debug(f"Page load timeout: {timeout} seconds")
   logger.debug(f"Headless mode: {headless}")
   logger.debug(f"Number of workers: {workers}")

   counters = {"success": 0, "failed": 0}

   try:
       json_files = find_json_files(input_dir)
       logger.debug(f"Found {len(json_files)} JSON files in '{input_dir}'")

       if not json_files:
           logger.warning("No JSON files found in input directory. Exiting.")
           return {"success": 0, "failed": 0}

       q = AsyncQueue()
       total_urls_queued = 0
       for json_file in json_files:
           try:
               url_info_list = extract_urls_from_json_file(json_file)
               for url, is_pdf in url_info_list:
                   await q.put((url, json_file, is_pdf))
                   total_urls_queued += 1
           except Exception as e:
               logger.error(f"Error reading JSON file {json_file}: {e}")
               counters["failed"] += 1

       logger.info(f"Extracted {total_urls_queued} URLs for screenshot capture.") # Changed to INFO
       if total_urls_queued == 0:
           logger.warning("No URLs found for screenshot capture. Exiting.")
           return {"success": 0, "failed": 0}

       tasks = []
       for _ in range(workers):
           task = asyncio.create_task(
               worker(q, input_dir, output_dir, headless, timeout, counters)
           )
           tasks.append(task)

       await q.join()

       for _ in range(workers):
           await q.put(None)
       
       await asyncio.gather(*tasks, return_exceptions=True)

       logger.info(f"Webpage screenshotter completed. Total: {counters['success']} captured, {counters['failed']} failed.")
       return counters

   except asyncio.CancelledError:
       logger.info("Webpage screenshotter process interrupted by user (asyncio.CancelledError).")
       return counters
   except KeyboardInterrupt:
       logger.info("Webpage screenshotter process interrupted by user (KeyboardInterrupt).")
       return counters
   except Exception as e:
       logger.critical(f"An unexpected error occurred in webpage screenshotter: {e}", exc_info=True)
       return {"success": counters["success"], "failed": counters["failed"] + 1 if counters["failed"] == 0 else counters["failed"]}


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
   asyncio.run(main_async(args.input_dir, args.output_dir, args.timeout, args.verbose, args.headless, args.workers))


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
    asyncio.run(main_async(args.input_dir, args.output_dir, args.timeout, args.verbose, args.headless, args.workers))