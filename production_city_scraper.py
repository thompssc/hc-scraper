#!/usr/bin/env python3
"""
HappyCow Production City Scraper
Designed for n8n workflow integration

Usage: python production_city_scraper.py <full_path> <url>
Example: python production_city_scraper.py "north_america/usa/texas/dallas" "https://www.happycow.net/north_america/usa/texas/dallas/"
"""

import argparse
import requests
import json
import time
import pandas as pd
import re
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class HappyCowScraper:
    def __init__(self, full_path: str, base_url: str, max_pages: int = 20):
        self.full_path = full_path
        self.base_url = base_url.rstrip('/')
        self.max_pages = max_pages
        self.session = requests.Session()
        
        # Set headers to mimic browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.restaurants = []
        
    def scrape_page(self, page_num: int) -> Tuple[List[Dict], bool]:
        """
        Scrape a single page of restaurants
        Returns: (restaurants_list, has_more_pages)
        """
        try:
            # Build AJAX URL for the page
            if page_num == 1:
                ajax_url = f"https://www.happycow.net/ajax/views/city/venues/{self.full_path}"
            else:
                ajax_url = f"https://www.happycow.net/ajax/views/city/venues/{self.full_path}?page={page_num}"
            
            logger.info(f"Scraping page {page_num}: {ajax_url}")
            
            # Make request
            response = self.session.get(ajax_url, timeout=30)
            response.raise_for_status()
            
            # Parse JSON response
            try:
                data = response.json()
                html_content = data.get('data', '')
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response for page {page_num}")
                return [], False
            
            if not html_content:
                logger.info(f"No content found for page {page_num}")
                return [], False
            
            # Parse HTML content
            soup = BeautifulSoup(html_content, 'html.parser')
            venue_items = soup.find_all('div', class_='venue-list-item')
            
            if not venue_items:
                logger.info(f"No venue items found on page {page_num}")
                return [], False
            
            page_restaurants = []
            for item in venue_items:
                restaurant_data = self.extract_restaurant_data(item, page_num)
                if restaurant_data:
                    page_restaurants.append(restaurant_data)
            
            logger.info(f"Found {len(page_restaurants)} restaurants on page {page_num}")
            
            # Check if there are more pages (if we got restaurants, assume there might be more)
            has_more = len(page_restaurants) > 0 and len(page_restaurants) >= 10  # Typical page size
            
            return page_restaurants, has_more
            
        except requests.RequestException as e:
            logger.error(f"Request failed for page {page_num}: {e}")
            return [], False
        except Exception as e:
            logger.error(f"Unexpected error scraping page {page_num}: {e}")
            return [], False
    
    def extract_restaurant_data(self, item, page_num: int) -> Optional[Dict]:
        """Extract restaurant data from a venue item"""
        try:
            # Basic information
            venue_id = item.get('data-id', '')
            if not venue_id:
                return None
            
            # Name
            name_elem = item.find('h3', class_='venue-name')
            name = name_elem.get_text(strip=True) if name_elem else 'Unknown'
            
            # Type (vegan, vegetarian, veg-options)
            venue_type = item.get('data-type', 'unknown')
            
            # Rating
            rating = 0.0
            rating_elem = item.find('div', class_='venue-rating')
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Review count
            review_count = 0
            review_elem = item.find('span', class_='review-count')
            if review_elem:
                review_text = review_elem.get_text(strip=True)
                review_match = re.search(r'(\d+)', review_text)
                if review_match:
                    review_count = int(review_match.group(1))
            
            # Address
            address_elem = item.find('div', class_='venue-address')
            address = address_elem.get_text(strip=True) if address_elem else ''
            
            # Coordinates from Google Maps link
            latitude, longitude = self.extract_coordinates(item)
            
            # Phone number
            phone = ''
            phone_elem = item.find('span', class_='venue-phone')
            if phone_elem:
                phone = phone_elem.get_text(strip=True)
            
            # Website
            website = ''
            website_elem = item.find('a', class_='venue-website')
            if website_elem:
                website = website_elem.get('href', '')
            
            # Cuisine tags
            cuisine_tags = []
            cuisine_elems = item.find_all('span', class_='cuisine-tag')
            for elem in cuisine_elems:
                cuisine_tags.append(elem.get_text(strip=True))
            
            # Price range
            price_range = ''
            price_elem = item.find('span', class_='price-range')
            if price_elem:
                price_range = price_elem.get_text(strip=True)
            
            # Features (delivery, takeout, etc.)
            features = []
            feature_elems = item.find_all('span', class_='venue-feature')
            for elem in feature_elems:
                features.append(elem.get_text(strip=True))
            
            return {
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
                'city_path': self.full_path,
                'scraped_at': datetime.now().isoformat(),
                'page_number': page_num
            }
            
        except Exception as e:
            logger.error(f"Error extracting restaurant data: {e}")
            return None
    
    def extract_coordinates(self, item) -> Tuple[Optional[float], Optional[float]]:
        """Extract latitude and longitude from Google Maps link"""
        try:
            # Look for Google Maps link
            maps_link = item.find('a', href=re.compile(r'google\.com/maps'))
            if not maps_link:
                return None, None
            
            href = maps_link.get('href', '')
            
            # Pattern 1: ?q=lat,lng
            coord_match = re.search(r'[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)', href)
            if coord_match:
                lat = float(coord_match.group(1))
                lng = float(coord_match.group(2))
                return lat, lng
            
            # Pattern 2: @lat,lng
            coord_match = re.search(r'@(-?\d+\.?\d*),(-?\d+\.?\d*)', href)
            if coord_match:
                lat = float(coord_match.group(1))
                lng = float(coord_match.group(2))
                return lat, lng
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error extracting coordinates: {e}")
            return None, None
    
    def scrape_all_pages(self) -> List[Dict]:
        """Scrape all pages for the city"""
        logger.info(f"Starting scrape for city: {self.full_path}")
        
        page = 1
        total_restaurants = 0
        
        while page <= self.max_pages:
            restaurants, has_more = self.scrape_page(page)
            
            if not restaurants:
                logger.info(f"No restaurants found on page {page}, stopping")
                break
            
            self.restaurants.extend(restaurants)
            total_restaurants += len(restaurants)
            
            logger.info(f"Page {page}: {len(restaurants)} restaurants (Total: {total_restaurants})")
            
            if not has_more:
                logger.info(f"No more pages detected after page {page}")
                break
            
            page += 1
            
            # Rate limiting - wait between requests
            if page <= self.max_pages:
                time.sleep(3)
        
        logger.info(f"Scraping completed. Total restaurants found: {len(self.restaurants)}")
        return self.restaurants
    
    def save_to_csv(self, filename: Optional[str] = None) -> str:
        """Save results to CSV file"""
        if not filename:
            city_name = self.full_path.split('/')[-1]
            filename = f"restaurants_{city_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if not self.restaurants:
            logger.warning("No restaurants to save")
            return filename
        
        df = pd.DataFrame(self.restaurants)
        df.to_csv(filename, index=False)
        logger.info(f"Saved {len(self.restaurants)} restaurants to {filename}")
        return filename
    
    def get_dataframe(self) -> pd.DataFrame:
        """Return results as pandas DataFrame"""
        return pd.DataFrame(self.restaurants)
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        if not self.restaurants:
            return {
                'total_restaurants': 0,
                'pages_scraped': 0,
                'city_path': self.full_path
            }
        
        df = pd.DataFrame(self.restaurants)
        
        return {
            'total_restaurants': len(self.restaurants),
            'pages_scraped': df['page_number'].max() if 'page_number' in df.columns else 0,
            'city_path': self.full_path,
            'types': df['type'].value_counts().to_dict() if 'type' in df.columns else {},
            'avg_rating': df['rating'].mean() if 'rating' in df.columns else 0,
            'restaurants_with_coordinates': len(df[(df['latitude'].notna()) & (df['longitude'].notna())]) if 'latitude' in df.columns else 0
        }

