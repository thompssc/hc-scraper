#!/usr/bin/env python3
"""
HappyCow Simple AJAX Scraper
============================

Simplified version using requests library to call the AJAX endpoint directly.
Based on JavaScript analysis showing restaurant data loads via:
/ajax/views/city/venues/{path}{params}
"""

import requests
import json
import re
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup
import pandas as pd
import time

class SimpleHappyCowScraper:
    def __init__(self):
        self.base_url = "https://www.happycow.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        })
    
    def get_city_path_from_url(self, city_url):
        """Extract the city path from a HappyCow city URL."""
        print(f"🔍 Getting city path from: {city_url}")
        
        try:
            # First visit the city page to establish session
            response = self.session.get(city_url, timeout=30)
            response.raise_for_status()
            
            print(f"✅ City page loaded, status: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the last breadcrumb item which contains the path
            breadcrumb_items = soup.select('.breadcrumb li')
            if not breadcrumb_items:
                print("❌ No breadcrumb found on page")
                return None
                
            last_breadcrumb = breadcrumb_items[-1]
            path = last_breadcrumb.get('data-path')
            
            if not path:
                print("❌ No data-path found in last breadcrumb")
                # Try to extract from URL as fallback
                path = city_url.replace(self.base_url, '').strip('/')
                print(f"🔄 Using URL-based path: {path}")
            
            print(f"✅ Extracted city path: {path}")
            return path
            
        except Exception as e:
            print(f"❌ Error extracting city path: {e}")
            return None
    
    def get_ajax_data(self, city_path, page=1):
        """Get restaurant data from the AJAX endpoint."""
        try:
            # Convert path format: replace / with | and encode
            ajax_path = city_path.replace('/', '|')
            ajax_path = quote(ajax_path, safe='')
            
            # Build query parameters
            params = ""
            if page > 1:
                params = f"?page={page}"
            
            # Construct AJAX URL
            ajax_url = f"{self.base_url}/ajax/views/city/venues/{ajax_path}{params}"
            
            print(f"🔄 Calling AJAX endpoint: {ajax_url}")
            
            # Set referer to the original city page
            self.session.headers['Referer'] = f"{self.base_url}/{city_path.replace('|', '/')}/"
            
            response = self.session.get(ajax_url, timeout=30)
            
            print(f"📡 AJAX Response Status: {response.status_code}")
            print(f"📡 Response Headers: {dict(response.headers)}")
            print(f"📡 Response Length: {len(response.text)} characters")
            
            if response.status_code != 200:
                print(f"❌ AJAX request failed with status {response.status_code}")
                print(f"Response text: {response.text[:500]}...")
                return None
            
            # Parse JSON response
            try:
                data = response.json()
                print(f"✅ JSON parsed successfully")
                print(f"📊 JSON keys: {list(data.keys())}")
                
                if data.get('success'):
                    print(f"✅ AJAX request successful")
                    return data
                else:
                    print(f"❌ AJAX request returned success=false")
                    print(f"Response data: {data}")
                    return None
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"Response content: {response.text[:500]}...")
                return None
                
        except Exception as e:
            print(f"❌ Error in AJAX request: {e}")
            return None
    
    def parse_restaurant_html(self, html_content):
        """Parse restaurant data from the HTML content returned by AJAX."""
        soup = BeautifulSoup(html_content, 'html.parser')
        restaurants = []
        
        # Find all venue list items
        venue_items = soup.select('.venue-list-item.card-listing')
        print(f"🔍 Found {len(venue_items)} venue items in HTML")
        
        # Also try alternative selectors
        if not venue_items:
            venue_items = soup.select('.venue-list-item')
            print(f"🔍 Found {len(venue_items)} venue-list-item elements")
        
        if not venue_items:
            venue_items = soup.select('[data-id]')
            print(f"🔍 Found {len(venue_items)} elements with data-id")
        
        # Debug: print first few elements
        all_divs = soup.select('div')
        print(f"🔍 Total divs in HTML: {len(all_divs)}")
        
        for item in venue_items:
            try:
                restaurant = {}
                
                # Basic data from attributes
                restaurant['id'] = item.get('data-id')
                restaurant['type'] = item.get('data-type')
                restaurant['is_top'] = item.get('data-top') == '1'
                restaurant['is_new'] = item.get('data-new') == '1'
                restaurant['is_partner'] = item.get('data-partner') == '1'
                
                # Name
                name_el = item.select_one('[data-analytics="listing-card-title"]')
                if not name_el:
                    name_el = item.select_one('.venue-title, .listing-title, h3, h2')
                restaurant['name'] = name_el.get_text(strip=True) if name_el else None
                
                # URL
                link_el = item.select_one('a[href*="/reviews/"]')
                if not link_el:
                    link_el = item.select_one('a[href]')
                restaurant['url'] = link_el.get('href') if link_el else None
                
                # Address
                address_el = item.select_one('.venue-address')
                restaurant['address'] = address_el.get_text(strip=True) if address_el else None
                
                # Coordinates from Google Maps link
                maps_link = item.select_one('a[href*="google.com/maps"]')
                if maps_link:
                    href = maps_link.get('href')
                    if href and isinstance(href, str):
                        coord_match = re.search(r'q=([+-]?\d+\.?\d*),([+-]?\d+\.?\d*)', href)
                        if coord_match:
                            restaurant['latitude'] = float(coord_match.group(1))
                            restaurant['longitude'] = float(coord_match.group(2))
                
                # Only add if we have essential data
                if restaurant.get('name') and restaurant.get('id'):
                    restaurants.append(restaurant)
                    print(f"  ✅ Found: {restaurant['name']}")
                    
            except Exception as e:
                print(f"❌ Error parsing restaurant item: {e}")
                continue
        
        return restaurants
    
    def test_ajax_endpoint(self, city_url):
        """Test the AJAX endpoint step by step."""
        print(f"🧪 TESTING AJAX ENDPOINT")
        print(f"{'='*50}")
        
        # Step 1: Get city path
        city_path = self.get_city_path_from_url(city_url)
        if not city_path:
            print("❌ Failed to get city path")
            return
        
        # Step 2: Test AJAX call
        ajax_data = self.get_ajax_data(city_path, page=1)
        if not ajax_data:
            print("❌ Failed to get AJAX data")
            return
        
        # Step 3: Examine response structure
        print(f"\n📊 AJAX RESPONSE STRUCTURE:")
        print(f"{'='*30}")
        self.print_dict_structure(ajax_data, max_depth=3)
        
        # Step 4: Try to parse HTML if available
        html_content = ajax_data.get('data', {})
        if isinstance(html_content, dict):
            html_content = html_content.get('data', '')
        
        if html_content:
            print(f"\n🔍 HTML CONTENT ANALYSIS:")
            print(f"{'='*30}")
            print(f"HTML length: {len(html_content)} characters")
            print(f"First 500 chars: {html_content[:500]}...")
            
            restaurants = self.parse_restaurant_html(html_content)
            print(f"\n✅ FOUND {len(restaurants)} RESTAURANTS")
            
            for i, restaurant in enumerate(restaurants[:3]):
                print(f"\n{i+1}. {restaurant.get('name', 'Unknown')}")
                print(f"   ID: {restaurant.get('id')}")
                print(f"   Type: {restaurant.get('type')}")
                if restaurant.get('latitude'):
                    print(f"   Coordinates: {restaurant['latitude']}, {restaurant['longitude']}")
        else:
            print("❌ No HTML content found in response")
    
    def print_dict_structure(self, obj, indent=0, max_depth=2):
        """Helper to print dictionary structure."""
        if indent > max_depth:
            return
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                print("  " * indent + f"{key}: {type(value).__name__}")
                if isinstance(value, (dict, list)) and indent < max_depth:
                    self.print_dict_structure(value, indent + 1, max_depth)
        elif isinstance(obj, list) and obj:
            print("  " * indent + f"[{len(obj)} items, first item type: {type(obj[0]).__name__}]")
            if indent < max_depth:
                self.print_dict_structure(obj[0], indent + 1, max_depth)

def main():
    """Test the scraper."""
    scraper = SimpleHappyCowScraper()
    
    # Test with Dallas
    dallas_url = "https://www.happycow.net/north_america/usa/texas/dallas/"
    
    print(f"🥕 HAPPYCOW AJAX SCRAPER TEST")
    print(f"{'='*50}")
    
    scraper.test_ajax_endpoint(dallas_url)

if __name__ == "__main__":
    main() 