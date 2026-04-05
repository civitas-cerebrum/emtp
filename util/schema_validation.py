import json

from util.utilities import get_logger

log = get_logger(__name__)


class ValidationError(Exception):
    """Raised when data fails schema validation."""
    pass


def validate_questions_file(path: str):
    """Validate questions JSON matches expected format.

    Supports:
    - New format: [{"category": "...", "questions": [...]}]
    - Legacy format: {"Category": ["q1", "q2"]}
    """
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, list):
        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                raise ValidationError(f"Questions entry {i} must be a dict, got {type(entry).__name__}")
            if "category" not in entry or "questions" not in entry:
                raise ValidationError(
                    f"Questions entry {i} missing 'category' or 'questions': {list(entry.keys())}"
                )
    elif isinstance(data, dict):
        pass  # Legacy format is flexible
    else:
        raise ValidationError(f"Questions file must be a list or dict, got {type(data).__name__}")

    log.debug(f"Validated questions file: {path}")


def validate_qna_dataset(path: str):
    """Validate Q&A dataset has required fields."""
    with open(path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValidationError(f"Q&A dataset must be a list, got {type(data).__name__}")

    for i, entry in enumerate(data):
        if "q" not in entry or "a" not in entry:
            raise ValidationError(f"Q&A entry {i} missing 'q' or 'a' keys: {list(entry.keys())}")

    log.debug(f"Validated Q&A dataset: {path} ({len(data)} entries)")


def validate_conversation_dataset(path: str):
    """Validate conversation dataset has required structure."""
    with open(path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValidationError(f"Conversation dataset must be a list, got {type(data).__name__}")

    for i, entry in enumerate(data):
        if "messages" not in entry:
            raise ValidationError(f"Conversation entry {i} missing 'messages' key")
        if not isinstance(entry["messages"], list) or len(entry["messages"]) == 0:
            raise ValidationError(f"Conversation entry {i} has empty or invalid 'messages'")

    log.debug(f"Validated conversation dataset: {path} ({len(data)} conversations)")