def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description='HappyCow City Scraper for n8n Integration')
    parser.add_argument('full_path', help='City path (e.g., north_america/usa/texas/dallas)')
    parser.add_argument('url', help='Full HappyCow URL')
    parser.add_argument('--max-pages', type=int, default=20, help='Maximum pages to scrape (default: 20)')
    parser.add_argument('--output-csv', help='Output CSV filename')
    parser.add_argument('--output-json', help='Output JSON filename for n8n')
    
    args = parser.parse_args()
    
    try:
        # Initialize scraper
        scraper = HappyCowScraper(args.full_path, args.url, args.max_pages)
        
        # Scrape all pages
        restaurants = scraper.scrape_all_pages()
        
        # Get summary
        summary = scraper.get_summary()
        
        # Output for n8n (JSON to stdout)
        output = {
            'success': True,
            'summary': summary,
            'restaurants': restaurants
        }
        
        # Save to CSV if requested
        if args.output_csv:
            scraper.save_to_csv(args.output_csv)
        
        # Save to JSON if requested
        if args.output_json:
            with open(args.output_json, 'w') as f:
                json.dump(output, f, indent=2, default=str)
        
        # Output JSON to stdout for n8n
        print(json.dumps(output, default=str))
        
        return 0
        
    except Exception as e:
        error_output = {
            'success': False,
            'error': str(e),
            'city_path': args.full_path
        }
        
        logger.error(f"Scraping failed: {e}")
        print(json.dumps(error_output))
        return 1

if __name__ == "__main__":
    sys.exit(main()) 