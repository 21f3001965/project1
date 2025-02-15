import subprocess
import os
import logging
import datetime
from dateutil.parser import parse
from utils import (
    read_file,
    llm_text_extraction,
    extract_text_from_csv,
    extract_text_from_json,
    extract_text_from_word,
    extract_text_from_excel,
    llm_process_image,
    text_embedding_llm
)
import glob
import json
import re
import markdown2 # type: ignore
from bs4 import BeautifulSoup # type: ignore
import base64
import numpy as np

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
        raise ValueError(f"Error executing script: {e.stderr}")


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
            raise ValueError(
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
            subprocess.run(
                ["npm", "install", f"prettier@{prettier_version}"], check=True
            )

        # Format the file using Prettier
        subprocess.run(
            ["npx", f"prettier@{prettier_version}", "--write", file_path], check=True
        )

        return
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Error formatting file: {e}")


def validate_data_paths(*paths):
    cleaned_paths = []
    for path in paths:
        path = path.strip("/")
        if not path.startswith("data/"):
            raise ValueError("cannot write file outside of data directory")
        cleaned_paths.append(path)
    return cleaned_paths


def count_dates(input_file, output_file, date_part, value_to_count):
    logging.info(
        f"count dates called with input_file: {input_file}, output_file: {output_file}, date_part: {date_part}, value_to_count: {value_to_count}"
    )
    input_file, output_file = validate_data_paths(input_file, output_file)
    try:
        file_extension = os.path.splitext(input_file)[1][1:]
        if file_extension == "csv":
            dates = extract_text_from_csv(input_file)
        elif file_extension == "json":
            dates = extract_text_from_json(input_file)
        elif file_extension == "docx":
            dates = extract_text_from_word(input_file)
        elif file_extension == "xlsx" or file_extension == "xls":
            dates = extract_text_from_excel(input_file)
        else:
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
        raise ValueError(f"Error counting dates: {e}")


def sort_contacts(input_file, output_file, sort_fields, sort_direction):
    logging.info(
        f"sort contacts called with input_file: {input_file}, output_file: {output_file}, sort_fields: {sort_fields}, sort_direction: {sort_direction}"
    )
    input_file, output_file = validate_data_paths(input_file, output_file)

    if len(sort_fields) != len(sort_direction):
        raise ValueError("sort_fields and sort_direction must have the same length")

    try:
        with open(input_file, "r") as f:
            contacts = json.load(f)

        if not isinstance(contacts, list):
            raise ValueError("Input file is not a valid JSON array")

        sort_criteria = []
        for field, direction in zip(sort_fields, sort_direction):
            reverse = direction.lower() == "desc"
            sort_criteria.append((field, reverse))

        def mutlti_sort(contact):
            return tuple(contact.get(field) for field, _ in sort_criteria)

        contacts.sort(key=mutlti_sort, reverse=False)

        for i, (field, reverse) in enumerate(sort_criteria):
            if reverse:
                contacts = sorted(
                    contacts, key=lambda k: k.get(field, None), reverse=True
                )

        with open(output_file, "w") as f:
            json.dump(contacts, f)

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {input_file}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in input file: {input_file}")
    except Exception as e:
        raise ValueError(f"Error sorting contacts: {e}")


def extract_log_info(
    log_directory,
    sort_order,
    output_file,
    extraction_type,
    date_filter_type="none",
    date_filter_value=None,
    num_files=None,
    line_number=None,
    lines_range_start=None,
    lines_range_end=None,
    regex_pattern=None,
):
    logging.info(
        f"extract log info called with log_directory: {log_directory}, output_file: {output_file}, extraction_type: {extraction_type}, num_files: {num_files}, line_number: {line_number}"
    )
    log_directory, output_file = validate_data_paths(log_directory, output_file)

    try:
        files = glob.glob(os.path.join(log_directory, "**", "*.log"), recursive=True)

        # Date Filtering
        if date_filter_type != "none":
            if date_filter_value is None:
                raise ValueError(
                    "A date_filter_value must be provided when using a date filter."
                )

            def filter_by_date(file_path):
                mod_time = datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                ).date()
                try:
                    if date_filter_type == "on":
                        filter_date = parse(date_filter_value).date()
                        return mod_time == filter_date
                    elif date_filter_type == "before":
                        filter_date = parse(date_filter_value).date()
                        return mod_time < filter_date
                    elif date_filter_type == "after":
                        filter_date = parse(date_filter_value).date()
                        return mod_time > filter_date
                    elif date_filter_type == "between":
                        start_date_str, end_date_str = date_filter_value.split(",")
                        start_date = parse(start_date_str).date()
                        end_date = parse(end_date_str).date()
                        return start_date <= mod_time <= end_date
                    else:
                        return True
                except Exception as e:
                    return False

            files = [f for f in files if filter_by_date(f)]

        # Sort the files
        if sort_order == "newest":
            files.sort(key=os.path.getmtime, reverse=True)
        elif sort_order == "oldest":
            files.sort(key=os.path.getmtime, reverse=False)
        elif sort_order == "name_asc":
            files.sort()
        elif sort_order == "name_desc":
            files.sort(reverse=True)
        elif sort_order == "size_asc":
            files.sort(key=os.path.getsize)
        elif sort_order == "size_desc":
            files.sort(key=os.path.getsize, reverse=True)
        elif sort_order == "none":
            pass  # Do not sort the files
        else:
            raise ValueError(f"Invalid sort order: {sort_order}")

        # Limit number of files
        if num_files is not None:
            try:
                num_files = int(num_files)
                files = files[:num_files]
            except ValueError:
                logging.info(f"Invalid num_files value: {num_files}, using all files")

        output_lines = []
        for file_path in files:
            try:
                with open(file_path, "r") as f:
                    lines = f.readlines()

                if extraction_type == "first":
                    extracted_line = lines[0].strip() if lines else ""
                elif extraction_type == "last":
                    extracted_line = lines[-1].strip() if lines else ""
                elif extraction_type == "all":
                    extracted_line = (
                        "".join(line.strip() for line in lines) if lines else ""
                    )
                elif extraction_type == "line_number":
                    if line_number is None:
                        raise ValueError(
                            "Line number is required for extraction_type 'line_number'"
                        )
                    try:
                        line_number = int(line_number) - 1  # 0-based index
                        extracted_line = (
                            lines[line_number].strip()
                            if 0 <= line_number < len(lines)
                            else ""
                        )
                    except (ValueError, IndexError):
                        raise ValueError(f"Invalid line number: {line_number}")
                elif extraction_type == "lines_range":
                    if lines_range_start is None or lines_range_end is None:
                        raise ValueError(
                            "Lines range start and end are required for extraction_type 'lines_range'"
                        )
                    try:
                        start_line = int(lines_range_start) - 1  # 0-based
                        end_line = int(lines_range_end)  # inclusive
                        extracted_line = "".join(
                            [
                                line.strip()
                                for i, line in enumerate(lines)
                                if start_line <= i < end_line
                            ]
                        )

                    except (ValueError, IndexError):
                        raise ValueError(
                            f"Invalid lines range: {lines_range_start}-{lines_range_end}"
                        )
                elif extraction_type == "regex":
                    if regex_pattern is None:
                        raise ValueError(
                            "Regex pattern is required for extraction_type 'regex'"
                        )
                    try:
                        extracted_line = "\n".join(
                            line.strip()
                            for line in lines
                            if re.search(regex_pattern, line)
                        )
                    except re.error as e:
                        raise ValueError(f"Invalid regex pattern: {e}")
                    except Exception as e:
                        raise ValueError(f"Error extracting with regex: {e}")
                else:
                    raise ValueError(f"Invalid extraction type: {extraction_type}")
                output_lines.append(extracted_line)
            except Exception as e:
                output_lines.append(f"Error reading {os.path.basename(file_path)}: {e}")

        with open(output_file, "w") as outfile:
            for line in output_lines:
                outfile.write(line + "\n")

        print(f"Extracted information from {len(files)} files to {output_file}")

    except FileNotFoundError:
        raise FileNotFoundError(f"Directory not found: {log_directory}")
    except Exception as e:
        raise ValueError(f"Error extracting log info: {e}")


