#!/usr/bin/env python3
"""
HappyCow Cloud Scraper Service
Flask HTTP API that n8n cloud can call to scrape cities
Deploy this to Render, Railway, or similar service
"""

from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import time
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class HappyCowScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def extract_city_path(self, city_url):
        """Extract city path from HappyCow URL"""
        try:
            response = self.session.get(city_url, timeout=10)
            response.raise_for_status()
            
            # Look for the path in the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Method 1: Look for data attributes or JavaScript variables
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'path' in script.string.lower():
                    content = script.string
                    # Look for path patterns
                    path_match = re.search(r'["\']([^"\']*north_america[^"\']*)["\']', content)
                    if path_match:
                        path = path_match.group(1)
                        if '/' in path:
                            return path.replace('/', '|')
            
            # Method 2: Extract from URL structure
            url_parts = city_url.replace('https://www.happycow.net/', '').strip('/')
            if url_parts:
                return url_parts.replace('/', '|')
            
            logger.warning(f"Could not extract path from {city_url}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting city path: {e}")
            return None
    
    def scrape_city_ajax(self, city_url):
        """Scrape city using AJAX endpoint"""
        try:
            # Extract path from actual HappyCow URL
            # https://www.happycow.net/north_america/usa/california/los_angeles/ -> north_america/usa/california/los_angeles
            if city_url.startswith('https://www.happycow.net/'):
                path_part = city_url.replace('https://www.happycow.net/', '').strip('/')
                ajax_path = path_part.replace('/', '%7C')
            else:
                # Fallback: assume it's already a path
                ajax_path = city_url.replace('|', '%7C').replace('/', '%7C')
            
            ajax_url = f"https://www.happycow.net/ajax/views/city/venues/{ajax_path}"
            
            logger.info(f"Calling AJAX endpoint: {ajax_url}")
            
            response = self.session.get(ajax_url, timeout=15)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            if not data.get('success', False):
                raise Exception("AJAX response indicates failure")
            
            html_content = data.get('data', {}).get('data', '')
            if not html_content:
                raise Exception("No HTML content in AJAX response")
            
            # Parse restaurants from HTML
            restaurants = self.parse_restaurants_from_html(html_content, city_url)
            
            return {
                'success': True,
                'restaurants': restaurants,
                'total_restaurants': len(restaurants),
                'pages_scraped': 1,
                'ajax_url': ajax_url
            }
            
        except Exception as e:
            logger.error(f"Error scraping city via AJAX: {e}")
            return {
                'success': False,
                'error': str(e),
                'restaurants': [],
                'total_restaurants': 0,
                'pages_scraped': 0
            }
    
    def parse_restaurants_from_html(self, html_content, city_path):
        """Parse restaurant data from HTML content"""
        restaurants = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all venue items
        venue_items = soup.find_all('div', class_='venue-list-item')
        logger.info(f"Found {len(venue_items)} venue items")
        
        for item in venue_items:
            try:
                restaurant = self.extract_restaurant_data(item, city_path)
                if restaurant:
                    restaurants.append(restaurant)
            except Exception as e:
                logger.warning(f"Error parsing restaurant: {e}")
                continue
        
        return restaurants
    
    def extract_restaurant_data(self, item, city_path):
        """Extract data from a single restaurant item"""
        try:
            # Basic info
            venue_id = item.get('data-id', '')
            venue_type = item.get('data-type', 'unknown')
            
            # Name
            name_elem = item.find('a', class_='venue-list-item-name-link')
            name = name_elem.get_text(strip=True) if name_elem else 'Unknown'
            
            # Rating
            rating = 0.0
            rating_elem = item.find('div', class_='venue-list-item-rating')
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Review count
            review_count = 0
            review_elem = item.find('span', class_='venue-list-item-review-count')
            if review_elem:
                review_text = review_elem.get_text(strip=True)
                review_match = re.search(r'(\d+)', review_text)
                if review_match:
                    review_count = int(review_match.group(1))
            
            # Address
            address = ''
            address_elem = item.find('div', class_='venue-list-item-address')
            if address_elem:
                address = address_elem.get_text(strip=True)
            
            # Coordinates from Google Maps link
            latitude, longitude = self.extract_coordinates(item)
            
            # Phone
            phone = ''
            phone_elem = item.find('a', href=re.compile(r'^tel:'))
            if phone_elem:
                phone = phone_elem.get('href', '').replace('tel:', '')
            
            # Website
            website = ''
            website_elem = item.find('a', class_='venue-list-item-website')
            if website_elem:
                website = website_elem.get('href', '')
            
            # Cuisine tags
            cuisine_tags = []
            cuisine_elems = item.find_all('span', class_='venue-list-item-cuisine')
            for elem in cuisine_elems:
                cuisine_tags.append(elem.get_text(strip=True))
            
            # Price range
            price_range = ''
            price_elem = item.find('span', class_='venue-list-item-price')
            if price_elem:
                price_range = price_elem.get_text(strip=True)
            
            # Features
            features = []
            feature_elems = item.find_all('span', class_='venue-list-item-feature')
            for elem in feature_elems:
                features.append(elem.get_text(strip=True))
            
            # Extract city and state from path
            path_parts = city_path.replace('|', '/').split('/')
            city_name = path_parts[-1].replace('_', ' ').title() if path_parts else 'Unknown'
            state_name = path_parts[-2].replace('_', ' ').title() if len(path_parts) > 1 else 'Unknown'
            
            restaurant = {
                'venue_id': venue_id,
                'name': name,
                'type': venue_type,
                'rating': rating,
                'review_count': review_count,
                'address': address,
                'latitude': latitude,
                'longitude': longitude,
                'phone': phone,
                'website': website,
                'cuisine_tags': cuisine_tags,
                'price_range': price_range,
                'features': features,
                'city_path': city_path.replace('|', '/'),
                'city_name': city_name,
                'state_name': state_name,
                'country_code': 'US',
                'scraped_at': datetime.utcnow().isoformat(),
                'page_number': 1
            }
            
            return restaurant
            
        except Exception as e:
            logger.error(f"Error extracting restaurant data: {e}")
            return None
    
    def extract_coordinates(self, item):
        """Extract latitude and longitude from Google Maps links"""
        try:
            # Look for Google Maps link
            maps_link = item.find('a', href=re.compile(r'google\.com/maps'))
            if maps_link:
                href = maps_link.get('href', '')
                # Extract coordinates from URL like: https://www.google.com/maps?q=32.74339,-96.826994
                coord_match = re.search(r'q=(-?\d+\.?\d*),(-?\d+\.?\d*)', href)
                if coord_match:
                    latitude = float(coord_match.group(1))
                    longitude = float(coord_match.group(2))
                    return latitude, longitude
            
            return None, None
            
        except Exception as e:
            logger.warning(f"Error extracting coordinates: {e}")
            return None, None

