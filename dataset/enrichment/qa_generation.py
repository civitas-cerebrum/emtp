import os
import configparser
import requests
import json

def generate_qna_dataset(prompt="You are an expert in {model_expertise}." ,model_expertise="Software Engineering", input_dir="../acquisition/temp/text_data", base_url="http://localhost:8080/api/generate", model_name="gemma3:27b", authorization_token=None):
    """
    Generates a semi-synthetic Q&A dataset from text files in a directory using Ollama.

    Args:
        input_dir (str): The directory containing the text files.  Defaults to "../acquisition/temp/text_data".
        base_url (str): The base URL for the Ollama API. Defaults to "http://localhost:11434/api/generate".
        model_name (str): The name of the Ollama model to use. Defaults to "gemma3:27b".

    Returns:
        list: A list of dictionaries, where each dictionary represents a Q&A pair.
              Returns an empty list if no files are found in the input directory or if there are errors during API calls.
    """

    qna_dataset = []
    text_files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]

    if not text_files:
        print(f"No .txt files found in {input_dir}")
        return qna_dataset

    for filename in text_files:
        filepath = os.path.join(input_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                document_content = f.read()
        except Exception as e:
            print(f"Error reading file {filename}: {e}")
            continue

        print("Generating semi-sythetic data based on: " + filename)

        prompt = prompt.format(domain_of_expertise=model_expertise)
        
        request_body = {
            "model": model_name,
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
            response = requests.post(base_url, headers=headers, data=json.dumps(request_body))
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            json_response = response.json()

            if "response" in json_response and "qnaList" in json_response["response"]:
                    qna_string = json_response['response']
                    qna = json.loads(qna_string)
                    qna_list = qna['qnaList']
                    qna_dataset.extend(qna_list)
            else:
                print(f"Unexpected response format from Ollama for file {filename}: {json_response}")

        except requests.exceptions.RequestException as e:
            print(f"Error making request to Ollama for file {filename}: {e}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response from Ollama for file {filename}: {e}")

    return qna_dataset

def main(input_dir=None, config=None):
    if(config==None):
        config = configparser.ConfigParser()
        config.read('config.ini')

    model_expertise = config['DEFAULT']['model_expertise']
    if input_dir == None:
        input_dir = config['DEFAULT']['input_dir']
    base_url = config['DEFAULT']['base_url']
    model_name = config['DEFAULT']['model_name']
    authorization_token = config['DEFAULT']['authorization_token']
    dataset_prompt = config['DEFAULT']['dataset_prompt']

    # Generate dataset
    dataset = generate_qna_dataset(dataset_prompt, model_expertise, input_dir, base_url, model_name, authorization_token)

    if dataset:
        print(f"Generated {len(dataset)} Q&A pairs.")
        with open("qna_dataset.json", "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=4)
        print("Q&A dataset saved to qna_dataset.json")
    else:
        print("Failed to generate Q&A dataset.")

if __name__ == "__main__":
    main()