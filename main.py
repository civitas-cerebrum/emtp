#!/usr/bin/env python3
"""
EMTP Main Pipeline - Interactive Session

This script provides an interactive interface to run individual stages
of the data acquisition pipeline with customizable input/output paths.
"""

import os
import argparse
import logging
import json
from typing import List, Dict, Any
import configparser
from collections import defaultdict # Import defaultdict
import asyncio # Import asyncio
from dataset.acquisition import retrieve_url_stage
from dataset.acquisition.save_datasource.main import main as save_datasource_stage
from dataset.enrichment.dataset_generation import main as generate_qna_dataset


# Set up a more flexible logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Default to INFO

def ensure_dir(path):
    """
    Ensures a directory exists, creating it if necessary.
    This prevents errors from trying to write to non-existent paths.
    """
    os.makedirs(path, exist_ok=True)

def aggregate_metadata_to_file(metadata_entries: List[Dict[str, Any]], output_path: str):
    """
    Aggregates and categorizes metadata entries.
    Saves the structured data to a specified JSON file.
    """
    categorized_metadata = defaultdict(list)
    for entry in metadata_entries:
        category_name = entry.get("categoryName", "Uncategorized")
        categorized_metadata[category_name].append({
            "contentFilePath": entry.get("contentFilePath"),
            "questionCount": entry.get("questionCount", 0),
            "url": entry.get("url"),
            "sourceType": entry.get("sourceType", "unknown") # Include sourceType
        })

    # Convert defaultdict to a list of dictionaries as in the example
    final_output = []
    for category, entries in categorized_metadata.items():
        final_output.append({
            "categoryName": category,
            "entries": entries
        })

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=4)
        logger.info(f"Metadata aggregated and saved to {output_path}. Content preview: {json.dumps(final_output[:1] if final_output else [], indent=2)}...") # Preview first entry
    except Exception as e:
        logger.error(f"Error aggregating metadata to file {output_path}: {e}")


def print_pipeline_report(urls_dir, datasources_dir, qa_file='qna_dataset.json'):
    # Generates and prints a summary report for the pipeline.
    # Displays metrics like retrieved URLs, markdown files, and Q&A pairs.
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
    # Executes the URL retrieval stage.
    # Fetches URLs from questions and saves them to the output directory.
    print(f"🔍 Starting URL retrieval...")
    print(f"  Input: {questions_file}")
    print(f"  Output: {output_dir}")
    ensure_dir(output_dir)
    # Assuming retrieve_url_stage accepts a verbose argument
    # Extract just the filename if a full path is provided
    filename_only = os.path.basename(questions_file)
    retrieve_url_stage(output_dir=output_dir, questions_file=filename_only, verbose=verbose, dorks=dorks)
    print(f"✅ URL retrieval completed! Results saved to {output_dir}")

