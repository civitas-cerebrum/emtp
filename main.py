#!/usr/bin/env python3
"""
EMTP Main Pipeline - Interactive Session

This script provides an interactive interface to run individual stages
of the data acquisition pipeline with customizable input/output paths.
"""

import os
import sys
import argparse
import asyncio
import logging
import yaml
from contextlib import contextmanager

from dataset.acquisition import retrieve_url_stage, save_datasource_stage, datasource_processing_stage
from dataset.enrichment import qa_generation

main_logger = logging.getLogger("main_pipeline")

@contextmanager
def suppress_stdout_stderr():
    """A context manager to suppress stdout and stderr."""
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

def configure_logging(verbose: bool = False):
    """Configures logging for the application."""
    # Set basicConfig level to INFO when not verbose, to allow main_logger.info messages
    log_level = logging.DEBUG if verbose else logging.CRITICAL
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    # Aggressively suppress third-party libraries
    logging.getLogger('pydoll').setLevel(logging.CRITICAL)
    logging.getLogger('PIL').setLevel(logging.CRITICAL)
    logging.getLogger('multiprocessing').setLevel(logging.CRITICAL)
    logging.getLogger('language_tool_python').setLevel(logging.CRITICAL)
    logging.getLogger('asyncio').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    logging.getLogger('websockets').setLevel(logging.CRITICAL)
    logging.getLogger('selenium').setLevel(logging.CRITICAL)
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.getLogger('ddgs').setLevel(logging.CRITICAL)
    logging.getLogger('pydoll.connection').setLevel(logging.CRITICAL)
    logging.getLogger('pydoll.browser').setLevel(logging.CRITICAL)
    
    # Set main_logger level to INFO when not verbose
    main_logger.setLevel(logging.INFO if not verbose else logging.DEBUG)

def ensure_dir(path):
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)

def load_denied_domains(file_path):
    """Loads a list of denied domains from a YAML file."""
    try:
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f)
            # Assuming 'domain_exclusion_list' is a list as per the YAML structure
            domain_list_entries = config.get('domain_exclusion_list', [])
            domains = []
            for entry in domain_list_entries:
                if isinstance(entry, dict) and 'domains' in entry:
                    domains.extend(entry['domains'])
            return domains
    except FileNotFoundError:
        main_logger.warning(f"Denied domains file not found at {file_path}. No domains will be excluded.")
        return []
    except yaml.YAMLError as e:
        main_logger.error(f"Error parsing denied domains YAML file {file_path}: {e}")
        return []

def run_url_retrieval(questions_file='sample.json', output_dir='dataset/acquisition/temp/urls', verbose: bool = False, dorks: str = None, denied_domains: list = None):
    """Run URL retrieval stage."""
    main_logger.info(f"Starting URL retrieval with input {questions_file} to output {output_dir}...")
    ensure_dir(output_dir)
    filename_only = os.path.basename(questions_file)
    try:
        with suppress_stdout_stderr(): # Apply suppression here
            result = retrieve_url_stage(output_dir=output_dir, questions_file=filename_only, verbose=verbose, dorks=dorks, denied_domains=denied_domains)
        if isinstance(result, dict) and "success" in result and "failed" in result:
            main_logger.info(f"URL retrieval completed. {result['success']} URLs found, {result['failed']} failed.")
            return result
        else:
            main_logger.error("URL retrieval returned an unexpected format.")
            main_logger.debug(f"URL retrieval raw result: {result}") # Debugging unexpected format
            return {"success": 0, "failed": 1}
    except Exception as e:
        main_logger.error(f"URL retrieval failed: {e}")
        return {"success": 0, "failed": 1}

async def run_datasource_capture(input_dir='dataset/acquisition/temp/urls', output_dir='dataset/acquisition/temp/datasources', verbose: bool = False):
    """Run datasource capture stage."""
    main_logger.info(f"Starting datasource capture from {input_dir} to {output_dir}...")
    ensure_dir(output_dir)
    try:
        with suppress_stdout_stderr(): # Suppress all output during this stage
            result = await save_datasource_stage(input_dir=input_dir, output_dir=output_dir, verbose=verbose)
        if isinstance(result, dict) and "success" in result and "failed" in result:
            main_logger.info(f"Datasource capture completed. {result['success']} datasources captured, {result['failed']} failed.")
            return result
        else:
            main_logger.error("Datasource capture returned an unexpected format.")
            main_logger.debug(f"Datasource capture raw result: {result}") # Debugging unexpected format
            return {"success": 0, "failed": 1}
    except Exception as e:
        main_logger.error(f"Datasource capture failed: {e}")
        return {"success": 0, "failed": 1}

