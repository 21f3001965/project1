from utils import call_llm_with_functions, read_file
import json

from helper import (
    online_script_runner,
    write_file,
    format_file_with_prettier,
    count_dates,
    sort_contacts,
    extract_log_info,
    extract_markdown_headers,
    extract_information,
    process_image,
    find_texts_with_embeddings,
    query_database,
    reject_task,
    fetch_and_save_data,
    clone_git_repo,
    scrape_website,
    compress_image,
    resize_image,
    transcribe_audio,
    convert_markdown_to_html,
    filter_csv_to_json_api,
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
                    "required": ["url", "email", "package"],
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
                            "description": "Path to the output file to save the processed content.",
                        },
                        "header_level": {
                            "type": "string",
                            "enum": ["h1", "h2", "h3", "h4", "h5", "h6"],
                            "description": """ 
                                The level of the headers to extract: 'h1', 'h2', 'h3', 'h4', 'h5', or 'h6'.
                            """,
                        },
                        "header_occurrence": {
                            "type": "string",
                            "enum": ["first", "nth", "last", "all"],
                            "description": """ 
                                Which occurrence of the header to extract: 'first', 'last', 'all', or 'nth'.
                            """,
                        },
                        "n_value": {
                            "type": "string",
                            "description": """
                                (Optional) the n value if header occurence is nth.
                            """,
                        },
                    },
                    "required": [
                        "md_directory",
                        "header_level",
                        "header_occurrence",
                        "output_file",
                    ],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "extract_information",
                "description": """
                    use this function if the task requires to extract information from a file with provided instructions
                    (e.g extract some information from file containg email message)                                        
                    and write the extracted information to an output file.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_file": {
                            "type": "string",
                            "description": "Path to the file from which to extract information.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Path to the file to write the extracted information.",
                        },
                        "extraction_instruction": {
                            "type": "string",
                            "description": "A plain-English instruction on what to extract from the file (e.g., 'the sender's email address', 'the customer ID', 'the product name').",
                        },
                    },
                    "required": ["input_file", "output_file", "extraction_instruction"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "process_image",
                "description": """
                    use this function if the task requires to process and image
                    based on a plain english instruction,
                    write the result to an output file.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the image file to process.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Path to the file where the processing result will be written..",
                        },
                        "processing_instruction": {
                            "type": "string",
                            "description": "A plain-English instruction on what to do with the image (e.g., 'extract credit card number', 'describe the image', 'identify objects in the image').",
                        },
                    },
                    "required": ["image_path", "output_file", "processing_instruction"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "find_texts_with_embeddings",
                "description": """
                   Finds similar or dissimilar texts in a file using text embeddings generated by the LLM. 
                   Writes the pair of texts to an output file.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_file": {
                            "type": "string",
                            "description": "Path to the file containing the texts, one text per line.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Path to the file where the pair of texts will be written, one text per line.",
                        },
                        "find_type": {
                            "type": "string",
                            "enum": ["most_similar", "most_dissimilar"],
                            "description": "Whether to find 'similar' or 'dissimilar' texts.",
                        },
                        "input_format": {
                            "type": "string",
                            "enum": ["one_per_line", "csv", "space_separated"],
                            "description": "Format of the text input: 'one_per_line', 'csv', or 'space_separated'.",
                        },
                        "output_format": {
                            "type": "string",
                            "enum": [
                                "one_per_line",
                                "space_separated",
                                "comma_separated",
                            ],
                            "description": "Format of the text output: 'one_per_line', 'space_separated', or 'comma_separated'.",
                        },
                    },
                    "required": [
                        "input_file",
                        "output_file",
                        "find_type",
                        "input_format",
                        "output_format",
                    ],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_database",
                "description": """
                    Executes a SQL query on a SQLite or DuckDB database and writes the result to an output file.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "db_path": {
                            "type": "string",
                            "description": "Path to the SQLite database file.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Path to the file where the query result will be written.",
                        },
                        "query": {
                            "type": "string",
                            "description": "The SQL query to execute.",
                        },
                        "is_deleting": {
                            "type": "boolean",
                            "description": "Whether the query is deleting/removing or not.",
                        },
                        "output_type": {
                            "type": "string",
                            "enum": ["single_value", "json", "csv", "text"],
                            "description": "The desired output format: 'single_value' for a single number, 'json' for JSON, 'csv' for CSV, and 'text' for plain text.",
                        },
                    },
                    "required": [
                        "db_path",
                        "output_file",
                        "query",
                        "is_deleting",
                        "output_type",
                    ],
                },
            },
        },
        # B-tasks
        {
            "type": "function",
            "function": {
                "name": "reject_task",
                "description": "Rejects the task if it violates the security policy (e.g., deleting files or writing to an existing file).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "The reason for rejecting the task. This should clearly state that deleting or removing data is not allowed..",
                        },
                    },
                    "required": ["reason"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_and_save_data",
                "description": "Fetches data from an API and saves it to a file within the /data directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "api_url": {
                            "type": "string",
                            "description": "The URL of the API endpoint to fetch data from.",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Path where the fetched data will be saved. if not said then the file will be saved in /data directory.",
                        },
                        "filename": {
                            "type": "string",
                            "description": "(Optional) The name of the file where the fetched data will be saved.",
                        },
                    },
                    "required": ["api_url", "output_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "clone_git_repo",
                "description": "Clone a git repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_url": {
                            "type": "string",
                            "description": "The URL of the git repository to clone.",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Path where the cloned repository will be saved. if not said then the file will be saved in /data directory.",
                        },
                    },
                    "required": ["repo_url", "output_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "scrape_website",
                "description": "Extract specific data from a website based on user-defined criteria.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL of the website to scrape."
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Path where the extracted data will be saved. If not specified, the file will be saved in the /data directory."
                        },
                        "filename": {
                            "type": "string",
                            "description": "(Optional) The name of the file where the extracted data will be saved."
                        },
                        "scrape_target": {
                            "type": "array",
                            "description": "List of elements to scrape from the webpage.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "element": {
                                        "type": "string",
                                        "description": "The HTML tag, CSS selector, or XPath of the element to scrape."
                                    },
                                    "attribute": {
                                        "type": "string",
                                        "description": "(Optional) If specified, extracts the attribute (e.g., 'href', 'src') instead of text content."
                                    }
                                },
                                "required": ["element"]
                            }
                        }
                    },
                    "required": ["url", "output_path", "scrape_target"]
                }
            }
        },

        {
            "type": "function",
            "function": {
                "name": "compress_image",
                "description": "Compress an image.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "The path of the image to compress.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Path where the compressed image will be saved. if not described in task then the file will be saved in /data with same name as input + 'compressed' directory.",
                        },
                        "quality": {
                            "type": "integer",
                            "description": "The quality of the compressed image (0-100).",
                            "minimum": 0,
                            "maximum": 100,
                        },
                    },
                    "required": ["image_path", "output_file", "quality"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "resize_image",
                "description": "Resizes an image.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "The path to the image file.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "The path to write the resized image to. if not described in task then the file will be saved in /data with same name as input + 'resized' directory.",
                        },
                        "width": {
                            "type": "integer",
                            "description": "The width of the resized image.",
                            "minimum": 1,
                        },
                        "height": {
                            "type": "integer",
                            "description": "The height of the resized image.",
                            "minimum": 1,
                        },
                    },
                    "required": ["image_path", "output_file", "width", "height"],
                },

            },
        },
        {
            "type": "function",
            "function": {
                "name": "transcribe_audio",
                "description": "Transcribes an audio file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "audio_path": {
                            "type": "string",
                            "description": "The path to the audio file.",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "The path to write the transcription to.",
                        },
                    },
                    "required": ["audio_path", "output_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "convert_markdown_to_html",
                "description": "Convert Markdown to HTML.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "markdown_path": {
                            "type": "string",
                            "description": "The path to the Markdown file.",
                        },
                        "output_file": {
                            "type": "string",
                            "description": "The path to write the HTML file to.",
                        },
                    },
                    "required": ["markdown_path", "output_file"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "filter_csv_to_json_api",
                "description": "Write an API endpoint that filters a CSV file and returns JSON data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "csv_path": {
                            "type": "string",
                            "description": "The path to the CSV file.",
                        },
                        "filter_column": {
                            "type": "string",
                            "description": "The column to filter by.",
                        },
                        "filter_value": {
                            "type": "string",
                            "description": "The value to filter for.",
                        },
                        "api_endpoint": {
                            "type": "string",
                            "description": "The API endpoint where the data will be served.",
                        },
                    },
                    "required": [
                        "csv_path",
                        "filter_column",
                        "filter_value",
                        "api_endpoint",
                    ],
                },
            },
        },
    ]

    llm_response = call_llm_with_functions(task, tools)

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
        elif function_name == "extract_information":
            extract_information(**arguments)
            return (
                f"Information extracted and written to {arguments.get('output_file')}"
            )
        elif function_name == "process_image":
            process_image(**arguments)
            return f"Image processing completed. Result written to {arguments.get('output_file')}"
        elif function_name == "find_texts_with_embeddings":
            find_texts_with_embeddings(**arguments)
            return f"Text analysis completed. Result written to {arguments.get('output_file')}"
        elif function_name == "query_database":
            query_database(**arguments)
            return f"Database query completed. Result written to {arguments.get('output_file')}"
        elif function_name == "reject_task":
            return reject_task(**arguments)
        elif function_name == "fetch_and_save_data":
            file_path = fetch_and_save_data(**arguments)
            return f"Data fetched and saved to {file_path}"
        elif function_name == "clone_git_repo":
            clone_git_repo(**arguments)
            return f"Git repository cloned and saved to {arguments.get('output_path')}"
        elif function_name == "scrape_website":
            scrape_website(**arguments)
            return f"Data extracted from website and saved to {arguments.get('output_path')}"
        elif function_name == "compress_image":
            compress_image(**arguments)
            return f"Image compressed and saved to {arguments.get('output_path')}"
        elif function_name == "resize_image":
            resize_image(**arguments)
            return f"Image resized and saved to {arguments.get('output_file')}"
        elif function_name == "transcribe_audio":
            transcribe_audio(**arguments)
            return f"Audio transcription completed. Result written to {arguments.get('output_path')}"
        elif function_name == "convert_markdown_to_html":
            convert_markdown_to_html(**arguments)
            return f"Markdown converted to HTML and saved to {arguments.get('output_file')}"
        elif function_name == "filter_csv_to_json_api":
            filter_csv_to_json_api(**arguments)
            return (
                f"CSV filtered and JSON data served at {arguments.get('api_endpoint')}"
            )
        else:
            raise ValueError(f"Unknown function name: {function_name}")
    except ValueError as e:
        raise ValueError(f"Error executing function: {e}")
    except Exception as e:
        raise Exception(f"Error executing function: {e}")