def extract_markdown_headers(
    md_directory, header_level, header_occurrence, output_file, n_value=None
):
    logging.info(
        f"extract_markdown_headers called with md_directory: {md_directory}, header_level: {header_level}, header_occurrence: {header_occurrence}, output_file: {output_file}, n_value: {n_value}"
    )
    md_directory, output_file = validate_data_paths(md_directory, output_file)

    try:
        index_data = {}
        files = glob.glob(os.path.join(md_directory, "**", "*.md"), recursive=True)

        for file in files:
            with open(file, "r") as f:
                md_content = f.read()

            html = markdown2.markdown(md_content)
            soup = BeautifulSoup(html, "html.parser")

            headers = soup.find_all(f"{header_level}")

            if header_occurrence == "first":
                title = headers[0].get_text().strip() if headers else ""
            elif header_occurrence == "last":
                title = headers[-1].get_text().strip() if headers else ""
            elif header_occurrence == "n":
                if n_value is not None:
                    raise ValueError("N value must be given if header_occurance is nth")
                title = (
                    headers[n_value].get_text().strip()
                    if len(headers) >= n_value
                    else ""
                )
            elif header_occurrence == "all":
                title = (
                    " | ".join(header.get_text().strip() for header in headers)
                    if headers
                    else ""
                )
            else:
                raise ValueError(f"Invalid header_occurrence: {header_occurrence}")

            filename = os.path.relpath(file, md_directory)
            index_data[filename] = title
        with open(output_file, "w") as outfile:
            json.dump(index_data, outfile, indent=4)

    except Exception as e:
        raise ValueError(f"Error extracting markdown headers: {e}")


