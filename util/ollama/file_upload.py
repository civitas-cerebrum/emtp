from ..utilities import getConfig
import requests
import time
from typing import IO, Optional, Dict, Any


def upload_file(
    file: IO[bytes],
    base_url: str = "http://localhost:3000/api/v1/files/",
    status_check_interval: int = 2,
    request_timeout: int = 60,
    authorization_token: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Uploads a file object and waits until the processing status is 'completed' or a timeout is reached.

    Args:
        file: The file object to upload.  This is the result of `open('file.txt', 'rb')`.
        base_url (str, optional): The base URL for the API. Defaults to "http://localhost:3000/api/v1/files/".
        authorization_token (str, optional): The authorization token. Defaults to None.

    Returns:
        Optional[Dict[str, Any]]: The 'file_id' from the API response when the status is 'completed', or None if timeout is reached.
    """

    headers = {
        "Authorization": f"Bearer {authorization_token}",
        "Accept": "application/json",
    }

    files = {"file": file}
    print(base_url)
    response = requests.post(base_url, headers=headers, files=files)
    print(f"DEBUG: File upload response: {response.json()}")

    try:
        response_json = response.json()
        file_id = response_json.get("id")

        if not file_id:
            print("File ID not found in response.")
            return None

        status_url = (
            f"[{base_url}]{file_id}/process/status?stream=false"
        )
        start_time = time.time()

        while True:
            status_response = requests.get(status_url, headers=headers)
            status_response.raise_for_status()
            status_data = status_response.json()
            status = status_data.get("status")

            if status == "completed":
                print(f"File upload complete! File id: {file_id}")
                return file_id

            if time.time() - start_time > request_timeout:
                print("Timeout reached while waiting for completion.")
                return None

            print(f"Status: {status}.  Waiting...")
            time.sleep(status_check_interval)

    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
        return None
    except ValueError as e:
        print(f"Error decoding JSON: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def main(config=None, file_path="generic-questions.json"):
    if config is None:
        config = getConfig()

    owui_base_url = config["DEFAULT"]["owui_base_url"]
    ollama_uri = config["DEFAULT"]["ollama_uri"]
    files_uri = config["DEFAULT"]["owui_files_uri"]
    base_url = owui_base_url + files_uri
    model_name = config["DEFAULT"]["model_name"]
    authorization_token = config["DEFAULT"]["authorization_token"]

    try:
        with open(file_path, "rb") as file:
            status_data = upload_file(
                file, base_url, authorization_token=authorization_token
            )

            if status_data:
                print("File upload and processing completed successfully:")
                print(status_data)
            else:
                print("File upload or processing failed (timeout or other error).")
    except FileNotFoundError:
        print("File not found.")


if __name__ == "__main__":
    main()
