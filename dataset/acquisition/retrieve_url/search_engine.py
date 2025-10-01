from ddgs import DDGS


def search_question(category, question):
    """Searches a single question using DuckDuckGo and returns the URLs."""
    print(f"- Searching for: {question}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(question, max_results=5))
            urls = [result['href'] for result in results if 'href' in result]

        return {"category": category, "question": question, "urls": urls}
    except Exception as e:
        print(f"- An error occurred while searching for '{question}': {e}")
        return {"category": category, "question": question, "urls": [], "error": str(e)}