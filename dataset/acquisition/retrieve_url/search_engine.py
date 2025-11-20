from ddgs import DDGS
import configparser
import logging

logger = logging.getLogger(__name__)


config = configparser.ConfigParser()
config.read('config.ini')
SEARCH_RESULT_COUNT = config.getint('DEFAULT', 'search_result_count', fallback=10)


def search_question(category, question_data, dorks=None):
    """
    Searches for a question using DuckDuckGo.
    Handles both string and dictionary formats for question data.
    """
    if isinstance(question_data, str):
        question = question_data
        question_dorks = dorks
        provided_urls = None
    elif isinstance(question_data, dict):
        question = question_data.get("question", "")
        question_dorks = question_data.get("dorks") or dorks
        provided_urls = question_data.get("urls")
    else:
        raise ValueError(f"Invalid question_data format: {question_data}")

    # If URLs are already provided, use them directly
    if provided_urls:
        logger.debug(f"Using provided URLs for: {question}")
        return {"category": category, "question": question, "dorks": question_dorks, "urls": provided_urls}

    # Build the search query
    search_query = question
    if question_dorks:
        search_query = f"{question} {question_dorks}"

    logger.debug(f"Searching for: {search_query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=SEARCH_RESULT_COUNT))
            urls = [result['href'] for result in results if 'href' in result]

        return {"category": category, "question": question, "dorks": question_dorks, "urls": urls}
    except Exception as e:
        logger.warning(f"An error occurred while searching for '{search_query}': {e}")
        return {"category": category, "question": question, "dorks": question_dorks, "urls": [], "error": str(e)}