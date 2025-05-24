#!/usr/bin/env python3
"""
Healthcheck script for IDIS Docker container

This script verifies that the IDIS system is running properly by checking:
1. Database connectivity
2. File system access to critical folders
3. Access to the OpenAI API (if API key is provided)
"""

import os
import sys
import sqlite3
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IDIS_Healthcheck")

def check_database_connection(db_path):
    """Verify database connection."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Check if our tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        tables = cursor.fetchall()
        conn.close()
        
        if not tables:
            logger.error(f"Database at {db_path} exists but doesn't contain required tables")
            return False
            
        logger.info(f"Successfully connected to database at {db_path}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Database connection failed: {e}")
        return False

def check_folder_access():
    """Verify access to critical folders."""
    required_folders = [
        "/app/watch_folder",
        "/app/holding_folder", 
        "/app/archive_folder",
        "/app/cover_sheets",
    ]
    
    all_accessible = True
    for folder in required_folders:
        folder_path = Path(folder)
        if not folder_path.exists():
            logger.error(f"Required folder {folder} does not exist")
            all_accessible = False
        elif not os.access(folder_path, os.R_OK | os.W_OK):
            logger.error(f"No read/write access to folder {folder}")
            all_accessible = False
        else:
            logger.info(f"Folder {folder} is accessible")
    
    return all_accessible

def check_openai_api():
    """Verify OpenAI API connectivity if API key is provided."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("No OpenAI API key provided, skipping API check")
        return True  # Skip check if no API key
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        # Make a simple API call to test connectivity
        response = client.models.list()
        logger.info("Successfully connected to OpenAI API")
        return True
    except Exception as e:
        logger.error(f"OpenAI API connection failed: {e}")
        return False

def main():
    """Run all health checks and exit with appropriate status code."""
    logger.info("Starting IDIS health check")
    
    # Determine the database path, defaulting to a standard location
    db_path = os.environ.get("IDIS_DB_PATH", "/app/db/idis.db")
    
    # Run checks
    db_ok = check_database_connection(db_path)
    folders_ok = check_folder_access()
    openai_ok = check_openai_api()
    
    # Evaluate overall health
    if db_ok and folders_ok and openai_ok:
        logger.info("Health check passed: All systems operational")
        return 0
    else:
        logger.error("Health check failed: One or more checks did not pass")
        return 1

if __name__ == "__main__":
    sys.exit(main())