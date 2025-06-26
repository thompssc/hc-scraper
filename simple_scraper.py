#!/usr/bin/env python3
"""
Simple HappyCow Scraper - Basic test version
"""

import asyncio
import json
import re
from crawl4ai import AsyncWebCrawler

async def test_scrape_dallas():
    """Simple test of Dallas HappyCow page"""
    print("🥕 Testing HappyCow Dallas scraping...")
    
    url = "https://www.happycow.net/north_america/usa/texas/dallas/"
    
    # Simple JavaScript to extract data
    js_code = """
    () => {
        // Look for different possible selectors
        const selectors = [
            'div.venue-list-item.card-listing',
            'div.venue-list-item', 
            '.card-listing',
            '[data-id]',
            '.venue-card',
            '.restaurant-item'
        ];
        
        let elements = [];
        let usedSelector = '';
        
        for (const selector of selectors) {
            elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                usedSelector = selector;
                break;
            }
        }
        
        if (elements.length === 0) {
            return {
                error: 'No restaurant elements found',
                selectors_tried: selectors,
                page_title: document.title,
                body_classes: document.body.className,
                sample_html: document.body.innerHTML.substring(0, 500)
            };
        }
        
        const restaurants = [];
        
        elements.forEach((element, index) => {
            // Get name
            let name = 'Unknown Restaurant ' + (index + 1);
            const nameEl = element.querySelector('h4 a, .venue-name a, a[href*="/reviews/"]');
            if (nameEl) {
                name = nameEl.textContent.trim();
            }
            
            // Get address  
            let address = null;
            const addressEl = element.querySelector('.venue-list-item-address, .address, .location');
            if (addressEl) {
                address = addressEl.textContent.trim();
            }
            
            // Get maps link
            let mapsUrl = null;
            const mapsEl = element.querySelector('a[href*="google.com/maps"]');
            if (mapsEl) {
                mapsUrl = mapsEl.href;
            }
            
            restaurants.push({
                name: name,
                address: address,
                maps_url: mapsUrl,
                data_id: element.getAttribute('data-id'),
                element_class: element.className
            });
        });
        
        return {
            success: true,
            selector_used: usedSelector,
            count: restaurants.length,
            restaurants: restaurants.slice(0, 5), // First 5 for testing
            page_title: document.title
        };
    }
    """
    
    async with AsyncWebCrawler(verbose=True, headless=True) as crawler:
        result = await crawler.arun(
            url=url,
            js_code=js_code,
            wait_for="body",
            delay_before_return_html=3.0
        )
        
        if hasattr(result, 'success') and result.success:
            if hasattr(result, 'extracted_content') and result.extracted_content:
                try:
                    data = json.loads(result.extracted_content)
                    
                    if data.get('success'):
                        print(f"✅ Found {data['count']} restaurants using selector: {data['selector_used']}")
                        print(f"📄 Page title: {data['page_title']}")
                        
                        for i, restaurant in enumerate(data['restaurants']):
                            print(f"\n🏪 Restaurant {i+1}:")
                            print(f"   Name: {restaurant['name']}")
                            print(f"   Address: {restaurant['address']}")
                            print(f"   Maps URL: {restaurant['maps_url']}")
                            print(f"   Data ID: {restaurant['data_id']}")
                            print(f"   Element class: {restaurant['element_class']}")
                            
                            # Extract coordinates if maps URL exists
                            if restaurant['maps_url']:
                                coord_match = re.search(r'q=(-?\d+\.?\d*),(-?\d+\.?\d*)', restaurant['maps_url'])
                                if coord_match:
                                    lat, lng = float(coord_match.group(1)), float(coord_match.group(2))
                                    print(f"   Coordinates: ({lat}, {lng})")
                        
                        return True
                    else:
                        print(f"❌ No restaurants found")
                        print(f"Selectors tried: {data.get('selectors_tried', [])}")
                        print(f"Page title: {data.get('page_title', 'Unknown')}")
                        print(f"Body classes: {data.get('body_classes', 'None')}")
                        print(f"Sample HTML: {data.get('sample_html', '')[:200]}...")
                        return False
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    print(f"Raw content: {result.extracted_content[:500]}...")
                    return False
            else:
                print("❌ No extracted content")
                return False
        else:
            print("❌ Crawling failed")
            if hasattr(result, 'error_message'):
                print(f"Error: {result.error_message}")
            return False

async def main():
    """Main function"""
    print("🧪 Simple HappyCow Scraper Test")
    success = await test_scrape_dallas()
    
    if success:
        print("\n✅ Test successful! Ready to build full scraper.")
    else:
        print("\n❌ Test failed. Need to investigate page structure.")

if __name__ == "__main__":
    asyncio.run(main()) 