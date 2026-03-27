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
import shutil
from typing import List, Dict, Any
import configparser
from collections import defaultdict # Import defaultdict
from dataset.acquisition import retrieve_url_stage
from dataset.acquisition.save_datasource.main import main as save_datasource_stage
from dataset.enrichment.dataset_generation import main as generate_qna_dataset
from dataset.enrichment.deep_dive_generation import main as generate_deep_dive_questions
from dataset.enrichment.conversation_conversion import main as convert_to_conversations
from util.utilities import get_config, get_logger, set_verbose, is_verbose
from util.pipeline_state import PipelineState
from util.schema_validation import validate_qna_dataset, validate_conversation_dataset, ValidationError
from util.file_utils import atomic_write_json
from util.deduplication import deduplicate_qna
from util.dataset_versioning import save_dataset_version
from util.export import export_dataset


config = get_config()
log = get_logger(__name__)

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
        atomic_write_json(output_path, final_output)
        log.info(f"Metadata aggregated and saved to {output_path}.") # Preview first entry
        log.debug(f"Content preview: {json.dumps(final_output[:1] if final_output else [], indent=2)}...") # Preview first entry
    except Exception as e:
        log.error(f"Error aggregating metadata to file {output_path}: {e}")


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
        log.info("\n" + "="*60)
        log.info("                    EMTP PIPELINE REPORT")
        log.info("="*60)
        log.info(f"  📊 URLs Retrieved:     {urls_count}")
        log.info(f"  📄 Markdown Files:     {markdown_count}")
        log.info(f"  ❓ Q&A Pairs Generated: {qa_count}")
        log.info("="*60)
        log.info("  ✅ Pipeline completed successfully!")
        log.info("="*60)

    except Exception as e:
        log.info(f"Note: Could not generate detailed report ({e})")

def run_url_retrieval(questions_file='sample.json', output_dir='dataset/acquisition/temp/urls', verbose: bool = False, dorks: str = None):
    if verbose:
        set_verbose(True)

    log.info(f"🔍 Starting URL retrieval...")
    log.info(f"  Input: {questions_file}")
    log.info(f"  Output: {output_dir}")
    ensure_dir(output_dir)
    # Only extract basename for relative paths; preserve absolute paths
    if not os.path.isabs(questions_file):
        questions_file = os.path.basename(questions_file)
    retrieve_url_stage(output_dir=output_dir, questions_file=questions_file, dorks=dorks)
    log.info(f"✅ URL retrieval completed! Results saved to {output_dir}")

