import os
import configparser
import json
import aiohttp # New import for async HTTP requests
import asyncio # New import for async operations

async def generate_qna_dataset(prompt="You are an expert in {model_expertise}." ,model_expertise="Software Engineering", input_dir="dataset/acquisition/temp/datasources", base_url="http://localhost:8080/api/generate", model_name="gemma3:27b", authorization_token=None):
    """
    Generates a semi-synthetic Q&A dataset from markdown files in a directory using Ollama.

    Args:
        input_dir (str): The directory containing the markdown files.  Defaults to "dataset/acquisition/temp/datasources".
        base_url (str): The base URL for the Ollama API. Defaults to "http://localhost:11434/api/generate".
        model_name (str): The name of the Ollama model to use. Defaults to "gemma3:27b".

    Returns:
        list: A list of dictionaries, where each dictionary represents a Q&A pair.
              Returns an empty list if no files are found in the input directory or if there are errors during API calls.
    """

    qna_dataset = []
    # Recursively find all .md files in the input directory
    markdown_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))

    if not markdown_files:
        print(f"No .md files found in {input_dir}")
        return qna_dataset

    async with aiohttp.ClientSession() as session: # Use aiohttp for async requests
        for filepath in markdown_files:
            filename = os.path.basename(filepath)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    document_content = f.read()
            except Exception as e:
                print(f"Error reading file {filename}: {e}")
                continue

            print(f"Generating semi-sythetic data based on: {filename} ({len(document_content)} chars)")

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
                async with session.post(base_url, headers=headers, json=request_body) as response:
                    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                    json_response = await response.json()

                    if "response" in json_response and "qnaList" in json_response["response"]:
                            qna_string = json_response['response']
                            qna = json.loads(qna_string)
                            qna_list = qna['qnaList']
                            qna_dataset.extend(qna_list)
                    else:
                        print(f"Unexpected response format from Ollama for file {filename}: {json_response}")

            except aiohttp.ClientConnectorError as e:
                print(f"Connection failed to Ollama at {base_url} for file {filename}: {e}")
            except aiohttp.ServerTimeoutError as e:
                print(f"Timeout connecting to Ollama at {base_url} for file {filename}: {e}")
            except aiohttp.ClientResponseError as e:
                print(f"HTTP {e.status} error from Ollama for file {filename}: {e.message}")
            except aiohttp.ClientError as e:
                print(f"Network error connecting to Ollama for file {filename}: {e}")
            except json.JSONDecodeError as e:
                print(f"Invalid JSON response from Ollama for file {filename}: {e}")
            except Exception as e:
                print(f"Unexpected error processing Ollama response for file {filename}: {type(e).__name__}: {e}")

    return qna_dataset

async def main(input_dir=None): # Made main asynchronous
    config = configparser.ConfigParser()
    config.read('config.ini')

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
    dataset = await generate_qna_dataset(formatted_dataset_prompt, model_expertise, input_dir, base_url, model_name, authorization_token) # Await the async function

    if dataset:
        print(f"Generated {len(dataset)} Q&A pairs.")
        with open("qna_dataset.json", "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=4)
        print("Q&A dataset saved to qna_dataset.json")
    else:
        print("Failed to generate Q&A dataset.")

if __name__ == "__main__":
    asyncio.run(main()) # Run the async main function
