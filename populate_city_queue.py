#!/usr/bin/env python3
"""
Populate Supabase city_queue table from city_listings.csv
Run this after setting up the Supabase tables
"""

import pandas as pd
import json
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env.local file
env_locations = [
    '.env.local',
    '../.env.local',
    '../veganvoyage/.env.local',
    '../../veganvoyage/.env.local'
]

env_loaded = False
for env_path in env_locations:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded .env from: {env_path}")
        env_loaded = True
        break

if not env_loaded:
    print("⚠️  No .env.local file found.")
    exit(1)

# Get environment variables
SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SERVICE_KEY:
    print("❌ Missing Supabase credentials in environment variables")
    exit(1)

print(f"🔗 Using Supabase URL: {SUPABASE_URL}")

def load_cities_from_csv():
    """Load cities from CSV file"""
    try:
        df = pd.read_csv('city_listings.csv')
        print(f"✅ Loaded {len(df)} cities from CSV")
        
        # Show sample of data
        print("\n📊 Sample data:")
        print(df.head()[['state', 'city', 'entries', 'city_path']].to_string())
        
        return df
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return None

def determine_priority(entries):
    """Determine scraping priority based on restaurant count"""
    if entries >= 500:
        return 'high'
    elif entries >= 100:
        return 'medium'
    else:
        return 'low'

def insert_cities_batch(cities_data, batch_size=100):
    """Insert cities in batches"""
    headers = {
        'apikey': SERVICE_KEY,
        'Authorization': f'Bearer {SERVICE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }
    
    total_cities = len(cities_data)
    successful_inserts = 0
    
    for i in range(0, total_cities, batch_size):
        batch = cities_data[i:i + batch_size]
        
        print(f"📥 Inserting batch {i//batch_size + 1}: cities {i+1}-{min(i+batch_size, total_cities)}")
        
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/city_queue",
            headers=headers,
            json=batch
        )
        
        if response.status_code == 201:
            successful_inserts += len(batch)
            print(f"✅ Batch inserted successfully")
        else:
            print(f"❌ Batch failed: {response.status_code} - {response.text}")
            
    return successful_inserts

def main():
    print("🚀 Starting city_queue population...")
    
    # Load CSV data
    df = load_cities_from_csv()
    if df is None:
        return
    
    # Prepare data for insertion
    print("📝 Preparing data for insertion...")
    
    cities_data = []
    for _, row in df.iterrows():
        # Create unique path by combining city_path with state abbreviation
        state_abbr = str(row['state']).lower().replace(' ', '_')
        unique_path = f"{row['city_path']}_{state_abbr}"
        
        city_data = {
            'city': row['city'],
            'state': row['state'],
            'entries': int(row['entries']),
            'full_path': unique_path,  # Use unique path
            'url': row['url'],
            'scrape_priority': determine_priority(row['entries']),
            'trigger_status': 'pending'
        }
        cities_data.append(city_data)
    
    # Insert data
    print(f"📤 Inserting {len(cities_data)} cities...")
    successful = insert_cities_batch(cities_data)
    
    # Summary
    print(f"\n🎉 POPULATION COMPLETE!")
    print(f"✅ Successfully inserted: {successful} cities")
    print(f"❌ Failed: {len(cities_data) - successful} cities")
    
    # Show priority breakdown
    priority_counts = {}
    for city in cities_data:
        priority = city['scrape_priority']
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    print(f"\n📊 Priority breakdown:")
    for priority, count in priority_counts.items():
        print(f"  {priority.upper()}: {count} cities")
    
    # Verify Dallas
    dallas_cities = [c for c in cities_data if 'dallas' in c['city'].lower()]
    print(f"\n🏙️  Dallas cities found: {len(dallas_cities)}")
    for city in dallas_cities:
        print(f"  - {city['city']}, {city['state']}: {city['entries']} entries")

if __name__ == "__main__":
    main() 