import os
import configparser
import json
import aiohttp # New import for async HTTP requests
import asyncio # New import for async operations
import logging # Import logging

logger = logging.getLogger(__name__) # Initialize logger

async def generate_qna_dataset(prompt="You are an expert in {model_expertise}." ,model_expertise="Software Engineering", input_dir="../acquisition/temp/text_data", base_url="http://localhost:8080/api/generate", model_name="gemma3:27b", authorization_token=None):
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
    processed_files = []
    failed_files = []
    text_files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]

    if not text_files:
        logger.warning(f"No .txt files found in {input_dir}")
        return qna_dataset

    async with aiohttp.ClientSession() as session: # Use aiohttp for async requests
        for filename in text_files:
            filepath = os.path.join(input_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    document_content = f.read()
            except Exception as e:
                logger.error(f"Error reading file {filename}: {e}")
                failed_files.append((filename, str(e)))
                continue
 
            logger.debug("Generating semi-sythetic data based on: " + filename) # Change to debug
 
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
                        error_msg = f"Unexpected response format from Ollama for file {filename}: {json_response}"
                        logger.error(error_msg)
                        failed_files.append((filename, error_msg))
 
            except aiohttp.ClientError as e: # Use aiohttp's exception for client errors
                error_msg = f"Error making request to Ollama for file {filename}: {e}"
                logger.error(error_msg)
                failed_files.append((filename, error_msg))
            except json.JSONDecodeError as e:
                error_msg = f"Error decoding JSON response from Ollama for file {filename}: {e}"
                logger.error(error_msg)
                failed_files.append((filename, error_msg))
            else:
                processed_files.append(filename) # Only add to processed if no exceptions
 
    if processed_files:
        logger.info(f"Successfully generated semi-synthetic data for {len(processed_files)} files: {', '.join(processed_files)}")
    if failed_files:
        logger.error(f"Failed to generate semi-synthetic data for {len(failed_files)} files:")
        for filename, error in failed_files:
            logger.error(f"  - {filename}: {error}")
 
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
    qna_dataset = await generate_qna_dataset(formatted_dataset_prompt, model_expertise, input_dir, base_url, model_name, authorization_token) # Await the async function

    if qna_dataset:
        logger.info(f"Generated {len(qna_dataset)} Q&A pairs.")
        with open("qna_dataset.json", "w", encoding="utf-8") as f:
            json.dump(qna_dataset, f, indent=4)
        logger.info("Q&A dataset saved to qna_dataset.json")
        return {"success": 1, "failed": 0, "count": len(qna_dataset)}
    else:
        logger.warning("Failed to generate any Q&A dataset.") # Changed message to be more precise
        return {"success": 0, "failed": 1, "count": 0}

if __name__ == "__main__":
    asyncio.run(main()) # Run the async main function
