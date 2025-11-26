import json
import time
import requests
from typing import Optional
from util.utilities import getConfig


def generate_questions(
    prompt: str = "Generate 50 questions about {topic}.",
    topic: str = "Software Engineering",
    base_url: str = "http://localhost:8080/api/generate",
    model_name: str = "gemma3:27b",
    authorization_token: Optional[str] = None,
    request_timeout: int = 60,
):
    """
    Generates a list of questions about a specified topic using the Ollama API.

    Args:
        prompt (str): Template prompt with `{topic}` placeholder.
        topic (str): Subject area for question generation.
        base_url (str): API URL.
        model_name (str): LLM model name.
        authorization_token (str): Optional API token.

    Returns:
        list: List of dictionaries like:
              [{"question": "..."}]
              Returns empty list if API call fails.
    """
    start_time = time.perf_counter()

    print(f"Generating generic questions about: {topic}")

    prompt = prompt.format(topic=topic)

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

        if "response" in json_response:
            questions = json.loads(json_response["response"])

            elapsed = time.perf_counter() - start_time
            print(f"Generation completed in {elapsed:.2f} seconds.")

            return questions
        else:
            print(f"Unexpected response format from API: {json_response}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"HTTP error during request: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")

    return []


def main(config=None):
    if config is None:
        config = getConfig()

    topic = config["DEFAULT"]["model_expertise"]
    owui_base_url = config["DEFAULT"]["owui_base_url"]
    ollama_uri = config["DEFAULT"]["ollama_uri"]
    base_url = owui_base_url + ollama_uri
    model_name = config["DEFAULT"]["model_name"]
    authorization_token = config["DEFAULT"]["authorization_token"]
    q_gen_prompt = config["DEFAULT"]["q_gen_prompt"]

    questions = generate_questions(
        q_gen_prompt, topic, base_url, model_name, authorization_token
    )

    if questions:
        print(f"Generated {len(questions)} domain questions.")
        with open("generic-questions.json", "w", encoding="utf-8") as f:
            json.dump(questions, f, indent=4)
        print("Domain questions saved to generic-questions.json")
    else:
        print("Failed to generate domain questions.")


if __name__ == "__main__":
    main()
