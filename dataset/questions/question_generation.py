import os
import json
import time
import requests
from typing import Optional
from .question_categorisation import main as categorise_questions
from ..acquisition import retrieve_url_stage, save_datasource_stage
from util.utilities import getConfig, getLogger, getEmtpDirectory

config = getConfig()
log = getLogger(__name__)


def generate_questions(
    prompt: str,
    topic: str,
    base_url: str,
    model_name: str,
    request_timeout: int,
    authorization_token: Optional[str] = None,
    retries: int = 5,
    retry_delay: int = 2,
):
    """
    Generates a list of questions about a specified topic using the Ollama API.
    Retries if no questions were returned or if the request fails.
    """

    start_time = time.perf_counter()

    prompt = prompt.format(topic=topic)

    headers = {"Content-Type": "application/json"}
    if authorization_token:
        headers["Authorization"] = f"Bearer {authorization_token}"
        
    request_body = {
        "model": model_name,
        "keep_alive": 0,
        "prompt": prompt,
        "stream": False,
        "images": None,
        "options": None,
        "format": {
            "type": "array",
            "items": {"type": "object", "properties": {"question": {"type": "string"}}},
        },
    }

    for attempt in range(1, retries + 1):
        try:
            if attempt > 1:
                log.info(f"Attempt {attempt}/{retries}...")
            else:
                log.info(f"Question generation started for {topic} topic...")

            response = requests.post(
                base_url,
                headers=headers,
                data=json.dumps(request_body),
                timeout=request_timeout,
            )
            response.raise_for_status()

            json_response = response.json()

            if "response" not in json_response:
                log.error(f"Missing 'response' in API result: {json_response}")
                raise ValueError("No 'response' field returned by API.")

            questions = json.loads(json_response["response"])

            if not questions:
                log.error("API returned empty question list.")
                raise ValueError("API returned zero questions.")

            elapsed = time.perf_counter() - start_time
            log.info(f"Generated {len(questions)} questions in {elapsed:.2f} seconds.")
            return questions

        except (
            requests.exceptions.RequestException,
            json.JSONDecodeError,
            ValueError,
        ) as e:
            log.error(f"Error: {e}")
            if attempt < retries:
                log.warning(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                log.warning("All retries exhausted...")

    raise Exception("All retries exhausted. Returning empty list.")


def main(
    topic=config.get("DEFAULT", "model_expertise", fallback="Software Engineering"),
    owui_base_url=config.get(
        "DEFAULT", "owui_base_url", fallback="http://localhost:8080"
    ),
    ollama_uri=config.get("DEFAULT", "ollama_uri", fallback="/api/generate"),
    model_name=config.get("DEFAULT", "model_name", fallback="gemma3:27b"),
    authorization_token=config.get("DEFAULT", "authorization_token", fallback=None),
    q_gen_prompt=config.get(
        "DEFAULT", "q_gen_prompt", fallback="Generate 50 questions about {topic}."
    ),
    request_timeout=config.getint("DEFAULT", "request_timeout", fallback=60),
    questions_file="generated-questions.json",
    categorised_questions_file="categorised-questions.json",
):

    base_url = owui_base_url + ollama_uri

    questions = generate_questions(
        q_gen_prompt,
        topic,
        base_url,
        model_name,
        authorization_token=authorization_token,
        request_timeout=request_timeout,
    )

    if questions:
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(questions, f, indent=4)

        log.info(f"Generated questions saved to {questions_file}")
    else:
        log.error("Failed to generate questions.")

    categorise_questions(
        owui_base_url=owui_base_url,
        ollama_uri=ollama_uri,
        model_name=model_name,
        authorization_token=authorization_token,
        questions_file=questions_file,
        categorised_questions_file=categorised_questions_file,
    )

    question_path = os.path.join(getEmtpDirectory(), categorised_questions_file)

    retrieve_url_stage(questions_file=question_path)
    save_datasource_stage()


if __name__ == "__main__":
    main()
