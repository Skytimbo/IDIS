#!/usr/bin/env python3
"""
Docker environment test script for IDIS

This script performs comprehensive tests of the IDIS system in a Docker environment.
It's intended to be run inside the container to verify proper configuration.
"""

import os
import sys
import time
import sqlite3
import shutil
import logging
import datetime
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IDIS_Docker_Test")

def test_file_paths():
    """
    Test that all required file paths exist and are accessible.
    """
    required_paths = [
        "/app/watch_folder",
        "/app/holding_folder",
        "/app/archive_folder",
        "/app/cover_sheets",
        "/app/db"
    ]
    
    passed = True
    for path in required_paths:
        dir_path = Path(path)
        if not dir_path.exists():
            logger.error(f"Path does not exist: {path}")
            passed = False
            continue
            
        # Test write access
        test_file = dir_path / f"test_file_{int(time.time())}.txt"
        try:
            with open(test_file, 'w') as f:
                f.write("Test file for Docker environment verification")
            test_file.unlink()  # Remove the test file
            logger.info(f"Successfully verified write access to {path}")
        except Exception as e:
            logger.error(f"Failed to write to {path}: {e}")
            passed = False
    
    return passed

def test_database():
    """
    Test database connectivity and permissions.
    """
    db_path = "/app/db/test_docker_idis.db"
    
    try:
        # Create test database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create a test table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS docker_test (
            id INTEGER PRIMARY KEY,
            test_name TEXT,
            timestamp TEXT
        )
        ''')
        
        # Insert a test record
        cursor.execute(
            "INSERT INTO docker_test (test_name, timestamp) VALUES (?, ?)",
            ("docker_environment_test", datetime.datetime.now().isoformat())
        )
        
        # Commit and verify
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM docker_test")
        count = cursor.fetchone()[0]
        
        # Close connection
        conn.close()
        
        if count > 0:
            logger.info(f"Successfully created and wrote to test database at {db_path}")
            
            # Clean up test database
            os.remove(db_path)
            logger.info(f"Removed test database {db_path}")
            return True
        else:
            logger.error("Database test failed: Could not verify written data")
            return False
    
    except sqlite3.Error as e:
        logger.error(f"Database test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in database test: {e}")
        return False

def test_openai_connectivity():
    """
    Test connectivity to OpenAI API if API key is provided.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        logger.warning("No OpenAI API key found in environment. Skipping OpenAI test.")
        return True  # Skip test rather than fail
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Make a simple API call
        response = client.models.list()
        model_count = len(response.data)
        
        logger.info(f"Successfully connected to OpenAI API. {model_count} models available.")
        return True
    
    except Exception as e:
        logger.error(f"OpenAI API test failed: {e}")
        return False

def test_create_sample_document():
    """
    Create a sample document in the watch folder.
    """
    watch_folder = "/app/watch_folder"
    test_doc_path = os.path.join(watch_folder, "docker_test_document.txt")
    
    try:
        with open(test_doc_path, 'w') as f:
            f.write("""
            SAMPLE INVOICE #12345
            
            Date: May 22, 2025
            
            Bill To:
            IDIS Docker Test
            123 Container Lane
            Docker City, DC 10001
            
            Description: Docker Environment Testing
            Amount: $99.99
            
            Thank you for your business!
            """)
        
        logger.info(f"Successfully created sample document at {test_doc_path}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to create sample document: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test IDIS Docker environment")
    parser.add_argument("--skip-openai", action="store_true", help="Skip OpenAI API test")
    args = parser.parse_args()
    
    logger.info("Starting IDIS Docker environment test")
    
    # Track test results
    results = {
        "file_paths": test_file_paths(),
        "database": test_database(),
        "sample_document": test_create_sample_document()
    }
    
    # Only run OpenAI test if not skipped
    if not args.skip_openai:
        results["openai"] = test_openai_connectivity()
    
    # Print summary
    logger.info("\n" + "="*50)
    logger.info("IDIS DOCKER TEST RESULTS")
    logger.info("="*50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        logger.info(f"{test_name.upper()}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("\nAll tests PASSED! Docker environment is properly configured.")
        return 0
    else:
        logger.error("\nSome tests FAILED. Please check the logs above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())