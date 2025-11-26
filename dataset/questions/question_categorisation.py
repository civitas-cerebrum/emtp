import json
import time
import requests
import logging
from typing import Optional, List, Dict
from util.utilities import getConfig, getLogger

config = getConfig()
log = getLogger(__name__)


def categorise_questions(
    questions,
    prompt: str,
    base_url: str,
    model_name: str,
    request_timeout: int,
    authorization_token: Optional[str] = None,
) -> List[Dict[str, List[str]]]:
    """
    Categorizes a list of questions using a language model. Each question is categorized
    individually using the `categorise_question` helper method. Categories accumulate
    across all questions.

    Returns:
        list[dict]: A list of category objects:
        [
            {"category": "Networking", "questions": ["What is DNS?", "What is HTTP?"]},
            {"category": "Security", "questions": ["What is encryption?"]}
        ]
    """

    log.info(f"Question categorisation started for {len(questions)} questions...")

    start_time = time.perf_counter()

    if not questions:
        log.info("No questions provided.")
        return []

    categories_map: Dict[str, List[str]] = {}

    for q in questions:
        question = q["question"]
        log.debug(f"Categorising question: {question}")

        result = categorise_question(
            question=question,
            prompt=prompt,
            existing_categories=list(categories_map.keys()),
            base_url=base_url,
            model_name=model_name,
            authorization_token=authorization_token,
            request_timeout=request_timeout,
        )

        log.debug(
            f"Categorisation result: {result["category"] if result else 'Unsuccessful'}"
        )

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
    log.info(
        f"Categorised {len(questions)} questions to {len(categorized_list)} categories in {elapsed:.2f} seconds."
    )

    return categorized_list


def categorise_question(
    question: str = "What is the meaning of life?",
    existing_categories: List[str] = [],
    prompt: str = "Categorise the following question into one of the existing categories or create a new category if none fit.",
    base_url: str = "http://localhost:8080/api/generate",
    model_name: str = "gemma3:27b",
    authorization_token: Optional[str] = None,
    request_timeout: int = 60,
    verbose: bool = False,
) -> Optional[Dict[str, str]]:
    """
    Send a question to the model and return its categorised interpretation.
    Expected model output: JSON array of objects:
    [
        {"question": "...", "category": "..."}
    ]
    """

    prompt = (
        f"Instruction: {prompt} "
        f"Question: {question}\n"
        f"Existing categories: {existing_categories}"
    )

    request_body = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "images": None,
        "options": None,
        "format": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "category": {"type": "string"},
            },
            "required": ["question", "category"],
        },
    }

    headers = {"Content-Type": "application/json"}
    if authorization_token:
        headers["Authorization"] = f"Bearer {authorization_token}"

    try:
        response = requests.post(
            base_url,
            headers=headers,
            data=json.dumps(request_body),
            timeout=request_timeout,
        )
        response.raise_for_status()

        json_response = response.json()

        raw = json_response.get("response")

        if not raw:
            log.warning(f"Unexpected response format from model: {json_response}")
            return None

        return json.loads(raw)

    except requests.exceptions.RequestException as e:
        log.error(f"Error making request to Ollama: {e}")
    except json.JSONDecodeError as e:
        log.error(f"Error decoding JSON response from Ollama: {e}")

    return None


def main(
    owui_base_url=config.get(
        "DEFAULT", "owui_base_url", fallback="http://localhost:8080"
    ),
    ollama_uri=config.get("DEFAULT", "ollama_uri", fallback="/api/generate"),
    model_name=config.get("DEFAULT", "model_name", fallback="gemma3:27b"),
    authorization_token=config.get("DEFAULT", "authorization_token", fallback=None),
    q_categorisation_prompt=config.get(
        "DEFAULT",
        "q_categorisation_prompt",
        fallback="Categorise the following question into one of the existing categories or create a new category if none fit.",
    ),
    request_timeout=config.getint("DEFAULT", "request_timeout", fallback=60),
    questions_file="generated-questions.json",
    categorised_questions_file="categorised-questions.json",
):

    base_url = owui_base_url + ollama_uri

    try:
        with open(questions_file, "r") as file:
            questions = json.load(file)

        categorized_questions = categorise_questions(
            questions=questions,
            prompt=q_categorisation_prompt,
            base_url=base_url,
            model_name=model_name,
            request_timeout=request_timeout,
            authorization_token=authorization_token,
        )

        if categorized_questions:
            with open(categorised_questions_file, "w", encoding="utf-8") as f:
                json.dump(categorized_questions, f, indent=4)

            print(f"Categorised questions saved to {categorised_questions_file}")
        else:
            print("Failed to generate categorised questions.")

    except FileNotFoundError:
        print(f"File not found: {categorised_questions_file}")
    except json.JSONDecodeError:
        print(
            f"Error decoding JSON from {categorised_questions_file}. Check the file format."
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
