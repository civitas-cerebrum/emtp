import json
import time
import random
import threading
from googlesearch import search
from ddgs import DDGS
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

def get_questions(filename="qa_questions.json"):
    """Reads questions from a JSON file."""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def search_question(category, question, engine='google'):
    """Searches a single question and returns the URLs."""
    print(f"- Searching for: {question} (using {engine})")
    try:
        if engine == 'google':
            urls = [url for url in search(question, num_results=5, lang='en')]
        elif engine == 'duckduckgo':
            with DDGS() as ddgs:
                results = list(ddgs.text(question, max_results=5))
                urls = [result['href'] for result in results if 'href' in result]
        else:
            raise ValueError(f"Unsupported search engine: {engine}")

        return {"category": category, "question": question, "urls": urls}
    except Exception as e:
        print(f"- An error occurred while searching for '{question}': {e}")
        return {"category": category, "question": question, "urls": [], "error": str(e)}

def search_and_save_urls(questions_data, engine='google', base_output_dir="output"):
    """Searches for questions using the specified engine and saves the resulting URLs to separate JSON files per category."""
    import os

    # Create engine-specific output directory
    output_dir = os.path.join(base_output_dir, engine)
    os.makedirs(output_dir, exist_ok=True)

    # Process each category sequentially
    for category, questions in questions_data.items():
        print(f"- Processing category: {category}")
        category_results = []
        for question in questions:
            result = search_question(category, question, engine)
            if result:
                category_results.append(result)
            # Respect rate limiting with 1-second delay
            time.sleep(1)

        # Create a safe filename from the category name (lowercase)
        safe_filename = "".join(c for c in category if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_filename = safe_filename.lower().replace(' ', '_').replace('-', '_') + '.json'
        output_file = os.path.join(output_dir, safe_filename)

        # Write the category results to its own JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(category_results, f, indent=4)
        print(f"- Saved {len(category_results)} results to {output_file}")

    print(f"Finished retrieving URLs using {engine}. Results saved to {output_dir}/")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Search questions using Google or DuckDuckGo')
    parser.add_argument('--engine', choices=['google', 'duckduckgo', 'both'],
                       default='google', help='Search engine to use (default: google)')
    parser.add_argument('--output-dir', default='output',
                       help='Base output directory (default: output)')

    args = parser.parse_args()

    questions_data = get_questions(filename="qa_questions.json")

    if args.engine == 'both':
        print("Running searches with both Google and DuckDuckGo in parallel...")

        # Create threads for both engines
        google_thread = threading.Thread(
            target=search_and_save_urls,
            args=(questions_data, 'google', args.output_dir)
        )
        duckduckgo_thread = threading.Thread(
            target=search_and_save_urls,
            args=(questions_data, 'duckduckgo', args.output_dir)
        )

        # Start both threads
        google_thread.start()
        duckduckgo_thread.start()

        # Wait for both to complete
        google_thread.join()
        duckduckgo_thread.join()

        print("All searches completed!")
    else:
        search_and_save_urls(questions_data, args.engine, args.output_dir)