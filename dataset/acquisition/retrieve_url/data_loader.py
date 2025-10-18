import json
import os

def get_questions(filename="qa_questions.json"):
    """Reads questions from a JSON file and normalizes to the expected format."""
    # If filename is relative, look in the same directory as this script
    if not os.path.isabs(filename):
        script_dir = os.path.dirname(__file__)
        filename = os.path.join(script_dir, filename)
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Normalize to expected format: {"category": [{"question": str, "dorks": str or None, "urls": list or None}]}
    normalized_data = {}
    for category, questions in data.items():
        normalized_questions = []
        for item in questions:
            if isinstance(item, str):
                # Legacy format: just a string
                normalized_questions.append({"question": item, "dorks": None, "urls": None})
            elif isinstance(item, dict):
                # New format: dict with question and optional dorks/urls
                normalized_questions.append({
                    "question": item.get("question", item.get("q", "")),
                    "dorks": item.get("dorks"),
                    "urls": item.get("urls")
                })
            else:
                raise ValueError(f"Invalid question format in category '{category}': {item}")
        normalized_data[category] = normalized_questions

    return normalized_data