def run_datasource_capture(input_dir='dataset/acquisition/temp/urls', output_dir='dataset/acquisition/temp/datasources', verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Converts URLs into markdown datasources.
    Returns metadata for the captured data.
    """
    print(f"📸 Starting datasource capture...")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    ensure_dir(output_dir)
    # save_datasource_stage is now synchronous
    collected_metadata = save_datasource_stage(input_dir=input_dir, output_dir=output_dir, verbose=verbose)
    print(f"✅ Datasource capture completed! Data sources saved to {output_dir}")
    return collected_metadata

def run_datasource_processing(input_dir='dataset/acquisition/temp/datasources', output_dir='dataset/acquisition/temp/text_data', verbose: bool = False, accurate: bool = False):
    # Placeholder for processing captured datasources into text data.
    # This stage is not yet fully implemented.
    print(f"🔄 Starting datasource processing...")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    ensure_dir(output_dir)
    datasource_processing_stage(input_dir, output_dir, verbose=verbose, accurate=accurate) # Positional arguments
    print(f"✅ Datasource processing completed! Text data saved to {output_dir}")

async def run_semi_sythetic_data_generation(metadata_entries: List[Dict[str, Any]], markdown_base_dir='dataset/acquisition/temp/datasources', base_url="http://localhost:8080/api/generate", model_name="gemma3:27b", authorization_token=None):
    # Generates Q&A data from markdown and updates metadata.
    # Aggregates results and saves them to a JSON file.
    print(f"🤖 Starting semi-synthetic data generation and metadata aggregation...")
    
    # Generate Q&A dataset
    # Pass the full path to the markdown files to qa_generation.generate_qna_dataset
    # qa_generation.generate_qna_dataset expects markdown files to be found from input_dir,
    # which is the markdown_base_dir here.
    qna_dataset = generate_qna_dataset()

    if qna_dataset:
        print(f"Generated {len(qna_dataset)} Q&A pairs.")
        qna_output_path = os.path.join(markdown_base_dir, "qna_dataset.json")
        with open(qna_output_path, "w", encoding="utf-8") as f:
            json.dump(qna_dataset, f, indent=4)
        print(f"Q&A dataset saved to {qna_output_path}")
    else:
        print("Failed to generate Q&A dataset.")

    # Update question counts in metadata (assuming 'questionCount' can now reflect actual Q&A pairs)
    # This part might need refinement depending on how questionCount is truly intended to be used.
    # For now, we'll set it to the count of generated Q&A pairs if available.
    updated_metadata = []
    for entry in metadata_entries:
        # Create a copy to avoid modifying the original list while iterating
        new_entry = entry.copy()
        new_entry["questionCount"] = len(qna_dataset) if qna_dataset else 0 # Simple update for now
        updated_metadata.append(new_entry)

    # Aggregate and save the final datasource_scheme.json
    output_scheme_path = os.path.join(markdown_base_dir, "datasource_metadata.json")
    aggregate_metadata_to_file(updated_metadata, output_scheme_path)

    print(f"✅ Semi-synthetic data generation and metadata aggregation completed! Results saved to {output_scheme_path}")


def get_user_choice():
    # Displays the main menu and prompts user for a stage choice.
    # Ensures a valid selection is made from the available options.
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
    # Prompts user for a path, providing a default.
    # Returns the user's input or the default value.
    path = input(f"{prompt} (default: {default}): ").strip()
    return path if path else default

def get_log_level_input():
    # Prompts user to select a logging level.
    # Validates input to ensure it's a recognized logging level.
    while True:
        log_level_str = input("Enter log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) [INFO]: ").strip().upper()
        if log_level_str in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', '']:
            return log_level_str if log_level_str else 'INFO'
        else:
            print("Invalid log level. Please choose from DEBUG, INFO, WARNING, ERROR, CRITICAL.")

async def main():
    # Main entry point for the EMTP pipeline.
    # Supports interactive and command-line execution.
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

    # Configure logging based on verbose flag
    logging_level = logging.DEBUG if verbose_logging else logging.INFO
    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.setLevel(logging_level) # Set our specific logger as well

    if args.stage:
        # Non-interactive mode
        if args.stage == 'url_retrieval':
            run_url_retrieval(args.questions_file, args.urls_output_dir, verbose=verbose_logging, dorks=args.dorks)
        elif args.stage == 'datasource_capture':
            collected_metadata = run_datasource_capture(args.urls_output_dir, args.datasources_output_dir, verbose=verbose_logging)
            logger.debug(f"Collected metadata count after datasource capture: {len(collected_metadata)}")
            # Save initial metadata before Q&A generation
            initial_metadata_path = os.path.join(args.datasources_output_dir, "datasource_metadata.json")
            aggregate_metadata_to_file(collected_metadata, initial_metadata_path)
            # Load config for API parameters
            config = configparser.ConfigParser()
            config.read('config.ini')
            base_url = config['DEFAULT']['base_url']
            model_name = config['DEFAULT']['model_name']
            authorization_token = config['DEFAULT'].get('authorization_token', None) # Use .get for optional values
            # Directly call Q&A generation stage with collected metadata
            run_semi_sythetic_data_generation(collected_metadata, args.datasources_output_dir, base_url, model_name, authorization_token)
        elif args.stage == 'qa_generation':
            # This path is now deprecated as qa_generation is integrated into datasource_capture in non-interactive mode.
            # However, if run separately, it expects metadata input.
            logger.info("To run 'qa_generation' separately, you need to provide metadata entries from a previous 'datasource_capture' run.")
            logger.info("Please run the 'full_pipeline' stage or use the interactive mode.")
            return
        elif args.stage == 'full_pipeline':
            logger.info("Running full pipeline...")
            run_url_retrieval(args.questions_file, args.urls_output_dir, verbose=verbose_logging, dorks=args.dorks)
            # Load config for API parameters
            config = configparser.ConfigParser()
            config.read('config.ini')
            base_url = config['DEFAULT']['base_url']
            model_name = config['DEFAULT']['model_name']
            authorization_token = config['DEFAULT'].get('authorization_token', None) # Use .get for optional values

            collected_metadata = run_datasource_capture(args.urls_output_dir, args.datasources_output_dir, verbose=verbose_logging)
            logger.debug(f"Collected metadata count after datasource capture (full_pipeline): {len(collected_metadata)}")
            
            # Save initial metadata before Q&A generation
            initial_metadata_path = os.path.join(args.datasources_output_dir, "datasource_metadata.json")
            aggregate_metadata_to_file(collected_metadata, initial_metadata_path)

            await run_semi_sythetic_data_generation(collected_metadata, args.datasources_output_dir, base_url, model_name, authorization_token)

            logger.info("🎉 Full pipeline completed!")
            logger.info(f"Intermediate URLs saved to: {args.urls_output_dir}")
            logger.info(f"Intermediate data sources saved to: {args.datasources_output_dir}")
            logger.info(f"Final datasource_scheme.json generated in: {args.datasources_output_dir}")
            # Correctly pass the path to qna_dataset.json for the report
            print_pipeline_report(args.urls_output_dir, args.datasources_output_dir, os.path.join(args.datasources_output_dir, "qna_dataset.json"))
    else:
        # Interactive mode
        logger.info("Welcome to EMTP Data Acquisition Pipeline!")
        while True:
            choice = get_user_choice()

            if choice == '5':
                logger.info("Goodbye!")
                break
            
            log_level_str = get_log_level_input()
            logging_level = getattr(logging, log_level_str.upper(), logging.INFO)
            logging.getLogger().setLevel(logging_level)
            logger.setLevel(logging_level)
            verbose_logging = (logging_level == logging.DEBUG)

            if choice == '1':
                # URL Retrieval
                questions_file = get_path_input("Questions file path", "sample.json")
                output_dir = get_path_input("Output directory for URLs", "dataset/acquisition/temp/urls")
                run_url_retrieval(questions_file, output_dir, verbose=verbose_logging)

            elif choice == '2':
                # Datasource Capture
                input_dir = get_path_input("Input directory with URLs", "dataset/acquisition/temp/urls")
                output_dir = get_path_input("Output directory for data sources", "dataset/acquisition/temp/datasources")
                collected_metadata = run_datasource_capture(input_dir, output_dir, verbose=verbose_logging)
                
                # Save initial metadata before Q&A generation
                initial_metadata_path = os.path.join(output_dir, "datasource_metadata.json")
                aggregate_metadata_to_file(collected_metadata, initial_metadata_path)

                # Load config for API parameters
                config = configparser.ConfigParser()
                config.read('config.ini')
                base_url = config['DEFAULT']['base_url']
                model_name = config['DEFAULT']['model_name']
                authorization_token = config['DEFAULT'].get('authorization_token', None) # Use .get for optional values
                await run_semi_sythetic_data_generation(collected_metadata, output_dir, base_url, model_name, authorization_token) # Pass collected metadata

            elif choice == '3':
                # Q&A Generation - In interactive mode, this implies running it after a datasource capture
                logger.info("Running Q&A Generation requires metadata from a datasource capture stage.")
                logger.info("Please run stage 2 (Datasource Capture) first, which will now automatically perform Q&A Generation.")
                # We can add more sophisticated logic here if a user wants to load existing markdown and generate Q&A
                # but for now, we direct them to the full pipeline or combined stage 2.
            elif choice == '4':
                # Full Pipeline
                logger.info("Running full pipeline...")

                # Get input path
                questions_file = get_path_input("Questions file path", "sample.json")

                # Use temp directories for intermediate data
                urls_temp = "dataset/acquisition/temp/urls"
                datasources_temp = "dataset/acquisition/temp/datasources"

                # Run URL retrieval
                run_url_retrieval(questions_file, urls_temp, verbose=verbose_logging)

                # Run datasource capture
                collected_metadata = run_datasource_capture(urls_temp, datasources_temp, verbose=verbose_logging)
                logger.debug(f"Collected metadata count after datasource capture (interactive full_pipeline): {len(collected_metadata)}")
                
                # Save initial metadata before Q&A generation
                initial_metadata_path = os.path.join(datasources_temp, "datasource_metadata.json")
                aggregate_metadata_to_file(collected_metadata, initial_metadata_path)

                # Load config for API parameters
                config = configparser.ConfigParser()
                config.read('config.ini')
                base_url = config['DEFAULT']['base_url']
                model_name = config['DEFAULT']['model_name']
                authorization_token = config['DEFAULT'].get('authorization_token', None) # Use .get for optional values

                # Run Q&A generation directly on collected metadata and markdown files
                await run_semi_sythetic_data_generation(collected_metadata, datasources_temp, base_url, model_name, authorization_token)

                logger.info("🎉 Full pipeline completed!")
                logger.info(f"Intermediate URLs saved to: {urls_temp}")
                logger.info(f"Intermediate data sources saved to: {datasources_temp}")
                logger.info(f"Final datasource_scheme.json generated in: {datasources_temp}")
                print_pipeline_report(urls_temp, datasources_temp, os.path.join(datasources_temp, "qna_dataset.json"))

if __name__ == "__main__":
    asyncio.run(main())