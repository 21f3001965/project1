import os
import httpx
import logging
import csv
import json
import pandas as pd
import docx

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
    
    
    
def extract_text_from_csv(file_path):
    """Extracts all content from a CSV file as a list of strings."""
    content = []
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            content.append(" | ".join(row))  # Join row content
    return content


def extract_text_from_json(file_path):
    """Extracts all content from a JSON file."""
    content = []
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

        def extract_from_json(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    extract_from_json(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_from_json(item)
            else:
                content.append(str(obj))  # Convert numbers/booleans to string

        extract_from_json(data)
    return content


def extract_text_from_excel(file_path):
    """Extracts all content from an Excel file (.xls, .xlsx)."""
    content = []
    df = pd.read_excel(file_path, sheet_name=None)  # Read all sheets
    for sheet_name, sheet in df.items():
        for col in sheet.columns:
            for value in sheet[col]:
                content.append(str(value))  # Convert all values to string
    return content



def extract_text_from_word(file_path):
    """Extracts all content from a Word (.docx) file."""
    content = []
    doc = docx.Document(file_path)
    for para in doc.paragraphs:
        content.append(para.text.strip())
    return content
