# Complete N8N Automation Plan for HappyCow Scraping

## Overview
This document outlines a complete end-to-end automation system using n8n to scrape HappyCow restaurant data, store it in Supabase, and provide real-time notifications via Slack.

## System Architecture

```
CSV File (city_listings.csv) 
    ↓ (trigger_status = 'pending')
n8n Workflow Trigger
    ↓
Python Scraper Script
    ↓
Supabase Database Storage
    ↓
Slack Notification
    ↓
Update CSV Status
```

## 1. Python Scraper Script Requirements

### Script: `production_city_scraper.py`

**Arguments:**
- `full_path`: City path (e.g., "north_america/usa/texas/dallas")
- `url`: Full HappyCow URL (e.g., "https://www.happycow.net/north_america/usa/texas/dallas/")

**Features:**
- Multi-page iteration (automatic pagination detection)
- Comprehensive data extraction (name, type, rating, address, coordinates, etc.)
- Error handling and retry logic
- Progress tracking and logging
- Pandas DataFrame output
- Supabase integration for direct database insertion

### Data Structure to Extract:
```python
restaurant_data = {
    'venue_id': str,           # HappyCow venue ID
    'name': str,               # Restaurant name
    'type': str,               # vegan, vegetarian, veg-options
    'rating': float,           # Average rating (0-5)
    'review_count': int,       # Number of reviews
    'address': str,            # Full address
    'latitude': float,         # GPS coordinates
    'longitude': float,        # GPS coordinates
    'phone': str,              # Phone number (if available)
    'website': str,            # Website URL (if available)
    'cuisine_tags': list,      # Cuisine types
    'price_range': str,        # $, $$, $$$, $$$$
    'features': list,          # Delivery, takeout, etc.
    'city_path': str,          # Source city path
    'scraped_at': datetime,    # When scraped
    'page_number': int,        # Which page found on
}
```

## 2. CSV Trigger System

### Enhanced city_listings.csv Structure:
```csv
state,city,entries,full_path,url,trigger_status,last_scraped,scrape_priority
California,Los Angeles,686,north_america/usa/california/los_angeles,https://www.happycow.net/north_america/usa/california/los_angeles/,pending,NULL,high
Texas,Dallas,193,north_america/usa/texas/dallas,https://www.happycow.net/north_america/usa/texas/dallas/,pending,NULL,medium
```

**Trigger Statuses:**
- `pending`: Ready to scrape
- `running`: Currently being scraped
- `completed`: Successfully scraped
- `error`: Failed scraping
- `skip`: Manually skipped

## 3. N8N Workflow Design

### Workflow Nodes (12 total):

#### 1. **Schedule Trigger** 
- Runs every 5 minutes
- Checks for pending cities

#### 2. **CSV File Reader**
- Reads city_listings.csv
- Filters for `trigger_status = 'pending'`
- Limits to 1 city per run (to avoid overwhelming)

#### 3. **City Data Processor**
- Extracts city information
- Validates required fields
- Sets status to 'running'

#### 4. **Update CSV Status (Running)**
- Updates trigger_status to 'running'
- Adds timestamp

#### 5. **Python Scraper Executor**
- Calls production_city_scraper.py
- Passes full_path and url arguments
- Captures output and errors

#### 6. **Scraper Results Processor**
- Parses scraper output
- Validates data quality
- Counts restaurants found

#### 7. **Supabase Data Inserter**
- Inserts restaurant data into Supabase
- Handles duplicate detection
- Batch processing for efficiency

#### 8. **Success/Error Branch**
- Routes based on scraper success/failure
- Different handling for each outcome

#### 9. **Slack Success Notification**
- Sends success message with stats
- Includes city name and restaurant count

#### 10. **Slack Error Notification**
- Sends error details
- Includes city name and error message

#### 11. **Update CSV Status (Final)**
- Sets status to 'completed' or 'error'
- Updates last_scraped timestamp

#### 12. **Cleanup & Logging**
- Logs workflow completion
- Cleans up temporary files

## 4. Supabase Database Schema

