import json
import time
import threading
import argparse
import os
from .data_loader import get_questions
from .search_engine import search_question

import json
import time
import argparse
import os
import logging
from .data_loader import get_questions
from .search_engine import search_question

# Use the global logger configuration
logger = logging.getLogger(__name__)


def search_and_save_urls(questions_data, base_output_dir="dataset/acquisition/temp/urls", verbose: bool = False, dorks: str = None):
    """
    Searches for questions and saves URLs to JSON files.
    Organizes results by category into separate JSON files.
    """
    os.makedirs(base_output_dir, exist_ok=True)

    logger.setLevel(logging.DEBUG if verbose else logging.INFO) # Set level for this call
    if dorks:
        logger.info(f"Using dorks: {dorks}")

    for category, questions in questions_data.items():
        logger.debug(f"Processing category: {category}")
        category_results = []
        for question_data in questions:
            question_text = question_data.get('question', str(question_data)) if isinstance(question_data, dict) else question_data
            result = search_question(category, question_text, dorks)
            if result:
                category_results.append(result)
            time.sleep(5) # Increased delay to prevent rate-limiting

        safe_filename = "".join(c for c in category if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_filename = safe_filename.lower().replace(' ', '_').replace('-', '_') + '.json'
        output_file = os.path.join(base_output_dir, safe_filename)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(category_results, f, indent=4)
        logger.debug(f"Saved {len(category_results)} results to {output_file}")


def run(output_dir='dataset/acquisition/temp/urls', questions_file='qa_questions.json', verbose: bool = True, dorks: str = None):
    """
    Executes the URL search and saving process.
    Loads questions and initiates the search.
    """
    questions_data = get_questions(filename=questions_file)
    search_and_save_urls(questions_data, output_dir, verbose, dorks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Search questions using DuckDuckGo')
    parser.add_argument('--output-dir', default='dataset/acquisition/temp/urls',
                        help='Output directory (default: dataset/acquisition/temp/urls)')
    parser.add_argument('--questions-file', default='qa_questions.json',
                        help='Questions file (default: qa_questions.json)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--dorks', type=str,
                        help='DuckDuckGo search operators to apply to all searches (e.g., "filetype:pdf site:example.com")')

    args = parser.parse_args()
    run(args.output_dir, args.questions_file, args.verbose, args.dorks)