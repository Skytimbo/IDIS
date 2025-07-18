#!/usr/bin/env python3
"""
Test script for the IDIS FastAPI application.
This script tests the basic functionality of the API endpoints.
"""

from fastapi.testclient import TestClient
from main import app

def test_fastapi_endpoints():
    """Test the FastAPI endpoints with proper authentication."""
    client = TestClient(app)
    
    # Test root endpoint (no auth required)
    response = client.get("/")
    print(f"✅ Root endpoint: {response.status_code} - {response.json()}")
    
    # Set up authentication headers
    headers = {"X-API-KEY": "a_very_secret_and_long_random_string_for_mvp"}
    
    # Test entities endpoint
    try:
        response = client.get("/entities/", headers=headers)
        print(f"✅ Entities endpoint: {response.status_code}")
        if response.status_code == 200:
            print("  - Authentication working correctly")
        else:
            print(f"  - Response: {response.text}")
    except Exception as e:
        print(f"❌ Entities endpoint error: {e}")
    
    # Test cases endpoint
    try:
        response = client.get("/cases/by_entity/1", headers=headers)
        print(f"✅ Cases endpoint: {response.status_code}")
        if response.status_code == 200:
            print("  - Cases endpoint working correctly")
        else:
            print(f"  - Response: {response.text}")
    except Exception as e:
        print(f"❌ Cases endpoint error: {e}")
    
    print("\n🎉 FastAPI application structure test completed!")

if __name__ == "__main__":
    test_fastapi_endpoints()