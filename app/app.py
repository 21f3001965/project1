# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "fastapi",
#     "uvicorn",
#     "httpx",
#     "python-dateutil",
#     "pandas",
#     "python-docx",
#     "markdown2",
#     "beautifulsoup4",
#     "numpy",
#     "duckdb",
#     "pillow",
#     "vosk",
#     "soundfile"
# ]
# ///

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from agent import run_task
from utils import read_file
from helper import filter_csv_to_json_api


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os

# Ensure 'data' directory exists
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

@app.post("/run")
def run(task: str):
    if not task:
        return Response(content="Task is required", status_code=400)

    try:
        result = run_task(task)  # calling the llm api
        return Response(content=result, status_code=200)
    except ValueError as e:
        return Response(content=str(e), status_code=400)
    except FileNotFoundError as e:
        return Response(content=str(e), status_code=400)
    except Exception as e:
        return Response(content=str(e), status_code=500)


@app.get("/read")
def read(path: str):
    if not path:
        return Response(content="File path is required", status_code=400)

    try:
        content = read_file(path)
        headers = {"Content-Type": "text/plain"}
        return Response(content=content, status_code=200, headers=headers)
    except FileNotFoundError:
        return Response(content="File not found", status_code=404)
    except ValueError as e:
        return Response(content=str(e), status_code=400)


@app.get("/filter_csv")
def filter_csv(csv_path: str, filter_column: str, filter_value: str):
    if not csv_path or not filter_column or not filter_value:
        return Response(
            content="CSV path, filter column, and filter value are required",
            status_code=400,
        )

    try:
        output_file = filter_csv_to_json_api(
            csv_path, filter_column, filter_value, "api_endpoint"
        )
        return Response(content=output_file, status_code=200)
    except ValueError as e:
        return Response(content=str(e), status_code=400)

@app.post("/create_endpoint/")
async def create_endpoint(api_endpoint: str, csv_path: str, filter_column: str, filter_value: str):
    existing_routes = {route.path for route in app.routes}
    if f"/{api_endpoint}" in existing_routes:
        return Response(content=f"Endpoint '{api_endpoint}' already exists.", status_code=400)

    return filter_csv_to_json_api(app, csv_path, filter_column, filter_value, api_endpoint)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
