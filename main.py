#!/usr/bin/env python3
"""
EMTP Main Pipeline - Interactive Session

This script provides an interactive interface to run individual stages
of the data acquisition pipeline with customizable input/output paths.
"""

import os
import sys
import argparse
import asyncio # Import asyncio for asynchronous operations
import logging
import json
from dataset.acquisition import retrieve_url_stage, save_datasource_stage
from dataset.enrichment import qa_generation

# Reduce verbosity of third-party libraries globally
logging.getLogger('pydoll').setLevel(logging.CRITICAL)
logging.getLogger('PIL').setLevel(logging.WARNING)
logging.getLogger('multiprocessing').setLevel(logging.WARNING)
logging.getLogger('language_tool_python').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('websockets').setLevel(logging.CRITICAL)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('pydoll.connection').setLevel(logging.CRITICAL)
logging.getLogger('pydoll.browser').setLevel(logging.CRITICAL)

def ensure_dir(path):
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)


def print_pipeline_report(urls_dir, datasources_dir, qa_file='qna_dataset.json'):
    """Print a simple ASCII report of pipeline results."""
    try:
        # Count URLs
        urls_count = 0
        if os.path.exists(urls_dir):
            for file in os.listdir(urls_dir):
                if file.endswith('.json'):
                    file_path = os.path.join(urls_dir, file)
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            # Handle different JSON structures
                            if isinstance(data, list):
                                # Array of objects, each with 'urls' field
                                for item in data:
                                    if isinstance(item, dict) and 'urls' in item:
                                        urls_count += len(item['urls'])
                            elif isinstance(data, dict) and 'urls' in data:
                                # Single object with 'urls' field
                                urls_count += len(data['urls'])
                            elif isinstance(data, list) and all(isinstance(url, str) for url in data):
                                # Simple array of URLs
                                urls_count += len(data)
                    except:
                        pass

        # Count markdown files
        markdown_count = 0
        if os.path.exists(datasources_dir):
            for root, dirs, files in os.walk(datasources_dir):
                markdown_count += len([f for f in files if f.endswith('.md')])

        # Count Q&A pairs
        qa_count = 0
        if os.path.exists(qa_file):
            try:
                with open(qa_file, 'r') as f:
                    qa_data = json.load(f)
                    qa_count = len(qa_data) if isinstance(qa_data, list) else 0
            except:
                pass

        # Print ASCII report
        print("\n" + "="*60)
        print("                    EMTP PIPELINE REPORT")
        print("="*60)
        print(f"  📊 URLs Retrieved:     {urls_count}")
        print(f"  📄 Markdown Files:     {markdown_count}")
        print(f"  ❓ Q&A Pairs Generated: {qa_count}")
        print("="*60)
        print("  ✅ Pipeline completed successfully!")
        print("="*60)

    except Exception as e:
        print(f"Note: Could not generate detailed report ({e})")

def run_url_retrieval(questions_file='sample.json', output_dir='dataset/acquisition/temp/urls', verbose: bool = False, dorks: str = None):
    """Run URL retrieval stage."""
    print(f"🔍 Starting URL retrieval...")
    print(f"  Input: {questions_file}")
    print(f"  Output: {output_dir}")
    ensure_dir(output_dir)
    # Assuming retrieve_url_stage accepts a verbose argument
    # Extract just the filename if a full path is provided
    filename_only = os.path.basename(questions_file)
    retrieve_url_stage(output_dir=output_dir, questions_file=filename_only, verbose=verbose, dorks=dorks)
    print(f"✅ URL retrieval completed! Results saved to {output_dir}")

async def run_datasource_capture(input_dir='dataset/acquisition/temp/urls', output_dir='dataset/acquisition/temp/datasources', verbose: bool = False):
    """Run datasource capture stage."""
    print(f"📸 Starting datasource capture...")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    ensure_dir(output_dir)
    # save_datasource_stage is now async
    await save_datasource_stage(input_dir=input_dir, output_dir=output_dir, verbose=verbose)
    print(f"✅ Datasource capture completed! Data sources saved to {output_dir}")

def run_datasource_processing(input_dir='dataset/acquisition/temp/datasources', output_dir='dataset/acquisition/temp/text_data', verbose: bool = False, accurate: bool = False):
    """Run datasource processing stage."""
    print(f"🔄 Starting datasource processing...")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    ensure_dir(output_dir)
    datasource_processing_stage(input_dir, output_dir, verbose=verbose, accurate=accurate) # Positional arguments
    print(f"✅ Datasource processing completed! Text data saved to {output_dir}")

async def run_semi_sythetic_data_generation(input_dir='dataset/acquisition/temp/datasources'):
    """Run Q&A generation stage."""
    print(f"🤖 Starting semi-sythetic data generation...")
    ensure_dir(input_dir)
    await qa_generation(input_dir) # qa_generation is now async
    print(f"✅ Semi-synthetic data generation completed based on markdown data from {input_dir}")

