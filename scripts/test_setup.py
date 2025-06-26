#!/usr/bin/env python3
"""
Test script to verify the hc-scraper setup
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

def test_imports():
    """Test if all modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        from core.stealth import get_stealth_headers, get_human_delay
        print("✅ stealth module imported successfully")
    except ImportError as e:
        print(f"❌ stealth module import failed: {e}")
        return False
    
    try:
        from models.restaurant import Restaurant, Coordinates, ScrapingResult
        print("✅ restaurant models imported successfully")
    except ImportError as e:
        print(f"❌ restaurant models import failed: {e}")
        return False
    
    return True

def test_stealth_functionality():
    """Test stealth module functionality"""
    print("\n🔍 Testing stealth functionality...")
    
    try:
        from core.stealth import get_stealth_headers, get_human_delay
        
        # Test headers
        headers = get_stealth_headers()
        print(f"✅ Generated headers with User-Agent: {headers.get('User-Agent', 'None')[:50]}...")
        
        # Test delay
        delay = get_human_delay()
        print(f"✅ Generated delay: {delay:.2f} seconds")
        
        return True
    except Exception as e:
        print(f"❌ Stealth functionality test failed: {e}")
        return False

def test_models():
    """Test restaurant models"""
    print("\n🏪 Testing restaurant models...")
    
    try:
        from models.restaurant import Restaurant, Coordinates, Address, VeganInfo
        
        # Create test restaurant
        restaurant = Restaurant(
            name="Test Vegan Restaurant",
            coordinates=Coordinates(latitude=30.2672, longitude=-97.7431),  # Austin
            address=Address(city="Austin", state="Texas"),
            vegan_info=VeganInfo(is_fully_vegan=True, vegan_category="vegan")
        )
        
        print(f"✅ Created test restaurant: {restaurant.name}")
        print(f"✅ Coordinates: {restaurant.coordinates.latitude}, {restaurant.coordinates.longitude}")
        print(f"✅ Vegan status: {restaurant.vegan_info.is_fully_vegan}")
        
        return True
    except Exception as e:
        print(f"❌ Models test failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    print("\n⚙️ Testing configuration...")
    
    try:
        import json
        config_path = Path(__file__).parent.parent / "config" / "cities.json"
        
        with open(config_path, 'r') as f:
            cities_config = json.load(f)
        
        print(f"✅ Loaded {len(cities_config['cities'])} cities")
        print(f"✅ Test cities: {cities_config['test_cities']}")
        print(f"✅ Priority cities: {cities_config['priority_cities']}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def main():
    print("🚀 HappyCow Scraper Setup Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_stealth_functionality,
        test_models,
        test_config
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Setup is ready.")
        print("\n📖 Next steps:")
        print("  1. Install crawl4ai: pip install crawl4ai")
        print("  2. Install playwright: playwright install")
        print("  3. Test single city: python scripts/run_scraper.py --single-city Austin")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 