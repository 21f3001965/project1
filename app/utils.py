import os
import httpx # type: ignore
import csv
import json
import pandas as pd
import docx # type: ignore

AIPROXY_TOKEN = os.environ.get("AIPROXY_TOKEN")


def request_constructor():
    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AIPROXY_TOKEN}",
    }
    return url, headers


def call_llm_with_functions(task, tools):
    print("llm_called")
    url, headers = request_constructor()

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": task},
            {
                "role": "system",
                "content": """
                    You are an automation agent. You will receive a task in plain English. 
                    Your job is to parse the task and use function calling to determine the necessary actions.
                """,
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
        print(f"Error calling OpenAI API: {e} {response.text}")
        raise Exception(f"Error calling OpenAI API: {e}")


def llm_text_extraction(extraction_instruction, content):

    schema = {
        "type": "object",
        "properties": {
            "extracted_information": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The extracted information from the content.",
            }
        },
        "required": ["extracted_information"],
    }

    url, headers = request_constructor()
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": f'Extract the "{extraction_instruction}" from the content provided.',
            },
            {"role": "user", "content": content},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "extract_information",
                    "description": "Extract information from the content.",
                    "parameters": schema,
                },
            }
        ],
        "tool_choice": {
            "type": "function",
            "function": {"name": "extract_information"},
        },
    }
    try:
        response = httpx.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        
        return response.json()
    except httpx.HTTPError as e:
        raise Exception(f"Error calling OpenAI API: {e}")


def llm_process_image(image_url, image_extension, processing_instruction):

    url, headers = request_constructor()
    modified_instruction = f"""
    You are an expert document analyst reviewing an image-based record.
    Carefully examine the provided image and follow the instructions:
    
    {processing_instruction}
    """
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert specializing in extracting structured information from images. Provide detailed and well-organized responses."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Analyze the provided image and extract relevant details. {modified_instruction}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "detail": "high",
                            "url": f"data:image/{image_extension};base64,{image_url}"
                        }
                    }
                ]
            }
        ]
    }
    
    try: 
        response = httpx.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        raise Exception(f"Error calling OpenAI API: {e}")

def text_embedding_llm(texts):
    url = "https://aiproxy.sanand.workers.dev/openai/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AIPROXY_TOKEN}",
    }
    data = {
        "input": texts,
        "model": "text-embedding-3-small",
        "encoding_format": "float"
    }

    try:
        response = httpx.post(url, headers=headers, data= json.dumps(data), timeout=10)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        raise Exception(f"Error calling OpenAI API: {e}")


def validate_path(file_path):
    if not file_path:
        raise ValueError("File path is required")

    file_path = file_path.strip("/")  # Move this after the None check

    if not file_path.startswith("data/"):
        raise ValueError("Cannot read file outside of data directory")
    return file_path



def read_file(file_path: str) -> str:
    file_path = validate_path(file_path)

    try:
        with open(file_path, "r") as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")


def extract_text_from_csv(file_path):
    """Extracts all content from a CSV file as a list of strings."""
    file_path = validate_path(file_path)

    content = []
    try:
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                content.append(" | ".join(row))  # Join row content
        return content
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")


def extract_text_from_json(file_path):
    """Extracts all content from a JSON file."""
    file_path = validate_path(file_path)

    content = []
    try:
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
    except Exception as e:
        raise ValueError(f"Error reading JSON file: {e}")


def extract_text_from_excel(file_path):
    """Extracts all content from an Excel file (.xls, .xlsx)."""
    file_path = validate_path(file_path)

    try:
        content = []
        df = pd.read_excel(file_path, sheet_name=None)  # Read all sheets
        for sheet_name, sheet in df.items():
            for col in sheet.columns:
                for value in sheet[col]:
                    content.append(str(value))  # Convert all values to string
        return content
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")


def extract_text_from_word(file_path):
    """Extracts all content from a Word (.docx) file."""
    file_path = validate_path(file_path)

    try:
        content = []
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            content.append(para.text.strip())
        return content
    except Exception as e:
        raise ValueError(f"Error reading Word file: {e}")