def run_datasource_capture(input_dir='dataset/acquisition/temp/urls', output_dir='dataset/acquisition/temp/datasources', verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Converts URLs into markdown datasources.
    Returns metadata for the captured data.
    """
    log.info(f"📸 Starting datasource capture...")
    log.info(f"  Input: {input_dir}")
    log.info(f"  Output: {output_dir}")
    ensure_dir(output_dir)
    # save_datasource_stage is now synchronous
    collected_metadata = save_datasource_stage(input_dir=input_dir, output_dir=output_dir, verbose=verbose)
    log.info(f"✅ Datasource capture completed! Data sources saved to {output_dir}")
    return collected_metadata

def run_deep_dive(datasources_dir='dataset/acquisition/temp/datasources',
                  urls_deep_dir='dataset/acquisition/temp/urls_deep',
                  datasources_deep_dir='dataset/acquisition/temp/datasources_deep',
                  verbose: bool = False, dorks: str = None):
    """
    Orchestrates the deep-dive stage:
    1. Generate follow-up questions from round 1 content
    2. Search those questions (reuse URL retrieval)
    3. Scrape the results (reuse datasource capture)
    """
    log.info(f"🔬 Starting deep-dive generation...")

    # Clear previous deep-dive outputs for idempotency
    for d in [urls_deep_dir, datasources_deep_dir]:
        if os.path.exists(d):
            shutil.rmtree(d)

    # Step 1: Generate deep-dive questions from round 1 markdown
    questions_file = generate_deep_dive_questions(scraped_content_dir=datasources_dir)

    # Check if any questions were generated
    try:
        with open(questions_file, 'r') as f:
            questions = json.load(f)
        total_qs = sum(len(cat.get("questions", [])) for cat in questions)
        if total_qs == 0:
            log.warning("No deep-dive questions generated. Skipping round 2 scraping.")
            return None
    except Exception as e:
        log.error(f"Failed to read deep-dive questions: {e}")
        return None

    log.info(f"Generated {total_qs} deep-dive questions. Starting round 2 search & scrape...")

    # Step 2: Search for those questions
    ensure_dir(urls_deep_dir)
    run_url_retrieval(questions_file=questions_file, output_dir=urls_deep_dir, verbose=verbose, dorks=dorks)

    # Step 3: Scrape the results
    ensure_dir(datasources_deep_dir)
    run_datasource_capture(input_dir=urls_deep_dir, output_dir=datasources_deep_dir, verbose=verbose)

    log.info(f"✅ Deep-dive generation completed! Round 2 data saved to {datasources_deep_dir}")
    return datasources_deep_dir

def run_conversation_conversion(qna_dataset_file='qna_dataset.json',
                                 output_file='conversation_dataset.json'):
    """Runs the conversation conversion stage."""
    log.info(f"💬 Starting conversation conversion...")
    log.info(f"  Input: {qna_dataset_file}")
    log.info(f"  Output: {output_file}")
    output_path = convert_to_conversations(
        qna_dataset_file=qna_dataset_file,
        output_file=output_file,
    )
    log.info(f"✅ Conversation conversion completed! Dataset saved to {output_path}")
    return output_path

def run_datasource_processing(input_dir='dataset/acquisition/temp/datasources', output_dir='dataset/acquisition/temp/text_data', verbose: bool = False, accurate: bool = False):
    # Placeholder for processing captured datasources into text data.
    # This stage is not yet fully implemented.
    log.info(f"🔄 Starting datasource processing...")
    log.info(f"  Input: {input_dir}")
    log.info(f"  Output: {output_dir}")
    ensure_dir(output_dir)
    datasource_processing_stage(input_dir, output_dir, verbose=verbose, accurate=accurate) # Positional arguments
    log.info(f"✅ Datasource processing completed! Text data saved to {output_dir}")

async def run_semi_sythetic_data_generation(metadata_entries: List[Dict[str, Any]], markdown_base_dir='dataset/acquisition/temp/datasources', base_url="http://localhost:8080/api/generate", model_name="gemma3:27b", authorization_token=None):
    # Generates Q&A data from markdown and updates metadata.
    # Aggregates results and saves them to a JSON file.
    log.info(f"🤖 Starting semi-synthetic data generation and metadata aggregation...")

    # Generate Q&A dataset
    # Pass the full path to the markdown files to qa_generation.generate_qna_dataset
    # qa_generation.generate_qna_dataset expects markdown files to be found from input_dir,
    # which is the markdown_base_dir here.
    qna_dataset = generate_qna_dataset()

    if qna_dataset:
        log.info(f"Generated {len(qna_dataset)} Q&A pairs.")
        qna_output_path = os.path.join(markdown_base_dir, "qna_dataset.json")
        with open(qna_output_path, "w", encoding="utf-8") as f:
            json.dump(qna_dataset, f, indent=4)
        log.info(f"Q&A dataset saved to {qna_output_path}")
    else:
        log.error("Failed to generate Q&A dataset.")

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

    log.info(f"✅ Semi-synthetic data generation and metadata aggregation completed! Results saved to {output_scheme_path}")


def get_user_choice():
    log.info("\n" + "="*50)
    log.info("EMTP Data Acquisition Pipeline")
    log.info("="*50)
    log.info("Choose a stage to run:")
    log.info("1. URL Retrieval (from questions to URLs)")
    log.info("2. Datasource Capture (from URLs to markdown data sources)")
    log.info("3. Deep-Dive Generation (generate follow-up questions & scrape)")
    log.info("4. Q&A Generation (from markdown data sources to Q&A dataset)")
    log.info("5. Conversation Conversion (from Q&A pairs to multi-turn dialogues)")
    log.info("6. Run Full Pipeline (all stages)")
    log.info("7. Exit")
    log.info("="*50)

    while True:
        try:
            choice = input("Enter your choice (1-7): ").strip()
            if choice in ['1', '2', '3', '4', '5', '6', '7']:
                return choice
            else:
                log.info("Invalid choice. Please enter 1-7.")
        except KeyboardInterrupt:
            log.info("\nExiting...")
            return '7'

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
            log.info("Invalid log level. Please choose from DEBUG, INFO, WARNING, ERROR, CRITICAL.")

def main():
    # Main entry point for the EMTP pipeline.
    # Supports interactive and command-line execution.
    parser = argparse.ArgumentParser(description="EMTP Data Acquisition Pipeline")
    parser.add_argument('--stage', type=str,
                        choices=['url_retrieval', 'datasource_capture', 'deep_dive',
                                 'qa_generation', 'conversation_conversion', 'full_pipeline'],
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
    parser.add_argument('--deep-dive-output-dir', type=str,
                        default='dataset/acquisition/temp/datasources_deep',
                        help='Output directory for deep-dive datasources.')
    parser.add_argument('--conversation-output', type=str,
                        default='conversation_dataset.json',
                        help='Output file for conversation dataset.')
    parser.add_argument('--skip-deep-dive', action='store_true',
                        help='Skip deep-dive stage in full pipeline.')
    parser.add_argument('--skip-conversation', action='store_true',
                        help='Skip conversation conversion in full pipeline (produce flat Q&A only).')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last completed stage in a previous run.')
    parser.add_argument('--export', type=str, choices=['csv', 'parquet'],
                        help='Export final dataset to this format after pipeline completion.')

    args = parser.parse_args()

    # Determine verbose logging from --log-level or --verbose
    verbose_logging = args.verbose or (args.log_level == 'DEBUG')

    set_verbose(verbose_logging)
    log.info(f"Logging level set to {is_verbose()}. Verbose logging {'enabled' if verbose_logging else 'disabled'}.")

    if args.stage:
        # Non-interactive mode
        if args.stage == 'url_retrieval':
            run_url_retrieval(args.questions_file, args.urls_output_dir, verbose=verbose_logging, dorks=args.dorks)
        elif args.stage == 'datasource_capture':
            collected_metadata = run_datasource_capture(args.urls_output_dir, args.datasources_output_dir, verbose=verbose_logging)
            log.debug(f"Collected metadata count after datasource capture: {len(collected_metadata)}")
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
        elif args.stage == 'deep_dive':
            run_deep_dive(
                datasources_dir=args.datasources_output_dir,
                urls_deep_dir='dataset/acquisition/temp/urls_deep',
                datasources_deep_dir=args.deep_dive_output_dir,
                verbose=verbose_logging, dorks=args.dorks
            )
        elif args.stage == 'conversation_conversion':
            run_conversation_conversion(
                qna_dataset_file='qna_dataset.json',
                output_file=args.conversation_output,
            )
        elif args.stage == 'qa_generation':
            # This path is now deprecated as qa_generation is integrated into datasource_capture in non-interactive mode.
            # However, if run separately, it expects metadata input.
            log.info("To run 'qa_generation' separately, you need to provide metadata entries from a previous 'datasource_capture' run.")
            log.info("Please run the 'full_pipeline' stage or use the interactive mode.")
            return
        elif args.stage == 'full_pipeline':
            log.info("Running full pipeline...")
            urls_dir = args.urls_output_dir
            datasources_dir = args.datasources_output_dir
            urls_deep_dir = 'dataset/acquisition/temp/urls_deep'
            datasources_deep_dir = args.deep_dive_output_dir

            pipeline = PipelineState()

            if args.resume and pipeline.has_previous_run():
                completed = pipeline.get_completed_stages()
                resume_point = pipeline.get_resume_point()
                log.info(f"Resuming pipeline. Completed stages: {completed}. Resuming from: {resume_point}")
            else:
                pipeline.start_run()

            # Stage 1: URL Retrieval
            if not pipeline.is_completed("url_retrieval"):
                run_url_retrieval(args.questions_file, urls_dir, verbose=verbose_logging, dorks=args.dorks)
                pipeline.mark_stage("url_retrieval", "completed", output_dir=urls_dir)
            else:
                log.info("Skipping url_retrieval (already completed)")

            # Stage 2: Datasource Capture
            if not pipeline.is_completed("datasource_capture"):
                collected_metadata = run_datasource_capture(urls_dir, datasources_dir, verbose=verbose_logging)
                pipeline.mark_stage("datasource_capture", "completed", output_dir=datasources_dir)
            else:
                log.info("Skipping datasource_capture (already completed)")

            # Stage 3: Deep-Dive (optional)
            content_dirs = [datasources_dir]
            if not args.skip_deep_dive:
                if not pipeline.is_completed("deep_dive"):
                    deep_result = run_deep_dive(
                        datasources_dir=datasources_dir,
                        urls_deep_dir=urls_deep_dir,
                        datasources_deep_dir=datasources_deep_dir,
                        verbose=verbose_logging, dorks=args.dorks
                    )
                    if deep_result:
                        content_dirs.append(datasources_deep_dir)
                    pipeline.mark_stage("deep_dive", "completed", output_dir=datasources_deep_dir)
                else:
                    log.info("Skipping deep_dive (already completed)")
                    if os.path.exists(datasources_deep_dir):
                        content_dirs.append(datasources_deep_dir)
            else:
                pipeline.mark_stage("deep_dive", "skipped")

            # Stage 4: Q&A Generation (from both rounds)
            if not pipeline.is_completed("qa_generation"):
                log.info(f"🤖 Starting Q&A generation from {len(content_dirs)} source(s)...")
                generate_qna_dataset(scraped_content_dirs=content_dirs)
                try:
                    validate_qna_dataset("qna_dataset.json")
                    log.info("Q&A dataset validation passed")
                except ValidationError as e:
                    log.error(f"Q&A dataset validation failed: {e}")

                # Deduplication
                try:
                    import json
                    with open("qna_dataset.json", "r") as f:
                        qna_data = json.load(f)
                    qna_data, removed = deduplicate_qna(qna_data)
                    if removed > 0:
                        from util.file_utils import atomic_write_json
                        atomic_write_json("qna_dataset.json", qna_data)
                        log.info(f"Removed {removed} duplicate Q&A pairs")
                except Exception as e:
                    log.warning(f"Deduplication failed: {e}")

                pipeline.mark_stage("qa_generation", "completed")
            else:
                log.info("Skipping qa_generation (already completed)")

            # Stage 5: Conversation Conversion (optional)
            if not args.skip_conversation:
                if not pipeline.is_completed("conversation_conversion"):
                    run_conversation_conversion(
                        qna_dataset_file='qna_dataset.json',
                        output_file=args.conversation_output,
                    )
                    try:
                        validate_conversation_dataset(args.conversation_output)
                        log.info("Conversation dataset validation passed")
                    except ValidationError as e:
                        log.error(f"Conversation dataset validation failed: {e}")
                    pipeline.mark_stage("conversation_conversion", "completed")
                else:
                    log.info("Skipping conversation_conversion (already completed)")
            else:
                pipeline.mark_stage("conversation_conversion", "skipped")

            # Save dataset version
            try:
                version_files = {"qna_dataset.json": "qna_dataset.json"}
                if not args.skip_conversation:
                    version_files["conversation_dataset.json"] = args.conversation_output
                save_dataset_version(version_files)
            except Exception as e:
                log.warning(f"Dataset versioning failed: {e}")

            # Export if requested
            if args.export:
                try:
                    export_name = f"qna_dataset.{args.export}"
                    export_dataset("qna_dataset.json", export_name, args.export)
                    if not args.skip_conversation and os.path.exists(args.conversation_output):
                        conv_export = f"conversation_dataset.{args.export}"
                        export_dataset(args.conversation_output, conv_export, args.export)
                except Exception as e:
                    log.warning(f"Export failed: {e}")

            pipeline.clear()
            log.info("🎉 Full pipeline completed!")
            print_pipeline_report(urls_dir, datasources_dir)
    else:
        # Interactive mode
        log.info("Welcome to EMTP Data Acquisition Pipeline!")
        while True:
            choice = get_user_choice()

            if choice == '7':
                log.info("Goodbye!")
                break

            log_level_str = get_log_level_input()
            logging_level = getattr(logging, log_level_str.upper(), logging.INFO)
            logging.getLogger().setLevel(logging_level)
            log.setLevel(logging_level)
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

            elif choice == '3':
                # Deep-Dive Generation
                datasources_dir = get_path_input("Input datasources directory", "dataset/acquisition/temp/datasources")
                run_deep_dive(
                    datasources_dir=datasources_dir,
                    urls_deep_dir="dataset/acquisition/temp/urls_deep",
                    datasources_deep_dir="dataset/acquisition/temp/datasources_deep",
                    verbose=verbose_logging,
                )

            elif choice == '4':
                # Q&A Generation
                datasources_dir = get_path_input("Input datasources directory (round 1)", "dataset/acquisition/temp/datasources")
                datasources_deep_dir = get_path_input("Input deep-dive datasources directory (leave blank to skip)", "")
                content_dirs = [datasources_dir]
                if datasources_deep_dir:
                    content_dirs.append(datasources_deep_dir)
                log.info(f"🤖 Starting Q&A generation from {len(content_dirs)} source(s)...")
                generate_qna_dataset(scraped_content_dirs=content_dirs)

            elif choice == '5':
                # Conversation Conversion
                qna_file = get_path_input("Q&A dataset file", "qna_dataset.json")
                output_file = get_path_input("Output conversation dataset file", "conversation_dataset.json")
                run_conversation_conversion(qna_dataset_file=qna_file, output_file=output_file)

            elif choice == '6':
                log.info("Running full pipeline...")
                questions_file = get_path_input("Questions file path", "sample.json")
                urls_temp = "dataset/acquisition/temp/urls"
                datasources_temp = "dataset/acquisition/temp/datasources"
                urls_deep_temp = "dataset/acquisition/temp/urls_deep"
                datasources_deep_temp = "dataset/acquisition/temp/datasources_deep"

                pipeline = PipelineState()
                if pipeline.has_previous_run():
                    completed = pipeline.get_completed_stages()
                    resume = input(f"Previous run found (completed: {completed}). Resume? (Y/n): ").strip().lower()
                    if resume != 'n':
                        log.info(f"Resuming from: {pipeline.get_resume_point()}")
                    else:
                        pipeline.start_run()
                else:
                    pipeline.start_run()

                # Stage 1: URL Retrieval
                if not pipeline.is_completed("url_retrieval"):
                    run_url_retrieval(questions_file, urls_temp, verbose=verbose_logging)
                    pipeline.mark_stage("url_retrieval", "completed", output_dir=urls_temp)
                else:
                    log.info("Skipping url_retrieval (already completed)")

                # Stage 2: Datasource Capture
                if not pipeline.is_completed("datasource_capture"):
                    collected_metadata = run_datasource_capture(urls_temp, datasources_temp, verbose=verbose_logging)
                    pipeline.mark_stage("datasource_capture", "completed", output_dir=datasources_temp)
                else:
                    log.info("Skipping datasource_capture (already completed)")

                # Stage 3: Deep-Dive (optional)
                content_dirs = [datasources_temp]
                skip_deep = input("Skip deep-dive stage? (y/N): ").strip().lower() == 'y'
                if not skip_deep:
                    if not pipeline.is_completed("deep_dive"):
                        deep_result = run_deep_dive(
                            datasources_dir=datasources_temp,
                            urls_deep_dir=urls_deep_temp,
                            datasources_deep_dir=datasources_deep_temp,
                            verbose=verbose_logging,
                        )
                        if deep_result:
                            content_dirs.append(datasources_deep_temp)
                        pipeline.mark_stage("deep_dive", "completed", output_dir=datasources_deep_temp)
                    else:
                        log.info("Skipping deep_dive (already completed)")
                        if os.path.exists(datasources_deep_temp):
                            content_dirs.append(datasources_deep_temp)
                else:
                    pipeline.mark_stage("deep_dive", "skipped")

                # Stage 4: Q&A Generation
                if not pipeline.is_completed("qa_generation"):
                    log.info(f"🤖 Starting Q&A generation from {len(content_dirs)} source(s)...")
                    generate_qna_dataset(scraped_content_dirs=content_dirs)
                    try:
                        validate_qna_dataset("qna_dataset.json")
                        log.info("Q&A dataset validation passed")
                    except ValidationError as e:
                        log.error(f"Q&A dataset validation failed: {e}")

                    # Deduplication
                    try:
                        import json
                        with open("qna_dataset.json", "r") as f:
                            qna_data = json.load(f)
                        qna_data, removed = deduplicate_qna(qna_data)
                        if removed > 0:
                            from util.file_utils import atomic_write_json
                            atomic_write_json("qna_dataset.json", qna_data)
                            log.info(f"Removed {removed} duplicate Q&A pairs")
                    except Exception as e:
                        log.warning(f"Deduplication failed: {e}")

                    pipeline.mark_stage("qa_generation", "completed")
                else:
                    log.info("Skipping qa_generation (already completed)")

                # Stage 5: Conversation Conversion (optional)
                skip_conv = input("Skip conversation conversion? (y/N): ").strip().lower() == 'y'
                if not skip_conv:
                    if not pipeline.is_completed("conversation_conversion"):
                        run_conversation_conversion()
                        try:
                            validate_conversation_dataset("conversation_dataset.json")
                            log.info("Conversation dataset validation passed")
                        except ValidationError as e:
                            log.error(f"Conversation dataset validation failed: {e}")
                        pipeline.mark_stage("conversation_conversion", "completed")
                    else:
                        log.info("Skipping conversation_conversion (already completed)")
                else:
                    pipeline.mark_stage("conversation_conversion", "skipped")

                # Save dataset version
                try:
                    version_files = {"qna_dataset.json": "qna_dataset.json"}
                    if not skip_conv:
                        version_files["conversation_dataset.json"] = "conversation_dataset.json"
                    save_dataset_version(version_files)
                except Exception as e:
                    log.warning(f"Dataset versioning failed: {e}")

                export_fmt = input("Export dataset? (csv/parquet/N): ").strip().lower()
                if export_fmt in ("csv", "parquet"):
                    try:
                        export_dataset("qna_dataset.json", f"qna_dataset.{export_fmt}", export_fmt)
                        log.info(f"Exported to qna_dataset.{export_fmt}")
                    except Exception as e:
                        log.warning(f"Export failed: {e}")

                pipeline.clear()
                log.info("🎉 Full pipeline completed!")
                print_pipeline_report(urls_temp, datasources_temp)

if __name__ == "__main__":
    main()
