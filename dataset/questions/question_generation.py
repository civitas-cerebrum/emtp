import os
import json
import time
from typing import Optional
from .question_categorisation import main as categorise_questions
from ..acquisition import retrieve_url_stage, save_datasource_stage
from util.llm_client import LLMClient, create_llm_client
from util.llm_providers.base import LLMError
from util.utilities import get_config, get_logger, get_emtp_directory
from util.file_utils import atomic_write_json

config = get_config()
log = get_logger(__name__)


def generate_questions(
    client: LLMClient,
    prompt: str,
    topic: str,
    model_name: str,
    retries: int = 5,
    retry_delay: int = 2,
):
    """
    Generates a list of questions about a specified topic using the LLM.
    Retries if no questions were returned or if the request fails.
    """
    start_time = time.perf_counter()
    prompt = prompt.format(topic=topic)

    schema = {
        "type": "array",
        "items": {"type": "object", "properties": {"question": {"type": "string"}}},
    }

    for attempt in range(1, retries + 1):
        try:
            if attempt > 1:
                log.info(f"Attempt {attempt}/{retries}...")
            else:
                log.info(f"Question generation started for {topic} topic...")

            questions = client.generate(prompt=prompt, model=model_name, format=schema)

            if not questions:
                raise ValueError("API returned zero questions.")

            elapsed = time.perf_counter() - start_time
            log.info(f"Generated {len(questions)} questions in {elapsed:.2f} seconds.")
            return questions

        except (LLMError, ValueError) as e:
            log.error(f"Error: {e}")
            if attempt < retries:
                log.warning(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                log.warning("All retries exhausted...")

    raise Exception("All retries exhausted. Returning empty list.")


def main(
    topic=config.get("DEFAULT", "model_expertise", fallback="Software Engineering"),
    model_name=config.get("DEFAULT", "model_name", fallback="gemma3:27b"),
    q_gen_prompt=config.get("DEFAULT", "q_gen_prompt", fallback="Generate 50 questions about {topic}."),
    request_timeout=config.getint("DEFAULT", "request_timeout", fallback=60),
    questions_file="generated-questions.json",
    categorised_questions_file="categorised-questions.json",
):
    client = create_llm_client()

    questions = generate_questions(
        client,
        q_gen_prompt,
        topic,
        model_name,
    )

    if questions:
        atomic_write_json(questions_file, questions)
        log.info(f"Generated questions saved to {questions_file}")
    else:
        log.error("Failed to generate questions.")

    categorise_questions(
        questions_file=questions_file,
        categorised_questions_file=categorised_questions_file,
    )

    question_path = os.path.join(get_emtp_directory(), categorised_questions_file)
    retrieve_url_stage(questions_file=question_path)
    save_datasource_stage()


if __name__ == "__main__":
    main()
