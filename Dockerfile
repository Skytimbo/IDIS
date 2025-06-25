# 1. Start with a lightweight, official Python base image
FROM python:3.11-slim

# 2. Set environment variables to prevent interactive prompts during installation
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# 3. Install necessary system dependencies, including Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 4. Set the working directory inside the container
WORKDIR /app

# 5. Copy and install Python dependencies first (for better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of the application source code into the container
COPY . .

# 7. Make shell scripts executable
RUN chmod +x ./start_watcher.sh ./run_ui.sh

# 8. Set the default command to run when the container starts.
# Note: The actual arguments will be overridden by docker-compose.
CMD ["python3", "watcher_service.py"]