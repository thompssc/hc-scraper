#!/usr/bin/env python3
"""
Simple test script to check the HappyCow AJAX endpoint
"""

import requests
import json

def test_endpoint():
    url = "https://www.happycow.net/ajax/views/city/venues/north_america/usa/texas/dallas"
    
    print(f"Testing URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Length: {len(response.text)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"JSON Response Keys: {list(data.keys())}")
                if 'data' in data:
                    print(f"Data Length: {len(data['data'])}")
                    print(f"First 200 chars: {data['data'][:200]}")
            except json.JSONDecodeError:
                print("Response is not JSON")
                print(f"First 200 chars: {response.text[:200]}")
        else:
            print(f"Error Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_endpoint() 