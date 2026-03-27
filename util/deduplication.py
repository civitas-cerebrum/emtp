import re
import hashlib

from util.utilities import get_logger

log = get_logger(__name__)


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def deduplicate_qna(dataset: list[dict]) -> tuple[list[dict], int]:
    """
    Remove exact and near-duplicate Q&A pairs based on normalized question text.

    Returns (deduplicated_dataset, num_removed).
    First occurrence wins, duplicates dropped.
    """
    seen = set()
    result = []
    removed = 0

    for entry in dataset:
        q_normalized = normalize_text(entry.get("q", ""))
        q_hash = hashlib.md5(q_normalized.encode()).hexdigest()

        if q_hash in seen:
            removed += 1
            continue

        seen.add(q_hash)
        result.append(entry)

    log.info(f"Deduplication: {removed} duplicates removed, {len(result)} entries remaining")
    return result, removed
