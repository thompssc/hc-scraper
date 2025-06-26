#!/usr/bin/env python3
"""
Save HappyCow HTML for analysis
"""

import asyncio
from crawl4ai import AsyncWebCrawler

async def save_dallas_html():
    """Save Dallas page HTML"""
    print("🥕 Saving HappyCow Dallas HTML...")
    
    url = "https://www.happycow.net/north_america/usa/texas/dallas/"
    
    async with AsyncWebCrawler(verbose=True, headless=True) as crawler:
        result = await crawler.arun(url=url)
        
        if hasattr(result, 'success') and result.success:
            if hasattr(result, 'html'):
                html = result.html
                print(f"✅ Page loaded! HTML length: {len(html)} characters")
                
                # Save to file
                with open('dallas_page.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                
                print(f"💾 Saved to dallas_page.html")
                
                # Quick analysis
                if 'venue-list-item' in html:
                    print("✅ Found 'venue-list-item' in HTML")
                else:
                    print("❌ No 'venue-list-item' found")
                
                if 'card-listing' in html:
                    print("✅ Found 'card-listing' in HTML")
                else:
                    print("❌ No 'card-listing' found")
                
                # Count some basic elements
                import re
                div_count = len(re.findall(r'<div', html))
                a_count = len(re.findall(r'<a', html))
                h_count = len(re.findall(r'<h[1-6]', html))
                
                print(f"📊 Basic counts: {div_count} divs, {a_count} links, {h_count} headers")
                
                return True
            else:
                print("❌ No HTML content")
                return False
        else:
            print("❌ Failed to load page")
            return False

if __name__ == "__main__":
    asyncio.run(save_dallas_html()) 