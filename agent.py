import subprocess
from utils import call_llm, read_file
import json
import os
import logging
import datetime
from dateutil.parser import parse

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def run_task(task):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "online_script_runner",
                "description": "Use this function if the task requires to install a package and run a script from a url with provided arguments.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The url of the script to run.",
                        },
                        "email": {
                            "type": "string",
                            "description": "The email pass as an argument to the script.",
                        },
                        "package": {
                            "type": "string",
                            "description": "The package to install if not already installed, described in the task if any else leave blank.",
                        },
                    },
                    "required": ["url", "arguments", "package"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "use this function if the task requires to read a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path of the file to read.",
                        }
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "use this function if the task requires to write content to a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path of the file to write.",
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file.",
                        },
                    },
                    "required": ["file_path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "format_file",
                "description": "use this function if the task requires to format a file using prettier.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path of the file to format.",
                        },
                        "prettier_version": {
                            "type": "string",
                            "description": "The version of prettier to use.",
                        },
                    },
                    "required": ["file_path", "prettier_version"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "count_dates",
                "description": "Count the number of occurances of a specific weekday, date or month in a list of dates in a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_file": {
                            "type": "string",
                            "description": "Path to the file containing the dates, one date per line.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Path to the file to write the count to.",
                        },
                        "date_part": {
                            "type": "string",
                            "enum": ["weekday", "date", "month"],
                            "description": "The part of the date to count. can be 'weekday', 'date' or 'month'.",
                        },
                        "value_to_count": {
                            "type": "string",
                            "description": """The specific weekday, date or month to count. 
                            For weekday, use the full name (e.g., 'Monday'). 
                            For date, use YYYY-MM-DD format. 
                            For month, use the full month name (e.g., 'January')""",
                        },
                    },
                    "required": [
                        "input_file",
                        "output_file",
                        "date_part",
                        "value_to_count",
                    ],
                },
            },
        },
    ]

    llm_response = call_llm(task, tools)
    logging.info(f"respose: {llm_response}")

    try:
        task_details = llm_response["choices"][0]["message"]["tool_calls"][0][
            "function"
        ]
        function_name = task_details["name"]
        arguments = json.loads(task_details["arguments"])
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in llm response")
    except Exception as e:
        raise ValueError(f"LLM response error: {e}")

    try:
        if function_name == "online_script_runner":
            result = online_script_runner(**arguments)
            return f"Command executed: {result}"
        elif function_name == "read_file":
            content = read_file(**arguments)
            return content
        elif function_name == "write_file":
            write_file(**arguments)
            return "File written successfully"
        elif function_name == "format_file":
            format_file_with_prettier(**arguments)
            return "File formatted successfully"
        elif function_name == "count_dates":
            count_dates(**arguments)
            return f"Date counting completed. Result written to {arguments.get('output_file')}"
        else:
            raise ValueError(f"Unknown function name: {function_name}")
    except Exception as e:
        raise Exception(f"Error executing function: {e}")


def online_script_runner(url, email, package):
    logging.info(
        f"online script runner called with url: {url}, email: {email}, package: {package}"
    )
    if (
        package
        and package != ""
        and package not in subprocess.check_output(["pip", "freeze"]).decode("utf-8")
    ):
        subprocess.run(["pip", "install", package])
    try:
        command = f"uv run {url} {email} --root ./data"
        subprocess.run(command, shell=True)
        return "Script executed successfully"
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error executing script: {e.stderr}")


def write_file(file_path, content):
    logging.info(f"write file called with file_path: {file_path}, content: {content}")
    if not file_path.startswith("/data/"):
        raise ValueError("cannot write file outside of data directory")
    if os.path.exists(file_path) and not content:
        raise ValueError("Cannot delete file")

    with open(file_path, "w") as file:
        file.write(content)


def format_file_with_prettier(file_path, prettier_version):
    logging.info(
        f"format file called with file_path: {file_path}, prettier_version: {prettier_version}"
    )
    file_path = file_path.strip("/")
    if not file_path.startswith("data/"):
        raise ValueError("cannot format file outside of data directory")

    try:
        # Check if npm is installed
        try:
            subprocess.run(["npm", "-v"], check=True, capture_output=True)
            npm_installed = True
        except FileNotFoundError:
            npm_installed = False

        if not npm_installed:
            raise Exception(
                "npm is not installed. Please install npm in the Docker image."
            )

        # Check if prettier is already installed with the correct version
        try:
            result = subprocess.run(
                ["npx", "prettier", "--version"],
                check=True,
                capture_output=True,
                text=True,
            )
            installed_version = result.stdout.strip()
            if installed_version == prettier_version:
                logging.info("Prettier is already installed with the correct version.")
                already_installed = True
            else:
                already_installed = False
        except subprocess.CalledProcessError:
            already_installed = False

        # Install Prettier only if it's not already installed or the version is different
        if not already_installed:
            print(f"Installing prettier@{prettier_version}...")
            subprocess.run(
                ["npm", "install", f"prettier@{prettier_version}"], check=True
            )

        # Format the file using Prettier
        subprocess.run(
            ["npx", f"prettier@{prettier_version}", "--write", file_path], check=True
        )

        return
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error formatting file: {e}")


def count_dates(input_file, output_file, date_part, value_to_count):
    logging.info(
        f"count dates called with input_file: {input_file}, output_file: {output_file}, date_part: {date_part}, value_to_count: {value_to_count}"
    )
    input_file = input_file.strip("/")
    output_file = output_file.strip("/")

    if not input_file.startswith("data/") or not output_file.startswith("data/"):
        raise ValueError("File paths must be within data directory")

    try:
        with open(input_file, "r") as f:
            dates = f.readlines()

        count = 0
        for date_str in dates:
            date_str = date_str.strip()
            try:
                date_obj = parse(date_str)

            except ValueError:
                logging.info(f"Skipping invalid date format: {date_str}")
                continue

            if date_part == "weekday":
                if date_obj.strftime("%A").lower() == value_to_count.lower():
                    count += 1
            elif date_part == "date":
                if date_obj.strftime("%Y-%m-%d") == value_to_count:
                    count += 1
            elif date_part == "month":
                if date_obj.strftime("%B").lower() == value_to_count.lower():
                    count += 1
            else:
                raise ValueError(f"Invalid date_part: {date_part}")

            with open(output_file, "w") as f:
                f.write(str(count))

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {input_file}")
    except Exception as e:
        raise Exception(f"Error counting dates: {e}")