def get_user_choice():
    """Get user's choice for which stage to run."""
    print("\n" + "="*50)
    print("EMTP Data Acquisition Pipeline")
    print("="*50)
    print("Choose a stage to run:")
    print("1. URL Retrieval (from questions to URLs)")
    print("2. Datasource Capture (from URLs to markdown data sources)")
    print("3. Q&A Generation (from markdown data sources to Q&A dataset)")
    print("4. Run Full Pipeline (all stages)")
    print("5. Exit")
    print("="*50)

    while True:
        try:
            choice = input("Enter your choice (1-5): ").strip()
            if choice in ['1', '2', '3', '4', '5']:
                return choice
            else:
                print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")
        except KeyboardInterrupt:
            print("\nExiting...")
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
            print("Invalid log level. Please choose from DEBUG, INFO, WARNING, ERROR, CRITICAL.")

async def main():
    """Main interactive loop or direct execution via arguments."""
    parser = argparse.ArgumentParser(description="EMTP Data Acquisition Pipeline")
    parser.add_argument('--stage', type=str, choices=['url_retrieval', 'datasource_capture', 'qa_generation', 'full_pipeline'],
                        help='Specify the pipeline stage to run directly (non-interactive mode).')
    parser.add_argument('--questions-file', type=str, default='sample.json',
                        help='Path to the questions JSON file.')
    parser.add_argument('--urls-output-dir', type=str, default='dataset/acquisition/temp/urls',
                        help='Output directory for URLs.')
    parser.add_argument('--datasources-output-dir', type=str, default='dataset/acquisition/temp/datasources',
                        help='Output directory for data sources.')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging.')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the logging level.')
    parser.add_argument('--dorks', type=str,
                        help='DuckDuckGo search operators to apply to all URL retrieval searches (e.g., "filetype:pdf site:example.com").')

    args = parser.parse_args()

    # Determine verbose logging from --log-level or --verbose
    verbose_logging = args.verbose or (args.log_level == 'DEBUG')

    if args.stage:
        # Non-interactive mode
        if args.stage == 'url_retrieval':
            run_url_retrieval(args.questions_file, args.urls_output_dir, verbose=verbose_logging, dorks=args.dorks)
        elif args.stage == 'datasource_capture':
            await run_datasource_capture(args.urls_output_dir, args.datasources_output_dir, verbose=verbose_logging)
        elif args.stage == 'qa_generation':
            await run_semi_sythetic_data_generation(args.datasources_output_dir)
        elif args.stage == 'full_pipeline':
            print("Running full pipeline...")
            run_url_retrieval(args.questions_file, args.urls_output_dir, verbose=verbose_logging, dorks=args.dorks)
            await run_datasource_capture(args.urls_output_dir, args.datasources_output_dir, verbose=verbose_logging)
            await run_semi_sythetic_data_generation(args.datasources_output_dir) # Skip processing, read markdown directly
            print("🎉 Full pipeline completed!")
            print(f"Intermediate URLs saved to: {args.urls_output_dir}")
            print(f"Intermediate data sources saved to: {args.datasources_output_dir}")
            print(f"Q&A dataset generated from markdown files in: {args.datasources_output_dir}")
            print_pipeline_report(args.urls_output_dir, args.datasources_output_dir)
    else:
        # Interactive mode
        print("Welcome to EMTP Data Acquisition Pipeline!")
        while True:
            choice = get_user_choice()

            if choice == '5':
                print("Goodbye!")
                break
            
            log_level = get_log_level_input()
            verbose_logging = (log_level == 'DEBUG') # Set verbose true only for DEBUG

            if choice == '1':
                # URL Retrieval
                questions_file = get_path_input("Questions file path", "sample.json")
                output_dir = get_path_input("Output directory for URLs", "dataset/acquisition/temp/urls")
                run_url_retrieval(questions_file, output_dir, verbose=verbose_logging)

            elif choice == '2':
                # Datasource Capture
                input_dir = get_path_input("Input directory with URLs", "dataset/acquisition/temp/urls")
                output_dir = get_path_input("Output directory for data sources", "dataset/acquisition/temp/datasources")
                await run_datasource_capture(input_dir, output_dir, verbose=verbose_logging)

            elif choice == '3':
                # Q&A Generation
                input_dir = get_path_input("Input directory with markdown data sources", "dataset/acquisition/temp/datasources")
                await run_semi_sythetic_data_generation(input_dir)
            elif choice == '4':
                # Full Pipeline
                print("Running full pipeline...")

                # Get input path
                questions_file = get_path_input("Questions file path", "sample.json")

                # Use temp directories for intermediate data
                urls_temp = "dataset/acquisition/temp/urls"
                datasources_temp = "dataset/acquisition/temp/datasources"

                # Run URL retrieval
                run_url_retrieval(questions_file, urls_temp, verbose=verbose_logging)

                # Run datasource capture
                await run_datasource_capture(urls_temp, datasources_temp, verbose=verbose_logging)

                # Skip datasource processing, run Q&A generation directly on markdown files
                await run_semi_sythetic_data_generation(datasources_temp)

                print("🎉 Full pipeline completed!")
                print(f"Intermediate URLs saved to: {urls_temp}")
                print(f"Intermediate data sources saved to: {datasources_temp}")
                print(f"Q&A dataset generated from markdown files in: {datasources_temp}")
                print_pipeline_report(urls_temp, datasources_temp)

if __name__ == "__main__":
    asyncio.run(main())