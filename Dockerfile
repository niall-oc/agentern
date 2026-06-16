FROM python:3.12-slim 

WORKDIR /app

# Install build dependencies for C++ compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the contents of the app folder directly into /app
COPY app/ .

# Run the application directly from the root workspace
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]