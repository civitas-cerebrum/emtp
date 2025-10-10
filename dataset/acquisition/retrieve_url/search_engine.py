from ddgs import DDGS


def search_question(category, question_data, dorks=None):
    """Searches a single question using DuckDuckGo and returns the URLs.

    Args:
        category: The category of the question
        question_data: Either a string (legacy) or dict with question, dorks, urls
        dorks: Optional DuckDuckGo search operators (e.g., "filetype:pdf site:example.com")
    """
    # Handle both legacy string format and new dict format
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
        print(f"- Using provided URLs for: {question}")
        return {"category": category, "question": question, "dorks": question_dorks, "urls": provided_urls}

    # Build the search query
    search_query = question
    if question_dorks:
        search_query = f"{question} {question_dorks}"

    print(f"- Searching for: {search_query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=5))
            urls = [result['href'] for result in results if 'href' in result]

        return {"category": category, "question": question, "dorks": question_dorks, "urls": urls}
    except Exception as e:
        print(f"- An error occurred while searching for '{search_query}': {e}")
        return {"category": category, "question": question, "dorks": question_dorks, "urls": [], "error": str(e)}