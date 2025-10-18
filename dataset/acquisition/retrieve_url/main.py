
import json
import time
import argparse
import os
import logging

from .data_loader import get_questions
from .search_engine import search_question
from .url_utils import is_denied_domain # Import from new utility file

logger = logging.getLogger(__name__)

def search_and_save_urls(questions_data, base_output_dir="dataset/acquisition/temp/urls", verbose: bool = False, dorks: str = None, denied_domains: list = None):
    """Searches for questions and saves the resulting URLs to separate JSON files per category."""
    os.makedirs(base_output_dir, exist_ok=True)

    logger.setLevel(logging.DEBUG if verbose else logging.INFO) # Default to INFO for main messages

    if dorks:
        logger.debug(f"Using dorks: {dorks}")

    total_urls_found = 0
    total_questions_failed = 0
    
    for category, questions in questions_data.items():
        logger.debug(f"Processing category: {category}")
        category_results = []
        
        for question_data in questions:
            retrieved_urls = []
            attempts = 0
            while len(retrieved_urls) < 5 and attempts < 3: # Try to get at least 5 valid URLs, max 3 attempts
                result = search_question(category, question_data, dorks)
                if result and result.get("urls"):
                    for url in result["urls"]:
                        if not is_denied_domain(url, denied_domains):
                            retrieved_urls.append(url)
                            if len(retrieved_urls) >= 5:
                                break
                attempts += 1
                time.sleep(1) # Be polite to search engines

            if retrieved_urls:
                final_urls_for_question = retrieved_urls[:5] # Take top 5
                category_results.append({"category": category, "question": question_data, "dorks": dorks, "urls": final_urls_for_question})
                total_urls_found += len(final_urls_for_question)
            else:
                total_questions_failed += 1
                logger.warning(f"Failed to find valid URLs for question: {question_data}")


        safe_filename = "".join(c for c in category if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_filename = safe_filename.lower().replace(' ', '_').replace('-', '_') + '.json'
        output_file = os.path.join(base_output_dir, safe_filename)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(category_results, f, indent=4)
        logger.debug(f"Saved {len(category_results)} results to {output_file}")
    
    return {"success": total_urls_found, "failed": total_questions_failed}


def main(output_dir='dataset/acquisition/temp/urls', questions_file='sample.json', verbose: bool = False, dorks: str = None, denied_domains: list = None):
    questions_data = get_questions(filename=questions_file)
    return search_and_save_urls(questions_data, output_dir, verbose, dorks, denied_domains)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Search questions using DuckDuckGo')
    parser.add_argument('--output-dir', default='dataset/acquisition/temp/urls',
                        help='Output directory (default: dataset/acquisition/temp/urls)')
    parser.add_argument('--questions-file', default='sample.json',
                        help='Questions file (default: sample.json)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--dorks', type=str,
                        help='DuckDuckGo search operators to apply to all searches (e.g., "filetype:pdf site:example.com")')

    args = parser.parse_args()
    # In __main__, denied_domains is not relevant as it's for full pipeline when run_url_retrieval passes it
    # We set a dummy empty list here for standalone execution
    main(args.output_dir, args.questions_file, args.verbose, args.dorks, denied_domains=[])