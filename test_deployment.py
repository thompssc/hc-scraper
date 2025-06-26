#!/usr/bin/env python3
"""
Simple deployment test script
Run this to verify your Railway deployment is working
"""

import requests
import sys
import json

def test_deployment(base_url):
    """Test the deployed scraper service"""
    print(f"Testing deployment at: {base_url}")
    
    # Test 1: Health check
    try:
        print("\n1. Testing health endpoint...")
        response = requests.get(f"{base_url}/health", timeout=10)
        response.raise_for_status()
        print("✅ Health check passed!")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test 2: Test endpoint
    try:
        print("\n2. Testing test endpoint...")
        response = requests.get(f"{base_url}/test", timeout=30)
        response.raise_for_status()
        result = response.json()
        print("✅ Test endpoint passed!")
        print(f"Found {result.get('total_restaurants', 0)} restaurants")
    except Exception as e:
        print(f"❌ Test endpoint failed: {e}")
        return False
    
    # Test 3: Custom scrape request
    try:
        print("\n3. Testing custom scrape...")
        test_data = {
            "url": "https://www.happycow.net/north_america/usa/texas/dallas/",
            "full_path": "north_america/usa/texas/dallas",
            "city": "Dallas",
            "state": "Texas"
        }
        
        response = requests.post(
            f"{base_url}/scrape",
            json=test_data,
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        print("✅ Custom scrape passed!")
        print(f"Success: {result.get('success', False)}")
        print(f"Restaurants found: {result.get('total_restaurants', 0)}")
    except Exception as e:
        print(f"❌ Custom scrape failed: {e}")
        return False
    
    print("\n🎉 All tests passed! Your deployment is working correctly.")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_deployment.py <railway_url>")
        print("Example: python test_deployment.py https://your-app.up.railway.app")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    success = test_deployment(base_url)
    sys.exit(0 if success else 1) 