#!/usr/bin/env python3
"""
Main execution script for HappyCow scraping
Usage: python scripts/run_scraper.py --single-city "Austin"
"""

import asyncio
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

def setup_logging(log_level: str = "INFO"):
    """Configure logging"""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'scraping.log'),
            logging.StreamHandler()
        ]
    )

def load_cities_config():
    """Load cities configuration from JSON file"""
    config_path = Path(__file__).parent.parent / "config" / "cities.json"
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Cities configuration not found at {config_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in cities configuration at {config_path}")

def test_stealth_module():
    """Test if stealth module can be imported and works"""
    try:
        from core.stealth import get_stealth_headers, get_human_delay
        headers = get_stealth_headers()
        delay = get_human_delay()
        print(f"✅ Stealth module working! Sample delay: {delay:.1f}s")
        print(f"✅ Sample User-Agent: {headers.get('User-Agent', 'None')}")
        return True
    except ImportError as e:
        print(f"❌ Cannot import stealth module: {e}")
        return False

async def main():
    parser = argparse.ArgumentParser(description='HappyCow Restaurant Scraper')
    parser.add_argument('--single-city', type=str, help='Test scrape a single city by name')
    parser.add_argument('--test', action='store_true', help='Run test scraping on test cities')
    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Setup
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    print("🚀 HappyCow Scraper")
    print("=" * 50)
    
    # Test stealth module
    if not test_stealth_module():
        return 1
    
    # Load city configuration
    try:
        cities_config = load_cities_config()
        print(f"✅ Loaded {len(cities_config['cities'])} cities from config")
        print(f"✅ Test cities: {cities_config['test_cities']}")
    except Exception as e:
        logger.error(f"Failed to load cities configuration: {e}")
        return 1
    
    # Handle single city test
    if args.single_city:
        if args.single_city not in cities_config['cities']:
            logger.error(f"City '{args.single_city}' not found in configuration")
            logger.info(f"Available cities: {list(cities_config['cities'].keys())}")
            return 1
        
        city_url = cities_config['cities'][args.single_city]
        print(f"\n🧪 Testing single city: {args.single_city}")
        print(f"📍 URL: {city_url}")
        
        # For now, just show what would happen
        print("\n⚠️  crawl4ai not installed yet. This is what would happen:")
        print(f"  1. Navigate to {city_url}")
        print(f"  2. Use stealth headers to appear as normal user")
        print(f"  3. Extract restaurant data using AI")
        print(f"  4. Save results to data/raw/")
        
        return 0
    
    elif args.test:
        print("\n🧪 Test mode - would scrape test cities:")
        for city in cities_config['test_cities']:
            print(f"  - {city}: {cities_config['cities'][city]}")
        
        print("\n⚠️  Install crawl4ai to enable actual scraping:")
        print("  pip install crawl4ai")
        print("  playwright install")
        
        return 0
    
    else:
        print("\n📖 Usage Examples:")
        print("  python scripts/run_scraper.py --single-city Austin")
        print("  python scripts/run_scraper.py --test")
        print("  python scripts/run_scraper.py --single-city Portland --log-level DEBUG")
        
        return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1) 