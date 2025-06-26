#!/usr/bin/env python3
"""
Test script to verify Crawl4AI installation and test basic HappyCow scraping
"""

import asyncio
from crawl4ai import AsyncWebCrawler
import json
import re

async def test_basic_crawl():
    """Test basic crawling functionality"""
    print("🚀 Testing Crawl4AI basic functionality...")
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        # Test with a simple page first
        result = await crawler.arun(url="https://httpbin.org/html")
        
        print(f"Result type: {type(result)}")
        print(f"Result attributes: {dir(result)}")
        
        if hasattr(result, 'success') and result.success:
            print("✅ Basic crawling works!")
            if hasattr(result, 'extracted_content'):
                print(f"📄 Content: {str(result.extracted_content)[:100]}...")
        else:
            print("❌ Basic crawling failed!")
            if hasattr(result, 'error_message'):
                print(f"Error: {result.error_message}")

async def test_happycow_simple():
    """Test simple HappyCow access"""
    print("\n🥕 Testing HappyCow page access...")
    
    url = "https://www.happycow.net/north_america/usa/texas/dallas/"
    
    async with AsyncWebCrawler(verbose=True, headless=True) as crawler:
        result = await crawler.arun(url=url)
        
        print(f"Result type: {type(result)}")
        
        if hasattr(result, 'success') and result.success:
            print("✅ HappyCow page loaded!")
            
            if hasattr(result, 'html'):
                html_content = result.html
                print(f"📊 Page length: {len(html_content)} characters")
                
                # Check for restaurant listings
                if "venue-list-item" in html_content:
                    print("✅ Found restaurant listings!")
                    
                    # Count restaurants
                    restaurant_count = len(re.findall(r'venue-list-item', html_content))
                    print(f"🏪 Found approximately {restaurant_count} restaurant elements")
                    
                    # Look for coordinates
                    maps_links = re.findall(r'https://www\.google\.com/maps\?q=([^"]+)', html_content)
                    coord_count = len([link for link in maps_links if ',' in link])
                    print(f"📍 Found {coord_count} potential coordinate links")
                    
                    # Show first few restaurant names
                    name_pattern = r'<h4[^>]*venue-list-item-name[^>]*>.*?<a[^>]*>([^<]+)</a>'
                    names = re.findall(name_pattern, html_content, re.DOTALL)
                    print(f"🏪 Sample restaurant names: {names[:3]}")
                    
                else:
                    print("⚠️ No restaurant listings found")
                    # Show a sample of the HTML to debug
                    print(f"Sample HTML: {html_content[:500]}...")
        else:
            print("❌ Failed to load HappyCow page!")
            if hasattr(result, 'error_message'):
                print(f"Error: {result.error_message}")

async def main():
    """Run tests"""
    print("🧪 Starting Crawl4AI tests...\n")
    
    try:
        await test_basic_crawl()
        await test_happycow_simple()
        print("\n🎉 Tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 