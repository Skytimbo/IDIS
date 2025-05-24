#!/bin/bash
# Script to run all Docker tests for the IDIS system

set -e

echo "===== IDIS Docker Test Suite ====="
echo "This script will run a series of tests to verify the Docker environment for IDIS"
echo

# Build the Docker image if it doesn't exist
echo "Step 1: Building Docker image..."
docker compose build || { echo "Failed to build Docker image"; exit 1; }
echo "✓ Docker image built successfully"
echo

# Test basic Python functionality
echo "Step 2: Testing Python functionality..."
docker compose run --rm idis python -c "import sqlite3, sys; print('Python and SQLite3 working properly'); sys.exit(0)" || { echo "Failed Python test"; exit 1; }
echo "✓ Python functionality verified"
echo

# Run Docker environment test
echo "Step 3: Running Docker environment test..."
docker compose run --rm idis python docker_test.py --skip-openai || { echo "Failed Docker environment test"; exit 1; }
echo "✓ Docker environment test completed"
echo

# Run Docker-aware demo of Context Store
echo "Step 4: Running Context Store demo in Docker..."
docker compose run --rm -e IDIS_DB_PATH=/app/db/docker_test.db idis python docker_demo_context_store.py || { echo "Failed Context Store demo"; exit 1; }
echo "✓ Context Store demo completed"
echo

# Create a test document in the watch folder
echo "Step 5: Creating test document in watch folder..."
cat > ./watch_folder/test_invoice.txt << EOF
INVOICE #12345

Date: May 24, 2025

Bill to:
IDIS Docker Test
123 Test Street
Dockerville, DC 12345

Items:
1. IDIS Container Setup - $150.00
2. Docker Configuration - $100.00

Total Due: $250.00

This is an urgent invoice.
EOF
echo "✓ Test document created"
echo

# Run the Docker-optimized MVP pipeline
echo "Step 6: Running the Docker-optimized IDIS pipeline..."
docker compose run --rm idis python docker_run_mvp.py || { echo "Failed Docker MVP pipeline"; exit 1; }
echo "✓ Pipeline run successfully"
echo

echo "===== All tests completed successfully! ====="
echo "The IDIS system is properly configured for Docker."