import requests
import time
import json
import uuid

API_URL = "http://localhost:8000/api"

def test_health():
    res = requests.get("http://localhost:8000/health")
    assert res.status_code == 200
    print("Health check passed.")

def test_custom_agent():
    payload = {
        "name": f"test_agent_{uuid.uuid4().hex[:6]}",
        "description": "A test agent",
        "system_prompt": "You are a test agent",
        "allowed_tools": ["scrape_website"]
    }
    res = requests.post(f"{API_URL}/agents", json=payload)
    assert res.status_code == 200, res.text
    agent = res.json()
    assert agent["name"] == payload["name"]
    print(f"Created custom agent: {agent['name']}")
    return agent

def test_prospects():
    res = requests.get(f"{API_URL}/prospects")
    assert res.status_code == 200, res.text
    print("List prospects passed.")

if __name__ == "__main__":
    try:
        test_health()
        test_custom_agent()
        test_prospects()
        print("All API tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
