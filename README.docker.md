# IDIS Docker Setup

## Overview
This Docker configuration allows you to run the Intelligent Document Insight System (IDIS) in a containerized environment with support for the Fujitsu fi-6130 scanner via USB pass-through.

## Prerequisites
- Docker and Docker Compose installed
- OpenAI API key for summarization functionality
- Fujitsu fi-6130 scanner connected via USB (optional)

## Directory Structure
Before running the container, ensure you have the following directory structure:
```
project_root/
├── watch_folder/     # Where documents are placed for processing
├── archive/          # Where processed documents are stored
└── database/         # Where the SQLite database is stored
```

## Getting Started

1. **Set up your OpenAI API key**:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   ```

2. **Build the Docker image**:
   ```bash
   docker compose build
   ```

3. **Run the IDIS system**:
   ```bash
   docker compose up
   ```

4. **Run in detached mode (background)**:
   ```bash
   docker compose up -d
   ```

## Configuration
The Docker container is configured with:
- A non-root user (UID 1001) for security
- Tesseract OCR for document text extraction
- WeasyPrint dependencies for PDF generation
- USB device pass-through for scanner integration

## Volumes
The Docker container mounts these volumes:
- `./watch_folder:/app/watch_folder` - Directory to monitor for new documents
- `./archive:/app/archive_folder` - Directory for archived processed documents
- `./database:/app/db` - Directory for the SQLite database

## Testing
To verify the container is working correctly:
```bash
docker compose run idis python -c "import sqlite3, sys; sys.exit(0)"
```

## Troubleshooting

### Scanner Not Detected
If the scanner isn't detected:
1. Ensure the scanner is powered on and connected
2. Check USB device permissions: `lsusb` to list USB devices
3. Verify the container has access to the USB device

### Database Issues
If database connectivity fails:
1. Check the database exists: `ls -la database/`
2. Verify permissions: `chmod 777 database/`

## Health Checks
The container performs regular health checks to ensure all components are functioning correctly. To manually run a health check:
```bash
docker compose run idis python healthcheck.py
```