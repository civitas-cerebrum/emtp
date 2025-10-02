import json
import time
import threading
import argparse
import os
from .data_loader import get_questions
from .search_engine import search_question

import json
import time
import threading
import argparse
import os
import logging
import sys # Import sys for StreamHandler
from .data_loader import get_questions
from .search_engine import search_question

# Configure logging for the module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def search_and_save_urls(questions_data, base_output_dir="dataset/acquisition/temp/urls", verbose: bool = False):
    """Searches for questions and saves the resulting URLs to separate JSON files per category."""
    os.makedirs(base_output_dir, exist_ok=True)

    logger.setLevel(logging.DEBUG if verbose else logging.INFO) # Set level for this call
    logger.info(f"Starting URL retrieval to: {base_output_dir}")

    for category, questions in questions_data.items():
        logger.info(f"Processing category: {category}")
        category_results = []
        for question in questions:
            logger.debug(f"Searching for question: {question}")
            result = search_question(category, question)
            if result:
                category_results.append(result)
                logger.debug(f"Found {len(result.get('urls', []))} URLs for '{question}'")
            time.sleep(1)

        safe_filename = "".join(c for c in category if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_filename = safe_filename.lower().replace(' ', '_').replace('-', '_') + '.json'
        output_file = os.path.join(base_output_dir, safe_filename)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(category_results, f, indent=4)
        logger.info(f"Saved {len(category_results)} results to {output_file}")

    logger.info(f"Finished retrieving URLs. Results saved to {base_output_dir}/")


def main(output_dir='dataset/acquisition/temp/urls', questions_file='sample.json', verbose: bool = False):
    questions_data = get_questions(filename=questions_file)
    search_and_save_urls(questions_data, output_dir, verbose)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Search questions using DuckDuckGo')
    parser.add_argument('--output-dir', default='dataset/acquisition/temp/urls',
                        help='Output directory (default: dataset/acquisition/temp/urls)')
    parser.add_argument('--questions-file', default='sample.json',
                        help='Questions file (default: sample.json)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')

    args = parser.parse_args()
    main(args.output_dir, args.questions_file, args.verbose)