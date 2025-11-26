import json
import os

def get_questions(filename="qa_questions.json"):
    """
    Loads questions from the JSON file and normalizes them into the format:
    {
        "Category Name": [
            {"question": str, "dorks": None, "urls": None}
        ]
    }

    Supports both new format:
    [
        {"category": "...", "questions": ["q1", "q2", ...]}
    ]

    And legacy format:
    {
        "Category": ["q1", {"question": "..."}]
    }
    """
    if not os.path.isabs(filename):
        script_dir = os.path.dirname(__file__)
        filename = os.path.join(script_dir, filename)

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    normalized_data = {}

    # ---- New Format: list of {"category", "questions"} ----
    if isinstance(data, list):
        for block in data:
            category = block.get("category")
            questions = block.get("questions", [])

            if not category:
                raise ValueError(f"Missing 'category' in entry: {block}")

            normalized_questions = []
            for q in questions:
                if isinstance(q, str):
                    normalized_questions.append({"question": q, "dorks": None, "urls": None})
                elif isinstance(q, dict):
                    normalized_questions.append({
                        "question": q.get("question", q.get("q", "")),
                        "dorks": q.get("dorks"),
                        "urls": q.get("urls")
                    })
                else:
                    raise ValueError(f"Invalid question format in category '{category}': {q}")

            normalized_data[category] = normalized_questions
        return normalized_data

    # ---- Legacy Format: dict ----
    if isinstance(data, dict):
        for category, questions in data.items():
            normalized_questions = []
            for item in questions:
                if isinstance(item, str):
                    normalized_questions.append({"question": item, "dorks": None, "urls": None})
                elif isinstance(item, dict):
                    normalized_questions.append({
                        "question": item.get("question", item.get("q", "")),
                        "dorks": item.get("dorks"),
                        "urls": item.get("urls")
                    })
                else:
                    raise ValueError(f"Invalid question format in category '{category}': {item}")
            normalized_data[category] = normalized_questions
        return normalized_data

    raise ValueError("Unsupported JSON structure")
