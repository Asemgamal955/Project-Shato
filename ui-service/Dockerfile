FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install only required system libs (skip ffmpeg unless needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

    
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose Gradio port
EXPOSE 7860

# Start Gradio app
CMD ["python", "ui.py"]