# Initialize scraper
scraper = HappyCowScraper()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'HappyCow Cloud Scraper'
    })

@app.route('/scrape', methods=['POST'])
def scrape_city():
    """Main scraping endpoint for n8n"""
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Extract parameters
        city_url = data.get('url')
        full_path = data.get('full_path')
        city_name = data.get('city', 'Unknown')
        state_name = data.get('state', 'Unknown')
        
        if not city_url:
            return jsonify({
                'success': False,
                'error': 'Missing required parameter: url'
            }), 400
        
        logger.info(f"Starting scrape for {city_name}, {state_name}")
        logger.info(f"URL: {city_url}")
        logger.info(f"Path: {full_path}")
        
        start_time = time.time()
        
        # If we don't have the path, extract it from the URL
        if not full_path:
            full_path = scraper.extract_city_path(city_url)
            if not full_path:
                return jsonify({
                    'success': False,
                    'error': 'Could not extract city path from URL'
                }), 400
        
        # Scrape the city using the actual URL
        result = scraper.scrape_city_ajax(city_url)
        
        # Add timing and context
        duration = int(time.time() - start_time)
        result['duration_seconds'] = duration
        result['city_name'] = city_name
        result['state_name'] = state_name
        result['city_path'] = full_path
        result['timestamp'] = datetime.utcnow().isoformat()
        
        logger.info(f"Scraping completed: {result['total_restaurants']} restaurants found in {duration}s")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in scrape endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'restaurants': [],
            'total_restaurants': 0,
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/test', methods=['GET'])
def test_scraper():
    """Test endpoint with Dallas data"""
    test_data = {
        'url': 'https://www.happycow.net/north_america/usa/texas/dallas/',
        'full_path': 'north_america/usa/texas/dallas',
        'city': 'Dallas',
        'state': 'Texas'
    }
    
    # Use the main scrape function
    with app.test_request_context('/scrape', json=test_data, method='POST'):
        return scrape_city()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting HappyCow Cloud Scraper on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug) 