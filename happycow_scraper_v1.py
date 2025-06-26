#!/usr/bin/env python3
"""
HappyCow Scraper v1 - Production ready scraper for HappyCow restaurant data
"""

import asyncio
import json
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from crawl4ai import AsyncWebCrawler
import time
from pathlib import Path

@dataclass
class Restaurant:
    """Restaurant data model"""
    name: str
    address: Optional[str] = None
    rating: Optional[float] = None
    price_range: Optional[str] = None
    cuisine_type: Optional[str] = None
    vegan_level: Optional[str] = None
    coordinates: Optional[tuple[float, float]] = None
    happycow_url: Optional[str] = None
    maps_url: Optional[str] = None
    data_id: Optional[str] = None
    data_type: Optional[str] = None
    phone: Optional[str] = None
    hours: Optional[str] = None
    description: Optional[str] = None

class HappyCowScraper:
    """Main scraper class for HappyCow data"""
    
    def __init__(self, delay_between_requests: float = 3.0):
        self.delay = delay_between_requests
        self.session_count = 0
        
    async def scrape_city(self, city_url: str, city_name: str) -> List[Restaurant]:
        """Scrape all restaurants from a city page"""
        print(f"🏙️ Scraping {city_name}: {city_url}")
        
        async with AsyncWebCrawler(
            verbose=True,
            headless=True,
            browser_type="chromium"
        ) as crawler:
            
            # JavaScript to extract restaurant data after page loads
            extraction_js = """
            () => {
                // Wait for content to load
                const waitForElements = (selector, timeout = 10000) => {
                    return new Promise((resolve) => {
                        const startTime = Date.now();
                        const check = () => {
                            const elements = document.querySelectorAll(selector);
                            if (elements.length > 0 || Date.now() - startTime > timeout) {
                                resolve(elements);
                            } else {
                                setTimeout(check, 100);
                            }
                        };
                        check();
                    });
                };
                
                // Try multiple possible selectors
                const selectors = [
                    'div.venue-list-item.card-listing',
                    'div.venue-list-item',
                    '.card-listing',
                    '[data-id]'
                ];
                
                let venueElements = [];
                for (const selector of selectors) {
                    venueElements = document.querySelectorAll(selector);
                    if (venueElements.length > 0) {
                        console.log(`Found ${venueElements.length} venues with selector: ${selector}`);
                        break;
                    }
                }
                
                if (venueElements.length === 0) {
                    console.log('No venue elements found, checking page structure...');
                    console.log('Body classes:', document.body.className);
                    console.log('Page title:', document.title);
                    return { error: 'No venues found', debug: document.body.innerHTML.substring(0, 1000) };
                }
                
                const restaurants = [];
                
                venueElements.forEach((element, index) => {
                    try {
                        // Try multiple name selectors
                        const nameSelectors = [
                            'h4.venue-list-item-name a',
                            '.venue-list-item-name a',
                            'h4 a',
                            'a[href*="/reviews/"]'
                        ];
                        
                        let nameElement = null;
                        for (const selector of nameSelectors) {
                            nameElement = element.querySelector(selector);
                            if (nameElement) break;
                        }
                        
                        // Try multiple address selectors
                        const addressSelectors = [
                            'span.venue-list-item-address',
                            '.venue-list-item-address',
                            '.address'
                        ];
                        
                        let addressElement = null;
                        for (const selector of addressSelectors) {
                            addressElement = element.querySelector(selector);
                            if (addressElement) break;
                        }
                        
                        // Get maps link
                        const mapsLink = element.querySelector('a[href*="google.com/maps"]');
                        
                        // Get rating
                        const ratingElement = element.querySelector('span.rating-stars, .rating-stars, [class*="rating"]');
                        
                        const restaurant = {
                            name: nameElement ? nameElement.textContent.trim() : `Unknown Restaurant ${index + 1}`,
                            address: addressElement ? addressElement.textContent.trim() : null,
                            rating: ratingElement ? ratingElement.getAttribute('title') || ratingElement.textContent : null,
                            maps_url: mapsLink ? mapsLink.href : null,
                            happycow_url: nameElement ? nameElement.href : null,
                            data_id: element.getAttribute('data-id'),
                            data_type: element.getAttribute('data-type'),
                            element_html: element.outerHTML.substring(0, 500) // For debugging
                        };
                        
                        // Extract coordinates from maps link
                        if (restaurant.maps_url) {
                            const coordMatch = restaurant.maps_url.match(/q=(-?\d+\.?\d*),(-?\d+\.?\d*)/);
                            if (coordMatch) {
                                restaurant.coordinates = [parseFloat(coordMatch[1]), parseFloat(coordMatch[2])];
                            }
                        }
                        
                        restaurants.push(restaurant);
                    } catch (error) {
                        console.error('Error extracting restaurant:', error);
                        restaurants.push({
                            error: error.message,
                            index: index,
                            element_html: element.outerHTML.substring(0, 200)
                        });
                    }
                });
                
                return {
                    success: true,
                    count: restaurants.length,
                    restaurants: restaurants,
                    page_title: document.title,
                    url: window.location.href
                };
            }
            """
            
            try:
                # Crawl with JavaScript extraction
                result = await crawler.arun(
                    url=city_url,
                    js_code=extraction_js,
                    wait_for="body",  # Wait for basic page load
                    delay_before_return_html=5.0,  # Give time for dynamic content
                    page_timeout=30000,  # 30 second timeout
                    magic=True  # Enable smart waiting
                )
                
                if result.success and result.extracted_content:
                    try:
                        data = json.loads(result.extracted_content)
                        
                        if data.get('success'):
                            print(f"✅ Successfully extracted {data.get('count', 0)} restaurants from {city_name}")
                            
                            # Convert to Restaurant objects
                            restaurants = []
                            for r_data in data.get('restaurants', []):
                                if 'error' not in r_data:
                                    restaurant = Restaurant(
                                        name=r_data.get('name', 'Unknown'),
                                        address=r_data.get('address'),
                                        rating=self._parse_rating(r_data.get('rating')),
                                        coordinates=tuple(r_data['coordinates']) if r_data.get('coordinates') else None,
                                        happycow_url=r_data.get('happycow_url'),
                                        maps_url=r_data.get('maps_url'),
                                        data_id=r_data.get('data_id'),
                                        data_type=r_data.get('data_type')
                                    )
                                    restaurants.append(restaurant)
                                else:
                                    print(f"⚠️ Error in restaurant data: {r_data.get('error')}")
                            
                            return restaurants
                        else:
                            print(f"❌ Extraction failed: {data.get('error', 'Unknown error')}")
                            if 'debug' in data:
                                print(f"Debug info: {data['debug'][:200]}...")
                            return []
                            
                    except json.JSONDecodeError as e:
                        print(f"❌ Failed to parse extracted data: {e}")
                        print(f"Raw content: {result.extracted_content[:500]}...")
                        return []
                else:
                    print(f"❌ Failed to crawl {city_url}")
                    if result.error_message:
                        print(f"Error: {result.error_message}")
                    return []
                    
            except Exception as e:
                print(f"❌ Exception while scraping {city_name}: {e}")
                return []
            
            finally:
                # Rate limiting
                if self.delay > 0:
                    print(f"⏱️ Waiting {self.delay}s before next request...")
                    await asyncio.sleep(self.delay)
    
    def _parse_rating(self, rating_str: Optional[str]) -> Optional[float]:
        """Parse rating from various formats"""
        if not rating_str:
            return None
            
        # Try to extract numeric rating
        rating_match = re.search(r'(\d+\.?\d*)', rating_str)
        if rating_match:
            try:
                return float(rating_match.group(1))
            except ValueError:
                pass
        
        return None
    
    async def save_results(self, restaurants: List[Restaurant], filename: str):
        """Save results to JSON file"""
        data = {
            'timestamp': time.time(),
            'count': len(restaurants),
            'restaurants': [asdict(r) for r in restaurants]
        }
        
        # Ensure data directory exists
        Path('data').mkdir(exist_ok=True)
        
        filepath = Path('data') / f"{filename}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(restaurants)} restaurants to {filepath}")