def run_datasource_processing(input_dir='dataset/acquisition/temp/datasources', output_dir='dataset/acquisition/temp/text_data', verbose: bool = False, accurate: bool = False):
    """Run datasource processing stage."""
    main_logger.info(f"Starting datasource processing from {input_dir} to {output_dir}...")
    ensure_dir(output_dir)
    try:
        with suppress_stdout_stderr(): # Apply suppression here
            result = datasource_processing_stage(input_dir, output_dir, verbose=verbose, accurate=accurate)
        if isinstance(result, dict) and "success" in result and "failed" in result:
            main_logger.info(f"Datasource processing completed. {result['success']} files processed, {result['failed']} failed.")
            return result
        else:
            main_logger.error("Datasource processing returned an unexpected format.")
            main_logger.debug(f"Datasource processing raw result: {result}") # Debugging unexpected format
            return {"success": 0, "failed": 1}
    except Exception as e:
        main_logger.error(f"Datasource processing failed: {e}")
        return {"success": 0, "failed": 1}

async def run_semi_sythetic_data_generation(input_dir='dataset/acquisition/temp/text_data'):
    """Run Q&A generation stage."""
    main_logger.info(f"Starting semi-synthetic data generation based on {input_dir}...")
    ensure_dir(input_dir)
    try:
        with suppress_stdout_stderr(): # Apply suppression here
            result = await qa_generation(input_dir)
        if isinstance(result, dict) and "success" in result and "failed" in result:
            main_logger.info(f"Semi-synthetic data generation completed. {result['success']} Q&A pairs generated, {result['failed']} failed.")
            return result
        else:
            main_logger.error("Semi-synthetic data generation returned an unexpected format.")
            main_logger.debug(f"Semi-synthetic data generation raw result: {result}") # Debugging unexpected format
            return {"success": 0, "failed": 1}
    except Exception as e:
        main_logger.error(f"Semi-synthetic data generation failed: {e}")
        return {"success": 0, "failed": 1}

# --- Helper for ASCII Table ---
def print_ascii_table(data):
    """Prints data in a simple ASCII table format."""
    if not data:
        return

    headers = list(data[0].keys())
    # Calculate maximum column widths
    column_widths = {header: len(header) for header in headers}
    for row in data:
        for header in headers:
            column_widths[header] = max(column_widths[header], len(str(row.get(header, ''))))

    # Print header
    header_line = "| " + " | ".join(header.ljust(column_widths[header]) for header in headers) + " |"
    separator_line = "+-" + "-+-".join("-" * column_widths[header] for header in headers) + "-+"
    
    main_logger.info(separator_line)
    main_logger.info(header_line)
    main_logger.info(separator_line)

    # Print rows
    for row in data:
        row_line = "| " + " | ".join(str(row.get(header, '')).ljust(column_widths[header]) for header in headers) + " |"
        main_logger.info(row_line)
    main_logger.info(separator_line)

# --- Interactive and CLI mode functions ---
def get_user_choice():
    """Get user's choice for which stage to run."""
    main_logger.info("\n" + "="*50)
    main_logger.info("EMTP Data Acquisition Pipeline")
    main_logger.info("="*50)
    main_logger.info("Choose a stage to run:")
    main_logger.info("1. URL Retrieval (from questions to URLs)")
    main_logger.info("2. Datasource Capture (from URLs to data sources)")
    main_logger.info("3. Datasource Processing (from data sources to text)")
    main_logger.info("4. Run Full Pipeline (all stages)")
    main_logger.info("5. Exit")
    main_logger.info("="*50)

    while True:
        try:
            choice = input("Enter your choice (1-5): ").strip()
            if choice in ['1', '2', '3', '4', '5']:
                return choice
            else:
                main_logger.warning("Invalid choice. Please enter 1, 2, 3, 4, or 5.")
        except KeyboardInterrupt:
            main_logger.info("\nExiting...")
            return '5' # Changed to '5' for exit

