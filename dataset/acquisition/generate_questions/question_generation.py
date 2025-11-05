import configparser
import json

import requests


def generate_questions(
        prompt="Generate 50 questions about {topic}.", topic="Software Engineering",
        base_url="http://localhost:8080/api/generate", model_name="gemma3:27b", authorization_token=None
):
    """
    Generates a list of questions about a specified topic using Ollama API.

    Args:
        prompt (str): Template prompt to format with the topic.
                     Default: "Generate 50 questions about {topic}."
        topic (str): Subject area for question generation.
                    Default: "Software Engineering"
        base_url (str): Base URL for the LLM API endpoint.
                       Default: "http://localhost:8080/api/generate"
        model_name (str): Name of the model to use for generation.
                         Default: "gemma3:27b"
        authorization_token (str): Optional bearer token for API authentication

    Returns:
        list: A list of question dictionaries in the format:
              [{"question": "What is...?"}, {"question": "How to...?"}, ...]
              Returns empty list if API call fails or response is invalid
    """

    print("Generating generic questions about: " + topic)

    prompt = prompt.format(topic=topic)

    request_body = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "images": None,
        "options": None,
        "format": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["questions"]
        }
    }

    headers = {"Content-Type": "application/json"}
    if authorization_token:
        headers["Authorization"] = f"Bearer {authorization_token}"

    questions = []

    try:
        response = requests.post(base_url, headers=headers, data=json.dumps(request_body))
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        json_response = response.json()

        if "response" in json_response and "questions" in json_response["response"]:
            response = json_response['response']
            questions_json = json.loads(response)
            questions = questions_json['questions']
        else:
            print(f"Unexpected response format from Ollama: {json_response}")

    except requests.exceptions.RequestException as e:
        print(f"Error making request to Ollama for file: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response from Ollama for file: {e}")

    return questions


def main(config=None):
    if config is None:
        config = configparser.ConfigParser()
        config.read('config.ini')

    topic = config['DEFAULT']['model_expertise']
    base_url = config['DEFAULT']['base_url']
    model_name = config['DEFAULT']['model_name']
    authorization_token = config['DEFAULT']['authorization_token']
    q_gen_prompt = config['DEFAULT']['q_gen_prompt']

    questions = generate_questions(q_gen_prompt, topic, base_url, model_name, authorization_token)

    if questions:
        print(f"Generated {len(questions)} domain questions.")
        with open("questions.json", "w", encoding="utf-8") as f:
            json.dump(questions, f, indent=4)
        print("Domain questions saved to qna_dataset.json")
    else:
        print("Failed to generate the domain questions.")


if __name__ == "__main__":
    main()
