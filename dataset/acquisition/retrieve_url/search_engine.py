from ddgs import DDGS
from util.utilities import getConfig, getLogger

config = getConfig()
log = getLogger(__name__)


def search_question(category, question_text, dorks=None, search_result_count=10):
    """
    Searches for a question using DuckDuckGo.
    Handles both string and dictionary formats for question data.
    """
    if isinstance(question_text, str):
        question = question_text
        question_dorks = dorks
        provided_urls = None
    elif isinstance(question_text, dict):
        question = question_text.get("question", "")
        question_dorks = question_text.get("dorks") or dorks
        provided_urls = question_text.get("urls")
    else:
        raise ValueError(f"Invalid question_data format: {question_text}")

    # If URLs are already provided, use them directly
    if provided_urls:
        log.debug(f"Using provided URLs for: {question}")
        return {"category": category, "question": question, "dorks": question_dorks, "urls": provided_urls}

    # Build the search query
    search_query = question
    if question_dorks:
        search_query = f"{question} {question_dorks}"

    log.debug(f"Searching for: {search_query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=search_result_count))
            urls = [result['href'] for result in results if 'href' in result]

        return {"category": category, "question": question, "dorks": question_dorks, "urls": urls}
    except Exception as e:
        log.warning(f"An error occurred while searching for '{search_query}': {e}")
        return {"category": category, "question": question, "dorks": question_dorks, "urls": [], "error": str(e)}