def get_path_input(prompt, default):
    """Get path input from user with default."""
    path = input(f"{prompt} (default: {default}): ").strip()
    return path if path else default

def get_log_level_input():
    """Get log level input from user."""
    while True:
        log_level_str = input("Enter log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) [INFO]: ").strip().upper()
        if log_level_str in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', '']:
            return log_level_str if log_level_str else 'INFO'
        else:
            main_logger.warning("Invalid log level. Please choose from DEBUG, INFO, WARNING, ERROR, CRITICAL.")

async def main():
    """Main interactive loop or direct execution via arguments."""
    parser = argparse.ArgumentParser(description="EMTP Data Acquisition Pipeline")
    parser.add_argument('--stage', type=str, choices=['url_retrieval', 'datasource_capture', 'datasource_processing', 'full_pipeline'],
                        help='Specify the pipeline stage to run directly (non-interactive mode).')
    parser.add_argument('--questions-file', type=str, default='sample.json',
                        help='Path to the questions JSON file.')
    parser.add_argument('--urls-output-dir', type=str, default='dataset/acquisition/temp/urls',
                        help='Output directory for URLs.')
    parser.add_argument('--datasources-output-dir', type=str, default='dataset/acquisition/temp/datasources',
                        help='Output directory for data sources.')
    parser.add_argument('--text-data-output-dir', type=str, default='dataset/acquisition/temp/text_data',
                        help='Output directory for text data.')
    parser.add_argument('--accurate', action='store_true',
                        help='Use more accurate (slower) processing for screenshot processing.')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging.')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the logging level.')
    parser.add_argument('--dorks', type=str,
                        help='DuckDuckGo search operators to apply to all URL retrieval searches (e.g., "filetype:pdf site:example.com").')

    args = parser.parse_args()

    # Configure logging based on verbose flag
    configure_logging(verbose=args.verbose)

    # Load denied domains once
    denied_domains_file = 'dataset/acquisition/retrieve_url/denied-domains.yaml'
    denied_domains = load_denied_domains(denied_domains_file)


    if args.stage:
        # Non-interactive mode
        if args.stage == 'url_retrieval':
            run_url_retrieval(args.questions_file, args.urls_output_dir, verbose=args.verbose, dorks=args.dorks, denied_domains=denied_domains)
        elif args.stage == 'datasource_capture':
            await run_datasource_capture(args.urls_output_dir, args.datasources_output_dir, verbose=args.verbose)
        elif args.stage == 'datasource_processing':
            run_datasource_processing(args.datasources_output_dir, args.text_data_output_dir, verbose=args.verbose, accurate=args.accurate)
        elif args.stage == 'full_pipeline':
            main_logger.info("Running full pipeline...")
            pipeline_results = []

            # Stage 1: URL Retrieval
            url_retrieval_status = run_url_retrieval(args.questions_file, args.urls_output_dir, verbose=args.verbose, dorks=args.dorks, denied_domains=denied_domains)
            pipeline_results.append({"Stage": "URL Retrieval", "Status": "✅ Success" if url_retrieval_status["failed"] == 0 else "❌ Failed", "Details": f"{url_retrieval_status['success']} URLs found, {url_retrieval_status['failed']} questions failed"})

            # Stage 2: Datasource Capture
            datasource_capture_status = await run_datasource_capture(args.urls_output_dir, args.datasources_output_dir, verbose=args.verbose)
            pipeline_results.append({"Stage": "Datasource Capture", "Status": "✅ Success" if datasource_capture_status["failed"] == 0 else "❌ Failed", "Details": f"{datasource_capture_status['success']} captured, {datasource_capture_status['failed']} failed"})

            # Stage 3: Datasource Processing
            datasource_processing_status = run_datasource_processing(args.datasources_output_dir, args.text_data_output_dir, verbose=args.verbose, accurate=args.accurate)
            pipeline_results.append({"Stage": "Datasource Processing", "Status": "✅ Success" if datasource_processing_status["failed"] == 0 else "❌ Failed", "Details": f"{datasource_processing_status['success']} processed, {datasource_processing_status['failed']} failed"})

            # Stage 4: Semi-synthetic Data Generation
            qa_generation_status = await run_semi_sythetic_data_generation(args.text_data_output_dir)
            pipeline_results.append({"Stage": "Semi-synthetic Data Gen", "Status": "✅ Success" if qa_generation_status["failed"] == 0 else "❌ Failed", "Details": f"{qa_generation_status['success']} generated, {qa_generation_status['failed']} failed"})

            main_logger.info("\n🎉 Full pipeline completed!")
            print_ascii_table(pipeline_results) # Print the ASCII table summary

            main_logger.debug(f"Intermediate URLs saved to: {args.urls_output_dir}")
            main_logger.debug(f"Intermediate data sources saved to: {args.datasources_output_dir}")
            main_logger.debug(f"Final text data saved to: {args.text_data_output_dir}")
    else:
        # Interactive mode
        main_logger.info("Welcome to EMTP Data Acquisition Pipeline!")
        while True:
            choice = get_user_choice()

            if choice == '5':
                main_logger.info("Goodbye!")
                break
            
            # The verbose flag from CLI will control logging, not interactive input
            # log_level = get_log_level_input()
            # verbose_logging = (log_level == 'DEBUG') # Set verbose true only for DEBUG

            if choice == '1':
                # URL Retrieval
                questions_file = get_path_input("Questions file path", "sample.json")
                output_dir = get_path_input("Output directory for URLs", "dataset/acquisition/temp/urls")
                run_url_retrieval(questions_file, output_dir, verbose=args.verbose, denied_domains=denied_domains)

            elif choice == '2':
                # Datasource Capture
                input_dir = get_path_input("Input directory with URLs", "dataset/acquisition/temp/urls")
                output_dir = get_path_input("Output directory for data sources", "dataset/acquisition/temp/datasources")
                await run_datasource_capture(input_dir, output_dir, verbose=args.verbose)

            elif choice == '3':
                # Datasource Processing
                input_dir = get_path_input("Input directory with data sources", "dataset/acquisition/temp/datasources")
                output_dir = get_path_input("Output directory for text data", "dataset/acquisition/temp/text_data")
                run_datasource_processing(input_dir, output_dir, verbose=args.verbose, accurate=True) # Automatically use accurate mode
            elif choice == '4':
                # Full Pipeline
                main_logger.info("Running full pipeline...")
                pipeline_results = []

                # Stage 1: URL Retrieval
                url_retrieval_status = run_url_retrieval(args.questions_file, args.urls_output_dir, verbose=args.verbose, dorks=args.dorks, denied_domains=denied_domains)
                pipeline_results.append({"Stage": "URL Retrieval", "Status": "✅ Success" if url_retrieval_status["failed"] == 0 else "❌ Failed", "Details": f"{url_retrieval_status['success']} URLs found, {url_retrieval_status['failed']} questions failed"})

                # Stage 2: Datasource Capture
                datasource_capture_status = await run_datasource_capture(urls_temp, datasources_temp, verbose=args.verbose)
                pipeline_results.append({"Stage": "Datasource Capture", "Status": "✅ Success" if datasource_capture_status["failed"] == 0 else "❌ Failed", "Details": f"{datasource_capture_status['success']} captured, {datasource_capture_status['failed']} failed"})

                # Stage 3: Datasource Processing
                datasource_processing_status = run_datasource_processing(datasources_temp, final_text_output, verbose=args.verbose, accurate=True)
                pipeline_results.append({"Stage": "Datasource Processing", "Status": "✅ Success" if datasource_processing_status["failed"] == 0 else "❌ Failed", "Details": f"{datasource_processing_status['success']} processed, {datasource_processing_status['failed']} failed"})

                # Stage 4: Semi-synthetic Data Generation
                qa_generation_status = await run_semi_sythetic_data_generation(final_text_output) # Use final_text_output as input
                pipeline_results.append({"Stage": "Semi-synthetic Data Gen", "Status": "✅ Success" if qa_generation_status["failed"] == 0 else "❌ Failed", "Details": f"{qa_generation_status['success']} generated, {qa_generation_status['failed']} failed"})

                main_logger.info("\n🎉 Full pipeline completed!")
                print_ascii_table(pipeline_results) # Print the ASCII table summary

                main_logger.debug(f"Intermediate URLs saved to: {urls_temp}")
                main_logger.debug(f"Intermediate data sources saved to: {datasources_temp}")
                main_logger.debug(f"Final text data saved to: {final_text_output}")

if __name__ == "__main__":
    configure_logging(verbose=False) # Default to non-verbose
    asyncio.run(main())