async def test_dallas():
    """Test scraping Dallas"""
    scraper = HappyCowScraper(delay_between_requests=2.0)
    
    dallas_url = "https://www.happycow.net/north_america/usa/texas/dallas/"
    restaurants = await scraper.scrape_city(dallas_url, "Dallas")
    
    print(f"\n📊 Results Summary:")
    print(f"   Total restaurants: {len(restaurants)}")
    
    if restaurants:
        with_coords = len([r for r in restaurants if r.coordinates])
        print(f"   With coordinates: {with_coords}/{len(restaurants)} ({with_coords/len(restaurants)*100:.1f}%)")
        
        # Show first few restaurants
        print(f"\n🏪 Sample restaurants:")
        for i, restaurant in enumerate(restaurants[:3]):
            print(f"   {i+1}. {restaurant.name}")
            print(f"      Address: {restaurant.address}")
            print(f"      Rating: {restaurant.rating}")
            print(f"      Coordinates: {restaurant.coordinates}")
            print()
        
        # Save results
        await scraper.save_results(restaurants, "dallas_test")
        print("✅ Test completed successfully!")
    else:
        print("❌ No restaurants found - check selectors and page structure")

async def main():
    """Main function"""
    print("🥕 HappyCow Scraper v1 - Starting test...")
    await test_dallas()

if __name__ == "__main__":
    asyncio.run(main()) 