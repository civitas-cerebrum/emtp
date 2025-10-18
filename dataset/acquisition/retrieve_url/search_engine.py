from ddgs import DDGS
import logging
from .url_utils import is_denied_domain

logger = logging.getLogger(__name__)


def search_question(category, question_data, dorks=None, denied_domains=None):
    """Searches a single question using DuckDuckGo and returns the URLs.

    Args:
        category: The category of the question
        question_data: Either a string (legacy) or dict with question, dorks, urls
        dorks: Optional DuckDuckGo search operators (e.g., "filetype:pdf site:example.com")
        denied_domains: A list of domains to exclude from results.
    """
    if denied_domains is None:
        denied_domains = []

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

    if provided_urls:
        # Assuming is_denied_domain is available in the scope or passed
        filtered_urls = [url for url in provided_urls if not is_denied_domain(url, denied_domains)]
        return {"category": category, "question": question, "dorks": question_dorks, "urls": filtered_urls}

    search_query = question
    if question_dorks:
        search_query = f"{question} {question_dorks}"

    logger.debug(f"Searching for: {search_query}")
    try:
        valid_urls = []
        # Increase max_results to allow for filtering
        with DDGS() as ddgs:
            results = ddgs.text(search_query, max_results=20) # Fetch more results to filter
            for result in results:
                if 'href' in result:
                    url = result['href']
                    # Assuming is_denied_domain is available in the scope or passed
                    if not is_denied_domain(url, denied_domains):
                        valid_urls.append(url)
                if len(valid_urls) >= 5: # Stop if we have enough valid URLs
                    break

        return {"category": category, "question": question, "dorks": question_dorks, "urls": valid_urls[:5]} # Return top 5 valid URLs
    except Exception as e:
        logger.warning(f"An error occurred while searching for '{search_query}': {e}")
        return {"category": category, "question": question, "dorks": question_dorks, "urls": [], "error": str(e)}