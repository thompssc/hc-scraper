# HappyCow Restaurant Scraper

A modern, AI-powered scraper for extracting vegan restaurant data from HappyCow using crawl4ai.

## Features

- 🤖 **AI-Powered Extraction**: Uses crawl4ai with local LLM for intelligent data extraction
- 🥸 **Stealth Mode**: Appears as normal user traffic with realistic headers and timing
- 🌍 **Multi-City Support**: Pre-configured for 37+ major cities worldwide
- 📊 **Comprehensive Data**: Extracts 15+ data fields per restaurant
- 🚀 **High Performance**: Concurrent processing with automatic retry logic
- 🔍 **Coordinate Extraction**: Gets precise GPS coordinates from Google Maps links

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install
```

### 2. Test Setup

```bash
python scripts/test_setup.py
```

### 3. Run Scraper

```bash
# Test single city
python scripts/run_scraper.py --single-city "Austin"

# Test mode
python scripts/run_scraper.py --test
```

## Expected Results

- **Single City**: 50-200 restaurants in 2-5 minutes
- **All Cities**: 15,000-25,000 restaurants in 2-4 hours
- **Success Rate**: 90%+ with 95%+ coordinate coverage 