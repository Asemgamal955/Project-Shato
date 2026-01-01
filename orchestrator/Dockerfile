# orchestrator/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy orchestrator app code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start the orchestrator
CMD ["uvicorn", "orchestrator:app", "--host", "0.0.0.0", "--port", "8000"]
