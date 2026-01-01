#!/bin/bash
# start.sh - robust version

# Start Ollama server
ollama serve &

# Wait until Ollama responds
echo "Waiting for Ollama to start..."
until curl -s http://localhost:11434 >/dev/null; do
    sleep 1
done
echo "Ollama is ready!"

# Pull the model
ollama pull gemma3:270m

# Start FastAPI
uvicorn app.api_rag:app --host 0.0.0.0 --port 9000
