from utils import call_llm, read_file
import json
import logging
from helper import (
    online_script_runner,
    write_file,
    format_file_with_prettier,
    count_dates,
    sort_contacts,
    extract_log_info,
    extract_markdown_headers,
)


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
        {
            "type": "function",
            "function": {
                "name": "sort_contacts",
                "description": "Sort a JSON array of contacts in a file based on specified fields and order",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_file": {
                            "type": "string",
                            "description": "Path to the JSON file containing the array of contacts.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Path to the file to write the sorted JSON array to.",
                        },
                        "sort_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": """
                            Array of the field names to sort by (e.g., ['lastname', 'first_name']).
                            The order of fields in this array dertermines the sorting priority.
                            """,
                        },
                        "sort_direction": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["asc", "desc"]},
                            "description": """
                            Array of sort directions 
                            ('asc' for ascending, 'desc' for descending)
                            corresponding to the sort_fields. 
                            Must be the same length as sort_fields.
                            """,
                        },
                    },
                    "required": [
                        "input_file",
                        "output_file",
                        "sort_fields",
                        "sort_direction",
                    ],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "extract_log_info",
                "description": """"Extracts information from .log files based on various criteria, writing the extracted content to an output file.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_directory": {
                            "type": "string",
                            "description": "Path to the directory containing the .log files.",
                        },
                        "sort_order": {
                            "type": "string",
                            "enum": [
                                "newest",
                                "oldest",
                                "name_asc",
                                "name_desc",
                                "none",
                                "size_asc",
                                "size_desc",
                            ],
                            "description": """How to sort the .log files before extraction. 
                                'newest' is most recently modified first, 
                                'oldest' is least recently modified first, 
                                'name_asc' is alphabetical, 
                                'name_desc' is reverse alphabetical, 
                                'size_asc' is smallest first, 
                                'size_desc' is largest first and 
                                'none' indicates no sorting.
                            """,
                        },
                        "date_filter_type": {
                            "type": "string",
                            "enum": ["before", "after", "on", "between", "none"],
                            "description": """Filter .log files based on their modification date. 
                                'before' for files modified before a certain date, 
                                'after' for after a date, 
                                'on' for a specific date, 
                                'between' for a date range and
                                'none' to extract from all files.
                            """,
                        },
                        "date_filter_value": {
                            "type": "string",
                            "description": """
                                The date or date range for filtering. 
                                If date_filter_type is 'before', 'after', or 'on', provide a single date (YYYY-MM-DD). 
                                If 'between', provide two dates separated by a comma (YYYY-MM-DD,YYYY-MM-DD). 
                                Required when date_filter_type is not 'none'.
                            """,
                        },
                        "num_files": {
                            "type": "integer",
                            "description": "(Optional) The number of .log files to process. If omitted, all log files are processed.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Path to the file to write the extracted lines to.",
                        },
                        "extraction_type": {
                            "type": "string",
                            "enum": [
                                "last",
                                "first",
                                "all",
                                "line_number",
                                "regex",
                                "lines_range",
                            ],
                            "description": """
                                What to extract from each .log file. 
                                'first' is the first line, 
                                'last' is the last line, 
                                'all' means all lines joined, 
                                'line_number' extracts a specific line, 
                                'regex' extracts lines matching a pattern, 
                                and 'lines_range' extracts a range of lines.
                            """,
                        },
                        "line_number": {
                            "type": "integer",
                            "description": "(Optional) The line number to extract (1-based).  Required if extraction_type is 'line_number'.",
                        },
                        "lines_range_start": {
                            "type": "integer",
                            "description": """
                                (Optional) The starting line number to extract (1-based). 
                                Required if extraction_type is 'lines_range'.
                            """,
                        },
                        "lines_range_end": {
                            "type": "integer",
                            "description": "(Optional) The ending line number to extract (1-based, inclusive). Required if extraction_type is 'lines_range'.",
                        },
                        "regex_pattern": {
                            "type": "string",
                            "description": "(Optional) The regular expression pattern to match lines.  Required if extraction_type is 'regex'.",
                        },
                    },
                    "required": [
                        "log_directory",
                        "sort_order",
                        "output_file",
                        "extraction_type",
                        "date_filter_type",
                    ],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "extract_markdown_headers",
                "description": """
                    Finds all Markdown (.md) files in a directory, 
                    extracts specified occurrences of headers of a specific level from each file, 
                    and creates an index file mapping filenames to their titles.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "md_directory": {
                            "type": "string",
                            "description": "Path to the directory containing the .md files.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Path to the output file to save the processed content.",\
                        },
                        "header_level": {
                            "type": "string",
                            "enum": ["h1", "h2", "h3", "h4", "h5", "h6"],
                            "description": """ 
                                The level of the headers to extract: 'h1', 'h2', 'h3', 'h4', 'h5', or 'h6'.
                            """
                        },
                        "header_occurrence": {
                            "type": "string",
                            "enum": ["first", "nth", "last", "all"],
                            "description": """ 
                                Which occurrence of the header to extract: 'first', 'last', 'all', or 'nth'.
                            """
                        },
                        "n_value": {
                            "type": "string",
                            "description": """
                                (Optional) the n value if header occurence is nth.
                            """
                        }
                    },
                    "required": ["docs_directory", "header_level", "header_occurrence", "output_file"]
                }
            }
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
        elif function_name == "sort_contacts":
            sort_contacts(**arguments)
            return f"Contacts sorted and written to {arguments.get('output_file')}"
        elif function_name == "extract_log_info":
            extract_log_info(**arguments)
            return f"Log info extracted and written to {arguments.get('output_file')}"
        elif function_name == "extract_markdown_headers":
            extract_markdown_headers(**arguments)
            return f"Markdown processing completed. Result written to {arguments.get('output_file')}"
        else:
            raise ValueError(f"Unknown function name: {function_name}")
    except ValueError as e:
        raise ValueError(f"Error executing function: {e}")
    except Exception as e:
        raise Exception(f"Error executing function: {e}")
