#!/usr/bin/env python3
"""
Dynamic HappyCow Scraper - Handles JavaScript-rendered content
"""

import asyncio
import json
import re
from crawl4ai import AsyncWebCrawler

async def scrape_with_wait():
    """Scrape HappyCow with proper waiting for dynamic content"""
    print("🥕 Scraping HappyCow with dynamic content loading...")
    
    url = "https://www.happycow.net/north_america/usa/texas/dallas/"
    
    # JavaScript to wait for and extract restaurant data
    extraction_js = """
    async () => {
        console.log('Starting restaurant extraction...');
        
        // Wait for restaurant elements to appear
        const waitForElements = async (selector, maxWait = 15000) => {
            const startTime = Date.now();
            while (Date.now() - startTime < maxWait) {
                const elements = document.querySelectorAll(selector);
                if (elements.length > 0) {
                    console.log(`Found ${elements.length} elements with selector: ${selector}`);
                    return elements;
                }
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            console.log(`Timeout waiting for selector: ${selector}`);
            return [];
        };
        
        // Try different selectors
        const selectors = [
            'div.venue-list-item.card-listing',
            'div.venue-list-item',
            '.card-listing',
            '[data-id]'
        ];
        
        let venues = [];
        let usedSelector = '';
        
        for (const selector of selectors) {
            console.log(`Trying selector: ${selector}`);
            venues = await waitForElements(selector);
            if (venues.length > 0) {
                usedSelector = selector;
                break;
            }
        }
        
        if (venues.length === 0) {
            // Scroll to trigger lazy loading
            console.log('No venues found, trying scroll to trigger loading...');
            window.scrollTo(0, document.body.scrollHeight);
            await new Promise(resolve => setTimeout(resolve, 3000));
            
            // Try again
            for (const selector of selectors) {
                venues = document.querySelectorAll(selector);
                if (venues.length > 0) {
                    usedSelector = selector;
                    break;
                }
            }
        }
        
        if (venues.length === 0) {
            return {
                error: 'No restaurant venues found',
                page_title: document.title,
                body_classes: document.body.className,
                selectors_tried: selectors,
                page_ready_state: document.readyState,
                sample_html: document.body.innerHTML.substring(0, 1000)
            };
        }
        
        console.log(`Extracting data from ${venues.length} venues...`);
        
        const restaurants = [];
        
        for (let i = 0; i < venues.length; i++) {
            const venue = venues[i];
            try {
                // Extract name
                const nameEl = venue.querySelector('h4.venue-list-item-name a, .venue-name a, h4 a, a[href*="/reviews/"]');
                const name = nameEl ? nameEl.textContent.trim() : `Restaurant ${i + 1}`;
                
                // Extract address
                const addressEl = venue.querySelector('.venue-list-item-address, .address, .location');
                const address = addressEl ? addressEl.textContent.trim() : null;
                
                // Extract rating
                const ratingEl = venue.querySelector('.rating-stars, [class*="rating"]');
                const rating = ratingEl ? (ratingEl.getAttribute('title') || ratingEl.textContent) : null;
                
                // Extract maps link
                const mapsEl = venue.querySelector('a[href*="google.com/maps"]');
                const mapsUrl = mapsEl ? mapsEl.href : null;
                
                // Extract coordinates from maps URL
                let coordinates = null;
                if (mapsUrl) {
                    const coordMatch = mapsUrl.match(/q=(-?\\d+\\.?\\d*),(-?\\d+\\.?\\d*)/);
                    if (coordMatch) {
                        coordinates = [parseFloat(coordMatch[1]), parseFloat(coordMatch[2])];
                    }
                }
                
                const restaurant = {
                    name: name,
                    address: address,
                    rating: rating,
                    maps_url: mapsUrl,
                    coordinates: coordinates,
                    happycow_url: nameEl ? nameEl.href : null,
                    data_id: venue.getAttribute('data-id'),
                    data_type: venue.getAttribute('data-type'),
                    data_top: venue.getAttribute('data-top'),
                    data_new: venue.getAttribute('data-new'),
                    data_partner: venue.getAttribute('data-partner')
                };
                
                restaurants.push(restaurant);
                
            } catch (error) {
                console.error(`Error extracting restaurant ${i}:`, error);
                restaurants.push({
                    error: error.message,
                    index: i,
                    html_sample: venue.outerHTML.substring(0, 200)
                });
            }
        }
        
        return {
            success: true,
            selector_used: usedSelector,
            count: restaurants.length,
            restaurants: restaurants,
            page_title: document.title,
            timestamp: new Date().toISOString()
        };
    }
    """
    
    async with AsyncWebCrawler(
        verbose=True,
        headless=True,
        browser_type="chromium",
        page_timeout=60000,  # 60 second timeout
        magic=True  # Enable smart waiting
    ) as crawler:
        
        result = await crawler.arun(
            url=url,
            js_code=extraction_js,
            wait_for="body",
            delay_before_return_html=10.0,  # Wait 10 seconds for content to load
            simulate_user=True,  # Simulate human behavior
            override_navigator=True  # Override navigator properties
        )
        
        if hasattr(result, 'success') and result.success:
            if hasattr(result, 'extracted_content') and result.extracted_content:
                try:
                    data = json.loads(result.extracted_content)
                    
                    if data.get('success'):
                        print(f"✅ Successfully extracted {data['count']} restaurants!")
                        print(f"📄 Page title: {data['page_title']}")
                        print(f"🔍 Used selector: {data['selector_used']}")
                        
                        # Show sample restaurants
                        restaurants = data['restaurants']
                        print(f"\n🏪 Sample restaurants:")
                        for i, restaurant in enumerate(restaurants[:5]):
                            if 'error' not in restaurant:
                                print(f"   {i+1}. {restaurant['name']}")
                                print(f"      Address: {restaurant['address']}")
                                print(f"      Rating: {restaurant['rating']}")
                                print(f"      Type: {restaurant['data_type']}")
                                print(f"      Coordinates: {restaurant['coordinates']}")
                                print(f"      Data ID: {restaurant['data_id']}")
                                print()
                        
                        # Save results
                        with open('dallas_restaurants.json', 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        
                        print(f"💾 Saved results to dallas_restaurants.json")
                        
                        # Statistics
                        with_coords = len([r for r in restaurants if r.get('coordinates')])
                        vegan_count = len([r for r in restaurants if r.get('data_type') == 'vegan'])
                        vegetarian_count = len([r for r in restaurants if r.get('data_type') == 'vegetarian'])
                        veg_options_count = len([r for r in restaurants if r.get('data_type') == 'veg-options'])
                        
                        print(f"\n📊 Statistics:")
                        print(f"   Total restaurants: {len(restaurants)}")
                        print(f"   With coordinates: {with_coords}/{len(restaurants)} ({with_coords/len(restaurants)*100:.1f}%)")
                        print(f"   Vegan: {vegan_count}")
                        print(f"   Vegetarian: {vegetarian_count}")
                        print(f"   Veg-friendly: {veg_options_count}")
                        
                        return True
                    else:
                        print(f"❌ Extraction failed: {data.get('error', 'Unknown error')}")
                        print(f"Page title: {data.get('page_title', 'Unknown')}")
                        print(f"Selectors tried: {data.get('selectors_tried', [])}")
                        print(f"Page ready state: {data.get('page_ready_state', 'Unknown')}")
                        if 'sample_html' in data:
                            print(f"Sample HTML: {data['sample_html'][:300]}...")
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
    print("🧪 Dynamic HappyCow Scraper Test")
    success = await scrape_with_wait()
    
    if success:
        print("\n✅ Dynamic scraping successful! Ready for production scraping.")
    else:
        print("\n❌ Dynamic scraping failed. May need different approach.")

if __name__ == "__main__":
    asyncio.run(main()) 