#!/usr/bin/env python3
"""
EMTP Main Pipeline - Interactive Session

This script provides an interactive interface to run individual stages
of the data acquisition pipeline with customizable input/output paths.
"""

import os
import sys
import configparser
import argparse
from dataset.acquisition import retrieve_url_stage, save_screenshot_stage, screenshot_processing_stage
from dataset.enrichment import qa_generation

def ensure_dir(path):
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)

def run_url_retrieval(questions_file='sample.json', output_dir='dataset/acquisition/temp/urls', verbose: bool = False):
    """Run URL retrieval stage."""
    print(f"Starting URL retrieval...")
    print(f"  Input: {questions_file}")
    print(f"  Output: {output_dir}")
    ensure_dir(output_dir)
    # Assuming retrieve_url_stage accepts a verbose argument
    # Extract just the filename if a full path is provided
    filename_only = os.path.basename(questions_file)
    retrieve_url_stage(output_dir=output_dir, questions_file=filename_only, verbose=verbose)
    print(f"URL retrieval completed! Results saved to {output_dir}")

def run_screenshot_capture(input_dir='dataset/acquisition/temp/urls', output_dir='dataset/acquisition/temp/screenshots', verbose: bool = False):
    """Run screenshot capture stage."""
    print(f"Starting screenshot capture...")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    ensure_dir(output_dir)
    # Assuming save_screenshot_stage accepts a verbose argument
    save_screenshot_stage(input_dir=input_dir, output_dir=output_dir, verbose=verbose)
    print(f"Screenshot capture completed! Images saved to {output_dir}")

def run_screenshot_processing(input_dir='dataset/acquisition/temp/screenshots', output_dir='dataset/acquisition/temp/text_data', verbose: bool = False, accurate: bool = False):
    """Run screenshot processing stage."""
    print(f"Starting screenshot processing...")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    ensure_dir(output_dir)
    screenshot_processing_stage(input_dir, output_dir, verbose=verbose, accurate=accurate) # Positional arguments
    print(f"Screenshot processing completed! Text data saved to {output_dir}")

def run_semi_sythetic_data_generation(input_dir='dataset/acquisition/temp/text_data', config=None):
    """Run Q&A generation stage."""
    print(f"Starting semi-sythetic data generation...")
    ensure_dir(input_dir)
    qa_generation(input_dir, config) # Positional arguments

def get_user_choice():
    """Get user's choice for which stage to run."""
    print("\n" + "="*50)
    print("EMTP Data Acquisition Pipeline")
    print("="*50)
    print("Choose a stage to run:")
    print("1. URL Retrieval (from questions to URLs)")
    print("2. Screenshot Capture (from URLs to images)")
    print("3. Screenshot Processing (from images to text)")
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

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')

    """Main interactive loop or direct execution via arguments."""
    parser = argparse.ArgumentParser(description="EMTP Data Acquisition Pipeline")
    parser.add_argument('--stage', type=str, choices=['url_retrieval', 'screenshot_capture', 'screenshot_processing', 'full_pipeline'],
                        help='Specify the pipeline stage to run directly (non-interactive mode).')
    parser.add_argument('--questions-file', type=str, default='sample.json',
                        help='Path to the questions JSON file.')
    parser.add_argument('--urls-output-dir', type=str, default='dataset/acquisition/temp/urls',
                        help='Output directory for URLs.')
    parser.add_argument('--screenshots-output-dir', type=str, default='dataset/acquisition/temp/screenshots',
                        help='Output directory for screenshots.')
    parser.add_argument('--text-data-output-dir', type=str, default='dataset/acquisition/temp/text_data',
                        help='Output directory for text data.')
    parser.add_argument('--accurate', action='store_true',
                        help='Use more accurate (slower) processing for screenshot processing.')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging.')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the logging level.')

    args = parser.parse_args()

    # Determine verbose logging from --log-level or --verbose
    verbose_logging = args.verbose or (args.log_level == 'DEBUG')

    if args.stage:
        # Non-interactive mode
        if args.stage == 'url_retrieval':
            run_url_retrieval(args.questions_file, args.urls_output_dir, verbose=verbose_logging)
        elif args.stage == 'screenshot_capture':
            run_screenshot_capture(args.urls_output_dir, args.screenshots_output_dir, verbose=verbose_logging)
        elif args.stage == 'screenshot_processing':
            run_screenshot_processing(args.screenshots_output_dir, args.text_data_output_dir, verbose=verbose_logging, accurate=args.accurate)
        elif args.stage == 'full_pipeline':
            print("Running full pipeline...")
            run_url_retrieval(args.questions_file, args.urls_output_dir, verbose=verbose_logging)
            run_screenshot_capture(args.urls_output_dir, args.screenshots_output_dir, verbose=verbose_logging)
            run_screenshot_processing(args.screenshots_output_dir, args.text_data_output_dir, verbose=verbose_logging, accurate=args.accurate)
            run_semi_sythetic_data_generation(config=config)
            print("Full pipeline completed!")
            print(f"Intermediate URLs saved to: {args.urls_output_dir}")
            print(f"Intermediate screenshots saved to: {args.screenshots_output_dir}")
            print(f"Final text data saved to: {args.text_data_output_dir}")
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
                # Screenshot Capture
                input_dir = get_path_input("Input directory with URLs", "dataset/acquisition/temp/urls")
                output_dir = get_path_input("Output directory for screenshots", "dataset/acquisition/temp/screenshots")
                run_screenshot_capture(input_dir, output_dir, verbose=verbose_logging)

            elif choice == '3':
                # Screenshot Processing
                input_dir = get_path_input("Input directory with screenshots", "dataset/acquisition/temp/screenshots")
                output_dir = get_path_input("Output directory for text data", "dataset/acquisition/temp/text_data")
                run_screenshot_processing(input_dir, output_dir, verbose=verbose_logging, accurate=True) # Automatically use accurate mode
            elif choice == '4':
                # Full Pipeline
                print("Running full pipeline...")

                # Get input and final output paths
                questions_file = get_path_input("Questions file path", "sample.json")
                final_text_output = get_path_input("Final output directory for text data", "dataset/acquisition/temp/text_data")

                # Use temp directories for intermediate data
                urls_temp = "dataset/acquisition/temp/urls"
                screenshots_temp = "dataset/acquisition/temp/screenshots"

                # Run URL retrieval
                run_url_retrieval(questions_file, urls_temp, verbose=verbose_logging)

                # Run screenshot capture
                run_screenshot_capture(urls_temp, screenshots_temp, verbose=verbose_logging)

                # Run screenshot processing
                run_screenshot_processing(screenshots_temp, final_text_output, verbose=verbose_logging, accurate=True) # Automatically use accurate mode

                run_semi_sythetic_data_generation(config=config)
                
                print("Full pipeline completed!")
                print(f"Intermediate URLs saved to: {urls_temp}")
                print(f"Intermediate screenshots saved to: {screenshots_temp}")
                print(f"Final text data saved to: {final_text_output}")

if __name__ == "__main__":
    main()