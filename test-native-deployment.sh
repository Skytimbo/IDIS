#!/bin/bash

# Test script to verify native deployment on a different port
echo "Testing IDIS Native Deployment on port 5002..."
echo "============================================="

# Temporarily modify the deployment script to use port 5002
sed 's/--server.port 5000/--server.port 5002/g' deploy-native.sh > test-deploy.sh
chmod +x test-deploy.sh

# Run the test deployment
timeout 30 ./test-deploy.sh

# Clean up
rm test-deploy.sh

echo "Test completed!"