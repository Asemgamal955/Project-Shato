FROM python:3.11-slim-bookworm

WORKDIR /app


RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80retries \
 && echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4

# System deps (ffmpeg is required by Whisper)
RUN apt-get update && apt-get install -y \
    ffmpeg git curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# The STT FastAPI app uses port 8003
EXPOSE 8003

# Start the server
CMD ["python", "main.py","--host", "0.0.0.0"]
