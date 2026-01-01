# Lightweight Python base
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Setup Python environment
ENV PIP_NO_CACHE_DIR=1
ENV TMPDIR=/app/tmp
RUN mkdir -p /app/tmp

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

RUN pip install --no-cache-dir torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir fastapi uvicorn[standard] requests chromadb sentence-transformers

# Copy app code and start.sh
COPY . .
RUN chmod +x start.sh

EXPOSE 9000 11434

# Use start.sh to start both Ollama and FastAPI
CMD ["./start.sh"]
