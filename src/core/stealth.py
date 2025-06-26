"""
Stealth browsing configuration to appear as normal user traffic.
NO research headers - appears as regular HappyCow user.
"""

import random
import asyncio
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class StealthConfig:
    """Configuration for stealth browsing"""
    
    # Realistic user agents (recent Chrome/Firefox on Windows/Mac)
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    
    # Normal browser headers that real users have
    BASE_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }
    
    # Realistic referrers (like user came from Google/social media)
    REFERRERS = [
        "https://www.google.com/",
        "https://www.google.com/search?q=vegan+restaurants",
        "https://www.facebook.com/",
        ""  # Direct navigation
    ]
    
    # Human-like delays (seconds)
    MIN_DELAY = 3.0
    MAX_DELAY = 8.0

def get_stealth_headers() -> Dict[str, str]:
    """Generate realistic browser headers"""
    config = StealthConfig()
    headers = config.BASE_HEADERS.copy()
    headers["User-Agent"] = random.choice(config.USER_AGENTS)
    
    # Add realistic referer occasionally
    if random.random() < 0.7:  # 70% chance of having referer
        headers["Referer"] = random.choice(config.REFERRERS)
    
    return headers

def get_human_delay() -> float:
    """Generate human-like delay between requests"""
    config = StealthConfig()
    base_delay = random.uniform(config.MIN_DELAY, config.MAX_DELAY)
    # Occasionally longer delays (user reading page)
    if random.random() < 0.1:  # 10% chance of longer delay
        base_delay += random.uniform(5.0, 15.0)
    return base_delay 