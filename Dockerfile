# Use an official lightweight Python image
FROM python:3.11-slim

# Set environment variables for best practices in containers
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory
WORKDIR /app

# Install system-level dependencies required by Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first to leverage Docker's layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source code into the container
COPY . .

# Make shell scripts executable for entrypoint commands
RUN chmod +x ./start_watcher.sh ./run_ui.sh