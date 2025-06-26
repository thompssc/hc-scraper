#!/usr/bin/env python3
"""
HappyCow AJAX Scraper - Direct API Access
=========================================

This scraper directly calls the HappyCow AJAX API endpoint that loads restaurant data,
bypassing the need to wait for JavaScript execution.

Key Discovery: Restaurant listings are loaded via AJAX call to:
/ajax/views/city/venues/{path}{params}

This is much faster and more reliable than trying to execute JavaScript.
"""

import asyncio
import json
import re
import time
from pathlib import Path
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup
import pandas as pd
from crawl4ai import AsyncWebCrawler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HappyCowAjaxScraper:
    def __init__(self):
        self.base_url = "https://www.happycow.net"
        self.session_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.happycow.net/',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        
    async def get_city_path_from_url(self, city_url):
        """Extract the city path from a HappyCow city URL."""
        try:
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(
                    url=city_url,
                    wait_for="css:.breadcrumb",
                    timeout=30000
                )
                
                if not result or not hasattr(result, 'success') or not result.success:
                    logger.error(f"Failed to load city page: {city_url}")
                    return None
                    
                soup = BeautifulSoup(result.html, 'html.parser')
                
                # Find the last breadcrumb item which contains the path
                breadcrumb_items = soup.select('.breadcrumb li')
                if not breadcrumb_items:
                    logger.error("No breadcrumb found on page")
                    return None
                    
                last_breadcrumb = breadcrumb_items[-1]
                path = last_breadcrumb.get('data-path')
                
                if not path:
                    logger.error("No data-path found in last breadcrumb")
                    return None
                    
                logger.info(f"✅ Extracted city path: {path}")
                return path
                
        except Exception as e:
            logger.error(f"Error extracting city path: {e}")
            return None
    
    async def get_ajax_data(self, city_path, page=1, filters=None):
        """Get restaurant data from the AJAX endpoint."""
        try:
            # Convert path format: replace / with | and encode
            ajax_path = city_path.replace('/', '|')
            ajax_path = quote(ajax_path, safe='')
            
            # Build query parameters
            params = []
            if page > 1:
                params.append(f"page={page}")
            if filters:
                for key, value in filters.items():
                    params.append(f"{key}={value}")
            
            query_string = "&" + "&".join(params) if params else ""
            
            # Construct AJAX URL
            ajax_url = f"{self.base_url}/ajax/views/city/venues/{ajax_path}{query_string}"
            
            logger.info(f"🔄 Calling AJAX endpoint: {ajax_url}")
            
            async with AsyncWebCrawler(
                headers=self.session_headers,
                verbose=True
            ) as crawler:
                result = await crawler.arun(
                    url=ajax_url,
                    timeout=30000
                )
                
                if not result or not hasattr(result, 'success') or not result.success:
                    logger.error(f"AJAX request failed")
                    return None
                
                # Parse JSON response
                try:
                    data = json.loads(result.html)
                    if data.get('success'):
                        logger.info(f"✅ AJAX request successful")
                        return data
                    else:
                        logger.error(f"AJAX request returned success=false")
                        return None
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Response content: {result.html[:500]}...")
                    return None
                    
        except Exception as e:
            logger.error(f"Error in AJAX request: {e}")
            return None
    
    def parse_restaurant_html(self, html_content):
        """Parse restaurant data from the HTML content returned by AJAX."""
        soup = BeautifulSoup(html_content, 'html.parser')
        restaurants = []
        
        # Find all venue list items
        venue_items = soup.select('.venue-list-item.card-listing')
        logger.info(f"🔍 Found {len(venue_items)} venue items in HTML")
        
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
                restaurant['name'] = name_el.get_text(strip=True) if name_el else None
                
                # URL
                link_el = item.select_one('a[href*="/reviews/"]')
                restaurant['url'] = link_el.get('href') if link_el else None
                
                # Address
                address_el = item.select_one('.venue-address')
                restaurant['address'] = address_el.get_text(strip=True) if address_el else None
                
                # Rating
                rating_el = item.select_one('.venue-rating')
                if rating_el:
                    rating_text = rating_el.get_text(strip=True)
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    restaurant['rating'] = float(rating_match.group(1)) if rating_match else None
                
                # Coordinates from Google Maps link
                maps_link = item.select_one('a[href*="google.com/maps"]')
                if maps_link:
                    href = maps_link.get('href')
                    # Extract coordinates from URL like: https://www.google.com/maps?q=32.7767,-96.7970
                    if href and isinstance(href, str):
                        coord_match = re.search(r'q=([+-]?\d+\.?\d*),([+-]?\d+\.?\d*)', href)
                        if coord_match:
                            restaurant['latitude'] = float(coord_match.group(1))
                            restaurant['longitude'] = float(coord_match.group(2))
                
                # Cuisine type
                cuisine_el = item.select_one('.venue-cuisine')
                restaurant['cuisine'] = cuisine_el.get_text(strip=True) if cuisine_el else None
                
                # Price range
                price_el = item.select_one('.venue-price')
                restaurant['price_range'] = price_el.get_text(strip=True) if price_el else None
                
                # Hours status
                hours_el = item.select_one('.venue-hours-text')
                restaurant['hours_status'] = hours_el.get_text(strip=True) if hours_el else None
                
                # Distance (if available)
                distance_el = item.select_one('.venue-distance')
                restaurant['distance'] = distance_el.get_text(strip=True) if distance_el else None
                
                # Features/tags
                features = []
                feature_els = item.select('.venue-features .feature-tag')
                for feature_el in feature_els:
                    features.append(feature_el.get_text(strip=True))
                restaurant['features'] = features
                
                # Only add if we have essential data
                if restaurant.get('name') and restaurant.get('id'):
                    restaurants.append(restaurant)
                    
            except Exception as e:
                logger.error(f"Error parsing restaurant item: {e}")
                continue
        
        return restaurants
    
    async def scrape_city(self, city_url, max_pages=10):
        """Scrape all restaurants from a city."""
        logger.info(f"🥕 Starting to scrape city: {city_url}")
        
        # Step 1: Get the city path
        city_path = await self.get_city_path_from_url(city_url)
        if not city_path:
            logger.error("Failed to extract city path")
            return []
        
        all_restaurants = []
        page = 1
        
        while page <= max_pages:
            logger.info(f"📄 Scraping page {page}")
            
            # Step 2: Get AJAX data
            ajax_data = await self.get_ajax_data(city_path, page=page)
            if not ajax_data:
                logger.error(f"Failed to get AJAX data for page {page}")
                break
            
            # Step 3: Parse restaurant HTML
            html_content = ajax_data.get('data', {}).get('data', '')
            if not html_content:
                logger.error(f"No HTML content in AJAX response for page {page}")
                break
            
            restaurants = self.parse_restaurant_html(html_content)
            if not restaurants:
                logger.info(f"No restaurants found on page {page}, stopping")
                break
            
            logger.info(f"✅ Found {len(restaurants)} restaurants on page {page}")
            all_restaurants.extend(restaurants)
            
            # Check pagination
            paginated_data = ajax_data.get('data', {}).get('paginated', {})
            has_next = paginated_data.get('next') is not None
            
            if not has_next:
                logger.info("No more pages available")
                break
            
            page += 1
            
            # Rate limiting
            await asyncio.sleep(2)
        
        logger.info(f"🎉 Total restaurants scraped: {len(all_restaurants)}")
        return all_restaurants
    
    def save_to_csv(self, restaurants, filename):
        """Save restaurants to CSV file."""
        if not restaurants:
            logger.warning("No restaurants to save")
            return
        
        df = pd.DataFrame(restaurants)
        
        # Ensure data directory exists
        data_dir = Path("data/processed")
        data_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = data_dir / filename
        df.to_csv(filepath, index=False)
        logger.info(f"💾 Saved {len(restaurants)} restaurants to {filepath}")
        
        # Print summary
        print(f"\n📊 SCRAPING SUMMARY")
        print(f"{'='*50}")
        print(f"Total restaurants: {len(restaurants)}")
        print(f"With coordinates: {len([r for r in restaurants if r.get('latitude')])}")
        print(f"Vegan restaurants: {len([r for r in restaurants if r.get('type') == 'vegan'])}")
        print(f"Top-rated: {len([r for r in restaurants if r.get('is_top')])}")
        print(f"Partner restaurants: {len([r for r in restaurants if r.get('is_partner')])}")
        print(f"Saved to: {filepath}")

async def main():
    """Main function to test the scraper."""
    scraper = HappyCowAjaxScraper()
    
    # Test with Dallas
    dallas_url = "https://www.happycow.net/north_america/usa/texas/dallas/"
    
    try:
        restaurants = await scraper.scrape_city(dallas_url, max_pages=5)
        scraper.save_to_csv(restaurants, "dallas_restaurants_ajax.csv")
        
        # Print first few restaurants as example
        if restaurants:
            print(f"\n🔍 SAMPLE RESTAURANTS:")
            print(f"{'='*50}")
            for i, restaurant in enumerate(restaurants[:3]):
                print(f"\n{i+1}. {restaurant.get('name', 'Unknown')}")
                print(f"   Type: {restaurant.get('type', 'Unknown')}")
                print(f"   Address: {restaurant.get('address', 'Unknown')}")
                print(f"   Rating: {restaurant.get('rating', 'Unknown')}")
                if restaurant.get('latitude'):
                    print(f"   Coordinates: {restaurant['latitude']}, {restaurant['longitude']}")
                print(f"   URL: {restaurant.get('url', 'Unknown')}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 