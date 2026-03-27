import json
import time
from typing import Optional, List, Dict
from util.llm_client import LLMClient, create_llm_client
from util.llm_providers.base import LLMError
from util.utilities import get_config, get_logger
from util.file_utils import atomic_write_json

config = get_config()
log = get_logger(__name__)


def categorise_questions(
    client: LLMClient,
    questions,
    prompt: str,
    model_name: str,
) -> List[Dict[str, List[str]]]:
    start_time = time.perf_counter()
    log.info(f"Question categorisation started for {len(questions)} questions...")

    if not questions:
        log.info("No questions provided.")
        return []

    categories_map: Dict[str, List[str]] = {}

    for q in questions:
        question = q["question"]
        log.debug(f"Categorising question: {question}")

        result = categorise_question(
            client=client,
            question=question,
            prompt=prompt,
            existing_categories=list(categories_map.keys()),
            model_name=model_name,
        )

        log.debug(f"Categorisation result: {result['category'] if result else 'Unsuccessful'}")

        if not result:
            log.warning(f"Skipping question due to model error: {q}")
            continue

        category = result["category"]
        question_text = result["question"]

        if not category:
            log.warning(f"Invalid response structure for question: {q}")
            continue

        if category not in categories_map:
            categories_map[category] = []
        categories_map[category].append(question_text)

    categorized_list = [
        {"category": cat, "questions": qs} for cat, qs in categories_map.items()
    ]

    elapsed = time.perf_counter() - start_time
    log.info(f"Categorised {len(questions)} questions to {len(categorized_list)} categories in {elapsed:.2f} seconds.")
    return categorized_list


def categorise_question(
    client: LLMClient,
    question: str,
    existing_categories: list[str],
    prompt: str,
    model_name: str,
) -> Optional[Dict[str, str]]:
    """Send a question to the model and return its categorised interpretation."""
    full_prompt = (
        f"Instruction: {prompt} "
        f"Question: {question}\n"
        f"Existing categories: {existing_categories}"
    )

    schema = {
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "category": {"type": "string"},
        },
        "required": ["question", "category"],
    }

    try:
        return client.generate(prompt=full_prompt, model=model_name, format=schema)
    except LLMError as e:
        log.error(f"Error categorising question: {e}")
        return None


def main(
    model_name=config.get("DEFAULT", "model_name", fallback="gemma3:27b"),
    q_categorisation_prompt=config.get(
        "DEFAULT", "q_categorisation_prompt",
        fallback="Categorise the following question into one of the existing categories or create a new category if none fit.",
    ),
    questions_file="generated-questions.json",
    categorised_questions_file="categorised-questions.json",
):
    client = create_llm_client()

    try:
        with open(questions_file, "r") as file:
            questions = json.load(file)

        categorized_questions = categorise_questions(
            client=client,
            questions=questions,
            prompt=q_categorisation_prompt,
            model_name=model_name,
        )

        if categorized_questions:
            atomic_write_json(categorised_questions_file, categorized_questions)
            print(f"Categorised questions saved to {categorised_questions_file}")
        else:
            print("Failed to generate categorised questions.")

    except FileNotFoundError:
        print(f"File not found: {questions_file}")
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {questions_file}. Check the file format.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
