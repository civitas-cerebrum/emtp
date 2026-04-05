import os
import json
from typing import Optional

from util.utilities import get_config, get_logger, get_emtp_directory
from util.llm_client import LLMClient, create_llm_client
from util.llm_providers.base import LLMError
from util.file_utils import atomic_write_json

config = get_config()
log = get_logger(__name__)


def generate_deep_dive_questions(
    client: LLMClient,
    scraped_content_dir: str,
    prompt: str,
    model_name: str,
    min_content_length: int = 200,
    max_content_length: int = 0,
) -> list[dict]:
    """
    Reads markdown files from scraped_content_dir, sends each to the LLM
    to generate deeper follow-up questions.
    If max_content_length > 0, truncates documents to that length.
    """
    categories_map: dict[str, list[str]] = {}

    markdown_files = []
    for root, dirs, files in os.walk(scraped_content_dir):
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))

    if not markdown_files:
        log.warning(f"No .md files found in {scraped_content_dir}")
        return []

    for idx, filepath in enumerate(markdown_files, 1):
        filename = os.path.basename(filepath)
        parent_dir = os.path.basename(os.path.dirname(filepath))
        category_hint = parent_dir.replace("_", " ").title() if parent_dir else "General"

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                # Bounded read to avoid OOM on huge files
                read_limit = max_content_length + 1 if max_content_length > 0 else -1
                document_content = f.read(read_limit)
        except (OSError, UnicodeDecodeError) as e:
            log.error(f"Error reading file {filename}: {e}")
            continue

        if not document_content.strip():
            log.warning(f"Skipping empty file: {filename}")
            continue

        if len(document_content.strip()) < min_content_length:
            log.warning(f"Skipping short file ({len(document_content.strip())} chars < {min_content_length}): {filename}")
            continue

        if max_content_length > 0 and len(document_content) > max_content_length:
            log.warning(f"Truncating {filename} to {max_content_length} chars")
            document_content = document_content[:max_content_length]

        log.info(f"[{idx}/{len(markdown_files)}] Generating deep-dive questions from: {filename} ({len(document_content)} chars)")

        full_prompt = (
            prompt + "\n\n"
            f"Source category: {category_hint}\n\n"
            f"Document content:\n{document_content}"
        )

        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "category": {"type": "string"},
                },
            },
        }

        try:
            questions_list = client.generate(prompt=full_prompt, model=model_name, format=schema)

            if not questions_list:
                log.warning(f"Zero questions generated for {filename}")
                continue

            for item in questions_list:
                cat = item.get("category", category_hint)
                question = item.get("question", "")
                if question:
                    categories_map.setdefault(cat, []).append(question)

            log.info(f"Generated {len(questions_list)} deep-dive questions from {filename}")

        except LLMError as e:
            log.warning(f"LLM call failed for {filename}: {e}")
            continue

    result = [
        {"category": cat, "questions": qs}
        for cat, qs in categories_map.items()
    ]

    log.info(f"Deep-dive generation complete: {sum(len(r['questions']) for r in result)} questions across {len(result)} categories")
    return result


def main(
    scraped_content_dir: str = "dataset/acquisition/temp/datasources",
    output_file: str = "dataset/acquisition/temp/deep_dive_questions.json",
    model_expertise: str = config.get("DEFAULT", "model_expertise", fallback="Quality Assurance"),
    model_name: str = config.get("DEFAULT", "model_name", fallback="gemma3:27b"),
    deep_dive_prompt: str = config.get("DEFAULT", "deep_dive_prompt", fallback="Generate follow-up questions about {domain_of_expertise}."),
    min_content_length: int = config.getint("DEFAULT", "min_content_length", fallback=200),
    max_content_length: int = config.getint("DEFAULT", "max_content_length", fallback=0),
) -> str:
    """Orchestrates deep-dive question generation."""
    client = create_llm_client()
    scraped_content_dir = os.path.join(get_emtp_directory(), scraped_content_dir)
    prompt = deep_dive_prompt.format(domain_of_expertise=model_expertise)

    questions = generate_deep_dive_questions(
        client=client,
        scraped_content_dir=scraped_content_dir,
        prompt=prompt,
        model_name=model_name,
        min_content_length=min_content_length,
        max_content_length=max_content_length,
    )

    output_path = os.path.join(get_emtp_directory(), output_file)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    atomic_write_json(output_path, questions)

    log.info(f"Deep-dive questions saved to {output_path}")
    return output_path


if __name__ == "__main__":
    main()
