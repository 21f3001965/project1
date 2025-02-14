# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "fastapi",
#     "uvicorn",
#     "httpx",
#     "python-dateutil"
# ]
# ///

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from agent import run_task
from utils import read_file

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
