import json
import os

def get_questions(filename="qa_questions.json"):
    """Reads questions from a JSON file."""
    # If filename is relative, look in the same directory as this script
    if not os.path.isabs(filename):
        script_dir = os.path.dirname(__file__)
        filename = os.path.join(script_dir, filename)
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data