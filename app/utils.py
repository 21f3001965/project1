import os
import httpx
import logging

AIPROXY_TOKEN = os.environ.get("AIPROXY_TOKEN")


def call_llm(task, tools):
    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AIPROXY_TOKEN}",
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": task},
            {
                "role": "system",
                "content": """
                    You are an automation agent. You will receive a task in plain English. 
                    Your job is to parse the task and use function calling to determine the necessary actions.
                """
            },
        ],
        "tools": tools,
        "tool_choice": "auto",
    }

    try:
        response = httpx.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.json()  # Raises an HTTPError for bad responses (4xx, 5xx)
    except httpx.HTTPError as e:
        raise Exception(f"Error calling OpenAI API: {e}")


def read_file(file_path: str) -> str:
    logging.info(f"read file called with file_path: {file_path}")
    if not file_path:
        raise ValueError("File path is required")

    file_path = file_path.strip("/")

    if not file_path.startswith("data/"):
        raise ValueError("Cannot read file outside of data directory")   
    
    try:
        with open(file_path, "r") as file:
            return file.read()
    except FileNotFoundError:
        logging.info(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")