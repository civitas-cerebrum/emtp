import os
import json
import requests

from util.utilities import getConfig

def generate_qna_dataset(prompt="You are an expert in {model_expertise}.", model_expertise="Software Engineering", input_dir="dataset/acquisition/temp/datasources", base_url="http://localhost:8080/api/generate", model_name="gemma3:27b", authorization_token=None):
    """
    Generates a Q&A dataset from markdown files using an external API.
    Processes files and formats questions and answers into a dataset.
    """
    qna_dataset = []  # Initialize qna_dataset
    # Recursively find all .md files in the input directory
    markdown_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))

    if not markdown_files:
        print(f"No .md files found in {input_dir}")
        return qna_dataset

    # Format the prompt once before the loop
    formatted_prompt = prompt.format(domain_of_expertise=model_expertise)

    for filepath in markdown_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                document_content = f.read()
        except Exception as e:
            print(f"Error reading file {filename}: {e}")
            continue

        print(f"Generating semi-sythetic data based on: {filename} ({len(document_content)} chars)")
        
        request_body = {
            "model": model_name,
            "keep_alive": 0,
            "prompt": formatted_prompt + "\n" + document_content,
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
                                "a": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["qnaList"]
            }
        }

        headers = {"Content-Type": "application/json"}
        if authorization_token:
            headers["Authorization"] = f"Bearer {authorization_token}"

        try:
            response = requests.post(base_url, headers=headers, json=request_body)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            json_response = response.json()
            print(f"DEBUG: Raw JSON response from Ollama for {filename}: {json_response}") # Added debug print

            # Check if 'response' key exists and is a string, then parse it
            if "response" in json_response:
                print(f"DEBUG: Content of json_response['response'] for {filename}: {json_response['response']}") # Added debug print
                if isinstance(json_response["response"], str):
                    try:
                        qna = json.loads(json_response["response"])
                        print(f"DEBUG: Parsed qna from string for {filename}: {qna}") # Added debug print
                        if "qnaList" in qna:
                            qna_list = qna["qnaList"]
                            qna_dataset.extend(qna_list)
                        else:
                            print(f"Key 'qnaList' not found in parsed response for file {filename}: {qna}")
                    except json.JSONDecodeError:
                        print(f"Failed to decode JSON string from 'response' for file {filename}: {json_response['response']}")
                elif isinstance(json_response["response"], dict) and "qnaList" in json_response["response"]:
                    # If 'response' is already a dict and contains 'qnaList'
                    qna_list = json_response["response"]["qnaList"]
                    qna_dataset.extend(qna_list)
                else:
                    print(f"Unexpected response format from Ollama for file {filename}: {json_response['response']}")
            else:
                print(f"Key 'response' not found in JSON response from Ollama for file {filename}: {json_response}")

        except requests.exceptions.ConnectionError as e:
            print(f"Connection failed to Ollama at {base_url} for file {filename}: {e}")
        except requests.exceptions.Timeout as e:
            print(f"Timeout connecting to Ollama at {base_url} for file {filename}: {e}")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP {e.response.status_code} error from Ollama for file {filename}: {e.response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Network error connecting to Ollama for file {filename}: {e}")
        except Exception as e:
            print(f"Unexpected error processing Ollama response for file {filename}: {type(e).__name__}: {e}")

    return qna_dataset

def main(config=None, input_dir=None):
    if config is None:
        config = getConfig()
    """
    Orchestrates Q&A dataset generation.
    Loads configuration, generates data, and saves it to a JSON file.
    """

    model_expertise = config['DEFAULT']['model_expertise']
    if input_dir == None:
        input_dir = config['DEFAULT']['input_dir']
    base_url = config['DEFAULT']['base_url']
    model_name = config['DEFAULT']['model_name']
    authorization_token = config['DEFAULT']['authorization_token']
    dataset_prompt_template = config['DEFAULT']['dataset_prompt']
    # Format the prompt with model_expertise before passing it
    formatted_dataset_prompt = dataset_prompt_template.format(domain_of_expertise=model_expertise)

    # Generate dataset
    dataset = generate_qna_dataset(formatted_dataset_prompt, model_expertise, input_dir, base_url, model_name, authorization_token)

    if dataset:
        print(f"Generated {len(dataset)} Q&A pairs.")
        with open("qna_dataset.json", "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=4)
        print("Q&A dataset saved to qna_dataset.json")
    else:
        print("Failed to generate Q&A dataset.")

if __name__ == "__main__":
    main()