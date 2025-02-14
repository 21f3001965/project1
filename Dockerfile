FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

RUN apt-get update && apt-get install -y nodejs npm

ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /app

COPY . /app

CMD ["uv", "run", "app.py"]