import argparse
import sys
from pathlib import Path
from multiprocessing import Pool, cpu_count
from functools import partial
import pytesseract
import shutil
from .ocr_processor import process_file
from .text_cleaner import init_language_tool, FAST_MODE


import logging
import sys # Import sys for StreamHandler

# Use the global logger configuration
logger = logging.getLogger(__name__)

# Reduce verbosity of third-party libraries
logging.getLogger('PIL').setLevel(logging.WARNING)
logging.getLogger('multiprocessing').setLevel(logging.WARNING)
logging.getLogger('language_tool_python').setLevel(logging.WARNING)


def main(input_dir: str, output_dir: str, accurate: bool = False, verbose: bool = False):
    """
    Main function for the OCR tool to extract text from images.

    Args:
        input_dir (str): Input directory containing PNG/TIFF files.
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

    logger.info(f"Starting screenshot processing from: {input_path} to: {output_path}")

    # Get list of files (PNG, TIFF, and PDF)
    if input_path.is_file():
        if input_path.suffix.lower() not in ['.png', '.tiff', '.tif', '.pdf']:
            logger.error("Error: Input file must be a PNG, TIFF, or PDF file")
            return
        files = [input_path]
    else:
        png_files = list(input_path.glob('**/*.png'))
        tiff_files = list(input_path.glob('**/*.tiff')) + list(input_path.glob('**/*.tif'))
        pdf_files = list(input_path.glob('**/*.pdf'))
        files = png_files + tiff_files + pdf_files

    if not files:
        logger.warning("No PNG, TIFF, or PDF files found in the specified path. Exiting.")
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


# Set Tesseract-OCR path if not in PATH
if shutil.which("tesseract") is None:
    TESSERACT_PATH = '/usr/bin/tesseract'
    if Path(TESSERACT_PATH).exists():
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    else:
        logger.error("Tesseract-OCR is not found. Please install it or specify its path.")
        logger.error("  On Debian/Ubuntu: sudo apt-get install tesseract-ocr")
        logger.error("  On macOS: brew install tesseract")
        logger.error("  On Windows: Install from https://tesseract-ocr.github.io/tessdoc/Downloads.html and add to PATH.")
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OCR tool to extract text from images')
    parser.add_argument('input', help='Input image file or directory containing PNG/TIFF files')
    parser.add_argument('-o', '--output', help='Output directory for text files (default: same as input)')
    parser.add_argument('--accurate', action='store_true', help='Use more accurate but slower processing')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()

    # Set output directory if not provided
    output_dir = args.output if args.output else Path(args.input).parent

    main(args.input, output_dir, args.accurate, args.verbose)