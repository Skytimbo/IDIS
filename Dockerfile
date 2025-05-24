FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    # Additional packages for handling USB devices and file operations
    usbutils \
    libusb-1.0-0 \
    libsane \
    libsane-common \
    sane-utils \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -u 1001 -m scanner

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p /app/watch_folder /app/holding_folder /app/archive_folder /app/cover_sheets /app/db \
    && chown -R scanner:scanner /app

# Switch to non-root user
USER scanner

# Define healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD ["python", "healthcheck.py"]

# Define entrypoint
ENTRYPOINT ["python", "run_mvp.py"]