def extract_information(input_file, output_file, extraction_instruction):
    logging.info(
        f"extract information called with input_file: {input_file}, output_file: {output_file}, extraction_instruction: {extraction_instruction}"
    )
    input_file, output_file = validate_data_paths(input_file, output_file)

    try:

        file_extension = os.path.splitext(input_file)[1][1:]
        if file_extension == "csv":
            content = extract_text_from_csv(
                input_file, output_file, extraction_instruction
            )
        elif file_extension == "json":
            content = extract_text_from_json(
                input_file, output_file, extraction_instruction
            )
        elif file_extension == "docx":
            content = extract_text_from_word(
                input_file, output_file, extraction_instruction
            )
        else:
            with open(input_file, "r") as f:
                content = f.read()

        try:
            llm_response = llm_text_extraction(extraction_instruction, content)
            extract_data = json.loads(
                llm_response["choices"][0]["message"]["tool_calls"][0]["function"][
                    "arguments"
                ]
            )["extracted_information"]
            for i, data in enumerate(extract_data):
                with open(output_file, "a") as f:
                    f.write(" ".join(extract_data))
        except Exception as e:
            raise Exception(f"Error calling llm: {e}")
    except Exception as e:
        raise ValueError(f"Error extracting information: {e}")


def process_image(image_path, output_file, processing_instruction):
    logging.info(
        f"process image called with image_path: {image_path}, output_file: {output_file}, processing_instruction: {processing_instruction}"
    )
    image_path, output_file = validate_data_paths(image_path, output_file)

    
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

        general_instruction = f"Extract all readable text and numbers from this image.Provide the extracted content in a structured format."
 
        try:
            image_extension = os.path.splitext(image_path)[1][1:]
            image_llm_response = llm_process_image(
                encoded_string, image_extension, general_instruction
            )
            logging.info(image_llm_response)
            extracted_data = image_llm_response['choices'][0]['message']['content']
            
            text_llm_response = llm_text_extraction(processing_instruction, extracted_data)
            
            extract_data = json.loads(
                text_llm_response["choices"][0]["message"]["tool_calls"][0]["function"][
                    "arguments"
                ]
            )["extracted_information"]
            for i, data in enumerate(extract_data):
                with open(output_file, "a") as f:
                    f.write(" ".join(extract_data))
        except Exception as e:
            raise Exception(f"Error calling llm: {e}")
    except Exception as e:
        raise ValueError(f"Error processing image: {e}")

def find_texts_with_embeddings(input_file, output_file, find_type, input_format, output_format):
    logging.info(
     f"analyze text called with input_file: {input_file}, output_file: {output_file}, find_type: {find_type}, input_format: {input_format}, output_format: {output_format}"   
    )
    
    input_file, output_file = validate_data_paths(input_file, output_file)
    
    try:  
        if input_format == "csv":
            texts = extract_text_from_csv(input_file)
        elif input_format == "space_separated":
            with open(input_file, "r") as f:
                texts = f.read().split()
        else:
            with open(input_file, "r") as f:
                texts = [line.strip() for line in f.readlines()]
        
        if len(texts) < 2:
            raise ValueError("Need at least two texts in the input file.")
        
        
        llm_response = text_embedding_llm(texts)
        embeddings = np.array([np.array(embedding["embedding"]) for embedding in llm_response["data"]])
        
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True) 
        normalized_embeddings = embeddings / norms
        similarity_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)
        
        np.fill_diagonal(similarity_matrix, -np.inf) # Ignore self-similarity
        
        if find_type == "most_similar":
               index = np.unravel_index(np.argmax(similarity_matrix), similarity_matrix.shape)
        elif find_type == "most_dissimilar":
            index = np.unravel_index(np.argmin(similarity_matrix), similarity_matrix.shape)
        else:
            raise ValueError("Invalid find_type. Use 'most_similar' or 'most_dissimilar'.")
        
        pairs = (texts[index[0]], texts[index[1]])
        
        if output_format == "comma_separated":
            output_string = pairs[0] + "," + pairs[1]
        elif output_format == "one_per_line":
            output_string = pairs[0] + "\n" + pairs[1]
        elif output_format == "space_separated":
            output_string = pairs[0] + " " + pairs[1]
        else:
            raise ValueError("Invalid output_format. Use 'comma_separated', 'one_per_line', or 'space_separated'.")
        
        with open(output_file, "w") as f:
            f.write(output_string)
        
    except Exception as e:
        raise ValueError(f"Error analyzing text: {e}")