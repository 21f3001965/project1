# Use a slim Python image
FROM python:3.12-slim-bookworm

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install UV (Python package manager)
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

RUN apt-get update && apt-get install -y nodejs npm
# Set environment variable for UV
ENV PATH="/root/.local/bin/:$PATH"

# Set working directory
WORKDIR /app

# Copy only the contents of the "app" folder into /app (without the "app/" itself)
COPY app/ . 

# Run the application (uv will handle package installation)
CMD ["uv", "run", "app.py"]
