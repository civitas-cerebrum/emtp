import os
import json
from collections import defaultdict

from util.utilities import get_config, get_logger, get_emtp_directory
from util.llm_client import LLMClient, create_llm_client
from util.llm_providers.base import LLMError
from util.file_utils import atomic_write_json

config = get_config()
log = get_logger(__name__)


def convert_to_conversations(
    client: LLMClient,
    qna_pairs: list[dict],
    prompt: str,
    model_name: str,
    batch_size: int = 8,
) -> list[dict]:
    """
    Groups Q&A pairs by category, sends batches to LLM to generate
    multi-turn conversations.

    Returns list of {"messages": [{"role": "user"|"assistant", "content": "..."}]} dicts.
    """
    conversations = []

    # Group by category
    groups = defaultdict(list)
    for pair in qna_pairs:
        category = pair.get("category", "General")
        groups[category].append(pair)

    total_batches = sum(
        (len(pairs) + batch_size - 1) // batch_size
        for pairs in groups.values()
    )
    batch_num = 0

    schema = {
        "type": "object",
        "properties": {
            "conversations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
            }
        },
        "required": ["conversations"],
    }

    for category, pairs in groups.items():
        # Split into batches
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i + batch_size]
            batch_num += 1

            log.info(f"Converting batch {batch_num}/{total_batches}: {category} ({len(batch)} pairs)")

            # Format Q&A pairs for the prompt
            qa_text = "\n\n".join(
                f"Q: {p.get('q', '')}\nA: {p.get('a', '')}"
                for p in batch
            )

            full_prompt = prompt + "\n\n" + qa_text

            try:
                result = client.generate(prompt=full_prompt, model=model_name, format=schema)

                conv_messages = result.get("conversations", []) if isinstance(result, dict) else []
                if not conv_messages:
                    log.warning(f"Empty conversation returned for batch {batch_num}")
                    continue

                filtered = [
                    msg for msg in conv_messages
                    if msg.get("role") in ("user", "assistant")
                ]

                if filtered:
                    conversations.append({"messages": filtered})
                    log.info(f"Generated conversation with {len(filtered)} turns for {category}")

            except LLMError as e:
                log.warning(f"LLM call failed for batch {batch_num}: {e}")
                continue

    log.info(f"Conversation conversion complete: {len(conversations)} conversations generated")
    return conversations


def main(
    qna_dataset_file: str = "qna_dataset.json",
    output_file: str = "conversation_dataset.json",
    model_expertise: str = config.get("DEFAULT", "model_expertise", fallback="Quality Assurance"),
    model_name: str = config.get("DEFAULT", "model_name", fallback="gemma3:27b"),
    conversation_prompt: str = config.get(
        "DEFAULT", "conversation_prompt",
        fallback="Convert these Q&A pairs about {domain_of_expertise} into a conversation."
    ),
    batch_size: int = config.getint("DEFAULT", "conversation_batch_size", fallback=8),
) -> str:
    """
    Orchestrates conversation conversion.
    Returns path to the saved conversation dataset.
    """
    client = create_llm_client()
    prompt = conversation_prompt.format(domain_of_expertise=model_expertise)

    qna_path = os.path.join(get_emtp_directory(), qna_dataset_file)
    with open(qna_path, "r", encoding="utf-8") as f:
        qna_pairs = json.load(f)

    log.info(f"Loaded {len(qna_pairs)} Q&A pairs from {qna_path}")

    conversations = convert_to_conversations(
        client=client,
        qna_pairs=qna_pairs,
        prompt=prompt,
        model_name=model_name,
        batch_size=batch_size,
    )

    output_path = os.path.join(get_emtp_directory(), output_file)
    atomic_write_json(output_path, conversations)

    log.info(f"Conversation dataset saved to {output_path} ({len(conversations)} conversations)")
    return output_path


if __name__ == "__main__":
    main()
