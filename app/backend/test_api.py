#!/usr/bin/env python3
"""Quick test script for the API"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_chat():
    """Test chat endpoint"""
    print("\n=== Testing Chat Endpoint ===")
    payload = {
        "message": "Hello, what is Kubernetes?",
        "conversation_id": None
    }
    
    response = requests.post(
        f"{BASE_URL}/api/chat/message",
        headers={"Content-Type": "application/json"},
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    print("Testing K8s MCP Backend API")
    
    try:
        test_health()
    except Exception as e:
        print(f"Health test failed: {e}")
    
    try:
        test_chat()
    except Exception as e:
        print(f"Chat test failed: {e}")
