#!/bin/bash

# IDIS Production Deployment Script
# This script launches the IDIS application using Docker Compose

echo "Starting IDIS Production Deployment..."
echo "=================================="

# Check if Docker and Docker Compose are available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed or not in PATH"
    exit 1
fi

# Check if required environment variables are set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY environment variable is not set"
    echo "The application will not be able to use AI-powered features"
fi

# Create necessary directories
echo "Creating required directories..."
mkdir -p data/scanner_output
mkdir -p data/inbox
mkdir -p data/holding
mkdir -p data/archive
mkdir -p data/coversheets

# Ensure the production database file exists
if [ ! -f "production_idis.db" ]; then
    echo "Warning: production_idis.db not found. Creating empty database..."
    touch production_idis.db
fi

# Start the application using Docker Compose
echo "Starting IDIS services..."
docker-compose up --build -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ IDIS deployment successful!"
    echo ""
    echo "Services running:"
    docker-compose ps
    echo ""
    echo "Access the application at: http://localhost:8501"
    echo "To stop the application, run: docker-compose down"
else
    echo "❌ Deployment failed. Check the logs:"
    docker-compose logs
    exit 1
fi