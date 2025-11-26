import os
import configparser
import json
import requests

def categorise_questions(
        prompt="Categorise these questions in the specified format.",
        base_url="http://localhost:8080/api/generate", 
        model_name="gemma3:27b", 
        authorization_token=None
):
    """

    """

    print("Performing question categorisation.")

    request_body = {
        "model": model_name,
        "keep_alive": 0,
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

    questions = []

    try:
        response = requests.post(
            base_url, 
            headers=headers, 
            data=json.dumps(request_body), 
            timeout=60
            )
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        json_response = response.json()
        
        print(json_response['response'])

        if "response" in json_response:
            questions = json.loads(json_response['response'])
        else:
            print(f"Unexpected response format from Ollama: {json_response}")

    except requests.exceptions.RequestException as e:
        print(f"Error making request to Ollama for file: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response from Ollama for file: {e}")

    return questions