### Table: `restaurants`
```sql
CREATE TABLE restaurants (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    venue_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    rating DECIMAL(2,1),
    review_count INTEGER,
    address TEXT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    phone TEXT,
    website TEXT,
    cuisine_tags TEXT[],
    price_range TEXT,
    features TEXT[],
    city_path TEXT NOT NULL,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    page_number INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_restaurants_city_path ON restaurants(city_path);
CREATE INDEX idx_restaurants_venue_id ON restaurants(venue_id);
CREATE INDEX idx_restaurants_type ON restaurants(type);
CREATE INDEX idx_restaurants_rating ON restaurants(rating);
```

### Table: `scraping_logs`
```sql
CREATE TABLE scraping_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    city_path TEXT NOT NULL,
    status TEXT NOT NULL, -- 'started', 'completed', 'error'
    restaurants_found INTEGER,
    pages_scraped INTEGER,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER
);
```

## 5. Python Scraper Implementation

### Key Components:

#### A. Argument Parsing
```python
import argparse
import sys

def parse_arguments():
    parser = argparse.ArgumentParser(description='HappyCow City Scraper')
    parser.add_argument('full_path', help='City path (e.g., north_america/usa/texas/dallas)')
    parser.add_argument('url', help='Full HappyCow URL')
    parser.add_argument('--max-pages', type=int, default=10, help='Maximum pages to scrape')
    return parser.parse_args()
```

#### B. Multi-Page Iteration
```python
def scrape_all_pages(city_path, max_pages=10):
    all_restaurants = []
    page = 1
    
    while page <= max_pages:
        print(f"Scraping page {page} for {city_path}")
        
        # AJAX endpoint with pagination
        url = f"https://www.happycow.net/ajax/views/city/venues/{city_path}?page={page}"
        
        restaurants = scrape_page(url, page)
        
        if not restaurants:  # No more results
            break
            
        all_restaurants.extend(restaurants)
        page += 1
        time.sleep(3)  # Rate limiting
    
    return all_restaurants
```

#### C. Supabase Integration
```python
from supabase import create_client
import os

def save_to_supabase(restaurants_df):
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_KEY')
    )
    
    # Convert DataFrame to list of dicts
    records = restaurants_df.to_dict('records')
    
    # Batch insert with conflict handling
    result = supabase.table('restaurants').upsert(
        records,
        on_conflict='venue_id'
    ).execute()
    
    return len(result.data)
```

## 6. N8N Node Configurations

### Node 1: Schedule Trigger
```json
{
  "rule": {
    "interval": [
      {
        "field": "minutes",
        "triggerAtMinute": 5
      }
    ]
  }
}
```

### Node 2: CSV File Reader
```javascript
// JavaScript code for CSV processing
const fs = require('fs');
const csv = require('csv-parser');

const results = [];
fs.createReadStream('/path/to/city_listings.csv')
  .pipe(csv())
  .on('data', (data) => {
    if (data.trigger_status === 'pending') {
      results.push(data);
    }
  })
  .on('end', () => {
    // Return first pending city
    return results.slice(0, 1);
  });
```

### Node 5: Python Scraper Executor
```javascript
// Execute Python script
const { exec } = require('child_process');

const fullPath = $node["City Data Processor"].json["full_path"];
const url = $node["City Data Processor"].json["url"];

const command = `python production_city_scraper.py "${fullPath}" "${url}"`;

exec(command, (error, stdout, stderr) => {
  if (error) {
    return { error: error.message, stderr };
  }
  return { success: true, output: stdout };
});
```

### Node 7: Supabase Data Inserter
```javascript
// Supabase insertion logic
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  $env.SUPABASE_URL,
  $env.SUPABASE_SERVICE_KEY
);

const restaurantData = JSON.parse($node["Scraper Results Processor"].json["restaurants"]);

const { data, error } = await supabase
  .from('restaurants')
  .upsert(restaurantData, { onConflict: 'venue_id' });

if (error) {
  throw new Error(`Supabase error: ${error.message}`);
}

return { inserted: data.length };
```

