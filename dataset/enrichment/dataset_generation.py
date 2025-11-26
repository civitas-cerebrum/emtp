import os
import json
import requests
from typing import Optional

from util.utilities import getConfig, getLogger, getEmtpDirectory

config = getConfig()
log = getLogger(__name__)


def generate_qna_dataset(
    prompt: str,
    model_expertise: str,
    scraped_content_dir: str,
    base_url: str,
    model_name: str,
    request_timeout: int,
    authorization_token: Optional[str] = None,
):
    """
    Generates a Q&A dataset from markdown files using an external API.
    Processes files and formats questions and answers into a dataset.
    """
    qna_dataset = []
    markdown_files = []
    for root, dirs, files in os.walk(scraped_content_dir):
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))

    if not markdown_files:
        log.warning(f"No .md files found in {scraped_content_dir}")
        return qna_dataset

    prompt = prompt.format(domain_of_expertise=model_expertise)

    for filepath in markdown_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                document_content = f.read()
        except Exception as e:
            log.error(f"Error reading file {filename}: {e}")
            continue

        log.info(
            f"Generating semi-sythetic data based on: {filename} ({len(document_content)} chars)"
        )

        request_body = {
            "model": model_name,
            "keep_alive": 0,
            "prompt": prompt + "\n" + document_content,
            "stream": False,
            "images": None,
            "options": None,
            "format": {
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
            },
        }

        headers = {"Content-Type": "application/json"}
        if authorization_token:
            headers["Authorization"] = f"Bearer {authorization_token}"

        try:
            response = requests.post(
                base_url, headers=headers, json=request_body, timeout=request_timeout
            )
            response.raise_for_status()
            json_response = response.json()
            log.debug(f"Raw JSON response from Ollama for {filename}: {json_response}")

            if "response" in json_response:
                log.debug(
                    f"Content of json_response['response'] for {filename}: {json_response['response']}"
                )
                if isinstance(json_response["response"], str):
                    try:
                        qna = json.loads(json_response["response"])
                        log.debug(f"Parsed qna from string for {filename}: {qna}")
                        if "qnaList" in qna:
                            qna_list = qna["qnaList"]
                            qna_dataset.extend(qna_list)
                        else:
                            log.warning(
                                f"Key 'qnaList' not found in parsed response for file {filename}: {qna}"
                            )
                    except json.JSONDecodeError:
                        log.error(
                            f"Failed to decode JSON string from 'response' for file {filename}: {json_response['response']}"
                        )
                elif (
                    isinstance(json_response["response"], dict)
                    and "qnaList" in json_response["response"]
                ):
                    qna_list = json_response["response"]["qnaList"]
                    qna_dataset.extend(qna_list)
                else:
                    log.warning(
                        f"Unexpected response format from Ollama for file {filename}: {json_response['response']}"
                    )
            else:
                log.warning(
                    f"Key 'response' not found in JSON response from Ollama for file {filename}: {json_response}"
                )

        except requests.exceptions.ConnectionError as e:
            log.error(
                f"Connection failed to Ollama at {base_url} for file {filename}: {e}"
            )
        except requests.exceptions.Timeout as e:
            log.error(
                f"Timeout connecting to Ollama at {base_url} for file {filename}: {e}"
            )
        except requests.exceptions.HTTPError as e:
            log.error(
                f"HTTP {e.response.status_code} error from Ollama for file {filename}: {e.response.text}"
            )
        except requests.exceptions.RequestException as e:
            log.error(f"Network error connecting to Ollama for file {filename}: {e}")
        except Exception as e:
            log.error(
                f"Unexpected error processing Ollama response for file {filename}: {type(e).__name__}: {e}"
            )

    return qna_dataset


def main(
    model_expertise: str = config.get(
        "DEFAULT", "model_expertise", fallback="Software Engineering"
    ),
    scraped_content_dir: str = "dataset/acquisition/temp/text_data",
    owui_base_url: str = config["DEFAULT"]["owui_base_url"],
    ollama_uri: str = config["DEFAULT"]["ollama_uri"],
    model_name: str = config["DEFAULT"]["model_name"],
    authorization_token: str = config["DEFAULT"]["authorization_token"],
    dataset_prompt_template: str = config["DEFAULT"]["dataset_prompt"],
    request_timeout=config.getint("DEFAULT", "request_timeout", fallback=60),
):
    """
    Orchestrates Q&A dataset generation.
    Loads configuration, generates data, and saves it to a JSON file.
    """

    base_url = owui_base_url + ollama_uri
    scraped_content_dir = os.path.join(getEmtpDirectory(), scraped_content_dir)

    dataset = generate_qna_dataset(
        prompt=dataset_prompt_template,
        model_expertise=model_expertise,
        scraped_content_dir=scraped_content_dir,
        base_url=base_url,
        model_name=model_name,
        authorization_token=authorization_token,
        request_timeout=request_timeout
    )

    if dataset:
        print(f"Generated {len(dataset)} Q&A pairs.")
        with open("qna_dataset.json", "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=4)
        print("Q&A dataset saved to qna_dataset.json")
    else:
        print("Failed to generate Q&A dataset.")


if __name__ == "__main__":
    main()
