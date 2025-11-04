import argparse
import sys
from pathlib import Path
from multiprocessing import Pool, cpu_count
from functools import partial
from .text_processor import process_file
from .text_cleaner import init_language_tool, FAST_MODE


import logging
import sys # Import sys for StreamHandler

# Use the global logger configuration
logger = logging.getLogger(__name__)

# Reduce verbosity of third-party libraries
logging.getLogger('multiprocessing').setLevel(logging.WARNING)
logging.getLogger('language_tool_python').setLevel(logging.WARNING)


def main(input_dir: str, output_dir: str, accurate: bool = False, verbose: bool = False):
    """
    Main function for the text extraction tool to process markdown files.

    Args:
        input_dir (str): Input directory containing markdown files.
        output_dir (str): Output directory for text files.
        accurate (bool): Use more accurate but slower processing.
        verbose (bool): Enable verbose logging.
    """
    # Set logging level for this call
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Set processing mode
    global FAST_MODE
    FAST_MODE = not accurate

    # Initialize language tool if needed
    if not FAST_MODE:
        init_language_tool()

    # Handle input path
    input_path = Path(input_dir)
    if not input_path.exists():
        logger.error(f"Input path '{input_path}' does not exist")
        return

    # Set output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting markdown processing from: {input_path} to: {output_path}")

    # Get list of files (Markdown files)
    if input_path.is_file():
        if input_path.suffix.lower() != '.md':
            logger.error("Error: Input file must be a Markdown (.md) file")
            return
        files = [input_path]
    else:
        md_files = list(input_path.glob('**/*.md'))
        files = md_files

    if not files:
        logger.warning("No Markdown (.md) files found in the specified path. Exiting.")
        return

    total_start_time = __import__('time').time()

    # Process files in parallel
    with Pool(processes=min(cpu_count(), len(files))) as pool:
        process_func = partial(process_file, output_dir=output_path, use_language_tool=not FAST_MODE)
        results = pool.map(process_func, [str(f) for f in files])

    # Log results
    successful_results = []
    for file_path, output_file, process_time in results:
        if output_file:
            logger.debug(f"Processed {file_path} -> {output_file} (took {process_time:.2f} seconds)")
            successful_results.append((file_path, output_file, process_time))
        else:
            logger.warning(f"Failed to process {file_path}. No output file generated.")

    total_time = __import__('time').time() - total_start_time
    logger.info(f"\nTotal processing time: {total_time:.2f} seconds for {len(successful_results)} successfully processed file(s) out of {len(files)}.")
    if len(successful_results) == 0:
        logger.warning("No text files were successfully processed. No output will be available for subsequent stages.")

    # Only return successful_results to avoid issues in later stages
    return successful_results


# No OCR dependencies needed for markdown processing

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Text extraction tool to process markdown files')
    parser.add_argument('input', help='Input markdown file or directory containing .md files')
    parser.add_argument('-o', '--output', help='Output directory for text files (default: same as input)')
    parser.add_argument('--accurate', action='store_true', help='Use more accurate but slower processing')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()

    # Set output directory if not provided
    output_dir = args.output if args.output else Path(args.input).parent

    main(args.input, output_dir, args.accurate, args.verbose)