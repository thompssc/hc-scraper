#!/usr/bin/env python3
"""
Debug scraper to understand HappyCow page structure
"""

import asyncio
import re
from crawl4ai import AsyncWebCrawler

async def debug_page_structure():
    """Debug the actual page structure"""
    print("🔍 Debugging HappyCow page structure...")
    
    url = "https://www.happycow.net/north_america/usa/texas/dallas/"
    
    async with AsyncWebCrawler(verbose=True, headless=True) as crawler:
        result = await crawler.arun(url=url)
        
        if hasattr(result, 'success') and result.success:
            if hasattr(result, 'html'):
                html = result.html
                print(f"✅ Page loaded successfully!")
                print(f"📊 HTML length: {len(html)} characters")
                
                # Look for different patterns
                patterns = {
                    'venue-list-item': r'venue-list-item',
                    'card-listing': r'card-listing',
                    'data-id': r'data-id="[^"]*"',
                    'restaurant names': r'<h[1-6][^>]*>.*?</h[1-6]>',
                    'google maps links': r'https://www\.google\.com/maps[^"]*',
                    'rating elements': r'rating[^>]*>',
                    'address elements': r'address[^>]*>'
                }
                
                print(f"\n🔍 Pattern Analysis:")
                for name, pattern in patterns.items():
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    print(f"   {name}: {len(matches)} matches")
                    if matches and len(matches) <= 5:
                        for i, match in enumerate(matches[:3]):
                            print(f"      {i+1}: {match[:100]}...")
                
                # Look for any div elements that might contain restaurants
                div_classes = re.findall(r'<div[^>]*class="([^"]*)"', html)
                unique_classes = set(div_classes)
                restaurant_classes = [cls for cls in unique_classes if any(word in cls.lower() for word in ['venue', 'restaurant', 'listing', 'card', 'item'])]
                
                print(f"\n🏷️ Potential restaurant div classes:")
                for cls in restaurant_classes[:10]:
                    count = div_classes.count(cls)
                    print(f"   {cls}: {count} occurrences")
                
                # Look for specific HappyCow elements
                hc_patterns = {
                    'venue elements': r'<[^>]*venue[^>]*>',
                    'listing elements': r'<[^>]*listing[^>]*>',
                    'card elements': r'<[^>]*card[^>]*>',
                    'item elements': r'<[^>]*item[^>]*>'
                }
                
                print(f"\n🥕 HappyCow-specific patterns:")
                for name, pattern in hc_patterns.items():
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    print(f"   {name}: {len(matches)} matches")
                
                # Show a sample of the HTML around potential restaurant data
                venue_match = re.search(r'venue.*?>', html, re.IGNORECASE)
                if venue_match:
                    start = max(0, venue_match.start() - 200)
                    end = min(len(html), venue_match.end() + 500)
                    sample = html[start:end]
                    print(f"\n📄 Sample HTML around venue element:")
                    print(f"{sample}")
                
                return True
            else:
                print("❌ No HTML content available")
                return False
        else:
            print("❌ Failed to load page")
            if hasattr(result, 'error_message'):
                print(f"Error: {result.error_message}")
            return False

async def main():
    """Main function"""
    await debug_page_structure()

if __name__ == "__main__":
    asyncio.run(main()) 