### Node 9: Slack Success Notification
```javascript
// Slack notification
const cityName = $node["City Data Processor"].json["city"];
const restaurantCount = $node["Supabase Data Inserter"].json["inserted"];

return {
  text: `✅ HappyCow scraping completed for ${cityName}!`,
  blocks: [
    {
      type: "section",
      text: {
        type: "mrkdwn",
        text: `*City:* ${cityName}\n*Restaurants Found:* ${restaurantCount}\n*Status:* Completed Successfully`
      }
    }
  ]
};
```

## 7. Manual Trigger Process

### How to Trigger Scraping:

1. **Open city_listings.csv**
2. **Find desired city row**
3. **Change trigger_status from 'pending' to 'pending'** (or use a different trigger value)
4. **Save file**
5. **Wait for next n8n cycle (up to 5 minutes)**

### Batch Triggering:
```python
# Script to trigger multiple cities
import pandas as pd

def trigger_cities(city_names, priority='high'):
    df = pd.read_csv('city_listings.csv')
    
    for city in city_names:
        mask = df['city'] == city
        df.loc[mask, 'trigger_status'] = 'pending'
        df.loc[mask, 'scrape_priority'] = priority
    
    df.to_csv('city_listings.csv', index=False)
    print(f"Triggered {len(city_names)} cities for scraping")

# Usage
trigger_cities(['Los Angeles', 'New York City', 'Chicago'])
```

## 8. Monitoring & Management

### Dashboard Queries:
```sql
-- Scraping progress
SELECT 
    trigger_status,
    COUNT(*) as city_count,
    SUM(entries) as total_restaurants
FROM city_listings 
GROUP BY trigger_status;

-- Recent scraping activity
SELECT 
    city_path,
    restaurants_found,
    completed_at,
    duration_seconds
FROM scraping_logs 
WHERE completed_at > NOW() - INTERVAL '24 hours'
ORDER BY completed_at DESC;

-- Top cities by restaurant count
SELECT 
    city_path,
    COUNT(*) as restaurant_count
FROM restaurants 
GROUP BY city_path 
ORDER BY restaurant_count DESC 
LIMIT 20;
```

### Error Handling:
- Automatic retry for network errors (up to 3 attempts)
- Slack alerts for persistent failures
- Manual intervention triggers for problem cities
- Comprehensive logging for debugging

## 9. Scaling Considerations

### Performance Optimization:
- **Rate Limiting**: 3-5 seconds between requests
- **Batch Processing**: Process 1 city at a time
- **Parallel Processing**: Future enhancement for multiple cities
- **Caching**: Store successful results to avoid re-scraping

### Resource Management:
- **Memory Usage**: Process cities individually to avoid memory issues
- **Disk Space**: Regular cleanup of temporary files
- **API Limits**: Monitor HappyCow for rate limiting
- **Database Connections**: Use connection pooling

## 10. Deployment Checklist

### Prerequisites:
- [ ] n8n instance running (cloud or self-hosted)
- [ ] Supabase database configured
- [ ] Slack webhook configured
- [ ] Python environment with required packages
- [ ] city_listings.csv file accessible to n8n
- [ ] Environment variables configured

### Environment Variables:
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
SLACK_WEBHOOK_URL=your_slack_webhook
CSV_FILE_PATH=/path/to/city_listings.csv
PYTHON_SCRIPT_PATH=/path/to/production_city_scraper.py
```

### Testing Process:
1. **Test single city scraping manually**
2. **Verify Supabase integration**
3. **Test Slack notifications**
4. **Run n8n workflow with test city**
5. **Monitor for 24 hours**
6. **Scale to production cities**

## 11. Expected Results

### Timeline:
- **Setup**: 1-2 days
- **Testing**: 1-2 days  
- **Production**: 2-3 weeks for all cities (at 1 city per 5 minutes)

### Data Volume:
- **Total Cities**: 4,827
- **Estimated Restaurants**: 50,000+
- **Database Size**: ~500MB
- **Processing Time**: 24/7 operation for 2-3 weeks

### Success Metrics:
- **Completion Rate**: >95% of cities successfully scraped
- **Data Quality**: >90% of restaurants with coordinates
- **Error Rate**: <5% of scraping attempts fail
- **Performance**: Average 2-3 minutes per city

This comprehensive system will provide fully automated HappyCow data collection with real-time monitoring and notifications, scalable to handle the entire dataset efficiently. 