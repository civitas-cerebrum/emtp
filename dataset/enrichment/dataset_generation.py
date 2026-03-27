import os
import json
from typing import Optional

from util.utilities import get_config, get_logger, get_emtp_directory
from util.llm_client import LLMClient, create_llm_client
from util.llm_providers.base import LLMError
from util.file_utils import atomic_write_json

config = get_config()
log = get_logger(__name__)


def generate_qna_dataset(
    client: LLMClient,
    prompt: str,
    model_expertise: str,
    scraped_content_dirs: list[str] | str,
    model_name: str,
    min_content_length: int = 200,
    max_content_length: int = 0,
):
    """
    Generates a Q&A dataset from markdown files using an LLMClient.
    Accepts a single directory path or a list of directory paths.
    If max_content_length > 0, truncates documents to that length.
    """
    qna_dataset = []

    # Backward compatibility: wrap single string in a list
    if isinstance(scraped_content_dirs, str):
        scraped_content_dirs = [scraped_content_dirs]

    markdown_files = []
    for content_dir in scraped_content_dirs:
        source_label = "round2" if "deep" in content_dir else "round1"
        for root, dirs, files in os.walk(content_dir):
            for file in files:
                if file.endswith(".md"):
                    markdown_files.append({
                        "path": os.path.join(root, file),
                        "source": source_label,
                        "category": os.path.basename(root).replace("_", " ").title(),
                        "source_file": os.path.relpath(os.path.join(root, file), content_dir),
                    })

    if not markdown_files:
        log.warning(f"No .md files found in {scraped_content_dirs}")
        return qna_dataset

    prompt = prompt.format(domain_of_expertise=model_expertise)

    for idx, file_info in enumerate(markdown_files, 1):
        filepath = file_info["path"]
        source = file_info["source"]
        category = file_info["category"]
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                document_content = f.read()
        except Exception as e:
            log.error(f"Error reading file {filename}: {e}")
            continue

        if len(document_content.strip()) < min_content_length:
            log.warning(f"Skipping short file ({len(document_content.strip())} chars < {min_content_length}): {filename}")
            continue

        if max_content_length > 0 and len(document_content) > max_content_length:
            log.warning(f"Truncating {filename} from {len(document_content)} to {max_content_length} chars")
            document_content = document_content[:max_content_length]

        log.info(
            f"[{idx}/{len(markdown_files)}] Generating semi-synthetic data based on: {filename} ({len(document_content)} chars)"
        )

        schema = {
            "type": "object",
            "properties": {
                "qnaList": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "q": {"type": "string"},
                            "a": {"type": "string"},
                        },
                    },
                }
            },
            "required": ["qnaList"],
        }

        try:
            result = client.generate(prompt=prompt + "\n" + document_content, model=model_name, format=schema)

            qna_list = None
            if isinstance(result, dict) and "qnaList" in result:
                qna_list = result["qnaList"]
            else:
                log.warning(f"Unexpected response format for {filename}: {type(result)}")

            if qna_list:
                for pair in qna_list:
                    pair["category"] = category
                    pair["source"] = source
                    pair["source_file"] = file_info["source_file"]
                qna_dataset.extend(qna_list)

        except LLMError as e:
            log.error(f"LLM call failed for {filename}: {e}")
            continue

    return qna_dataset


def main(
    model_expertise: str = config.get(
        "DEFAULT", "model_expertise", fallback="Software Engineering"
    ),
    scraped_content_dirs: list[str] | str = "dataset/acquisition/temp/datasources",
    model_name: str = config["DEFAULT"]["model_name"],
    dataset_prompt_template: str = config["DEFAULT"]["dataset_prompt"],
):
    """
    Orchestrates Q&A dataset generation.
    Loads configuration, generates data, and saves it to a JSON file.
    """
    client = create_llm_client()

    # Normalize to list and resolve paths
    if isinstance(scraped_content_dirs, str):
        scraped_content_dirs = [scraped_content_dirs]
    scraped_content_dirs = [
        os.path.join(get_emtp_directory(), d) for d in scraped_content_dirs
    ]

    min_content_length = config.getint("DEFAULT", "min_content_length", fallback=200)
    max_content_length = config.getint("DEFAULT", "max_content_length", fallback=0)

    dataset = generate_qna_dataset(
        client=client,
        prompt=dataset_prompt_template,
        model_expertise=model_expertise,
        scraped_content_dirs=scraped_content_dirs,
        model_name=model_name,
        min_content_length=min_content_length,
        max_content_length=max_content_length,
    )

    if dataset:
        print(f"Generated {len(dataset)} Q&A pairs.")
        atomic_write_json("qna_dataset.json", dataset)
        print("Q&A dataset saved to qna_dataset.json")
    else:
        print("Failed to generate Q&A dataset.")


if __name__ == "__main__":
    main()
