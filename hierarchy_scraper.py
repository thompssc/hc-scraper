#!/usr/bin/env python3
"""
HappyCow Hierarchy Scraper
=========================

Scrapes the complete USA state-city hierarchy from HappyCow to determine
the order of cities to process based on listing counts.

Output: city_listings.csv with columns: state, city, entries, state_path, city_path
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from pathlib import Path

class HappyCowHierarchyScraper:
    def __init__(self):
        self.base_url = "https://www.happycow.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
    def scrape_state_data(self):
        """Scrape state-level data from USA page"""
        print("Scraping state data from USA page...")
        url = f'{self.base_url}/north_america/usa/'
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            state_data = []
            
            # Find all state links with counts
            state_links = soup.find_all('a', href=re.compile(r'/north_america/usa/[^/]+/$'))
            
            for link in state_links:
                text = link.get_text(strip=True)
                href = link.get('href')
                
                # Extract state name and count
                match = re.match(r'(.+?)\s*\((\d+)\)', text)
                if match:
                    state_name = match.group(1).strip()
                    count = int(match.group(2))
                    
                    # Extract state path from href
                    state_path = href.split('/')[-2] if href.endswith('/') else href.split('/')[-1]
                    
                    state_data.append({
                        'state': state_name,
                        'state_path': state_path,
                        'total_entries': count,
                        'url': f'{self.base_url}{href}'
                    })
                    
            print(f"Found {len(state_data)} states")
            return sorted(state_data, key=lambda x: x['total_entries'], reverse=True)
            
        except Exception as e:
            print(f"Error scraping state data: {e}")
            return []
    
    def scrape_city_data(self, state_info):
        """Scrape city-level data for a specific state"""
        print(f"Scraping cities for {state_info['state']} ({state_info['total_entries']} total entries)...")
        
        try:
            response = self.session.get(state_info['url'])
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            city_data = []
            
            # Find all city links with counts
            city_links = soup.find_all('a', href=re.compile(f"/north_america/usa/{state_info['state_path']}/[^/]+/$"))
            
            for link in city_links:
                text = link.get_text(strip=True)
                href = link.get('href')
                
                # Extract city name and count
                match = re.match(r'(.+?)\s*\((\d+)\)', text)
                if match:
                    city_name = match.group(1).strip()
                    count = int(match.group(2))
                    
                    # Extract city path from href
                    city_path = href.split('/')[-2] if href.endswith('/') else href.split('/')[-1]
                    
                    city_data.append({
                        'state': state_info['state'],
                        'state_path': state_info['state_path'],
                        'city': city_name,
                        'city_path': city_path,
                        'entries': count,
                        'full_path': f"north_america/usa/{state_info['state_path']}/{city_path}",
                        'url': f'{self.base_url}{href}'
                    })
            
            print(f"  Found {len(city_data)} cities in {state_info['state']}")
            return city_data
            
        except Exception as e:
            print(f"Error scraping cities for {state_info['state']}: {e}")
            return []
    
    def scrape_all_hierarchy(self):
        """Scrape complete state-city hierarchy"""
        print("Starting complete hierarchy scrape...")
        
        # Get state data
        states = self.scrape_state_data()
        if not states:
            print("No state data found!")
            return []
        
        all_cities = []
        
        # Process each state
        for i, state_info in enumerate(states, 1):
            print(f"\nProcessing state {i}/{len(states)}: {state_info['state']}")
            
            cities = self.scrape_city_data(state_info)
            all_cities.extend(cities)
            
            # Rate limiting
            time.sleep(2)
        
        return all_cities
    
    def save_to_csv(self, city_data, filename="city_listings.csv"):
        """Save city data to CSV file"""
        if not city_data:
            print("No data to save!")
            return
        
        df = pd.DataFrame(city_data)
        
        # Sort by entries (descending) to prioritize high-volume cities
        df = df.sort_values('entries', ascending=False)
        
        # Save to CSV
        output_path = Path(filename)
        df.to_csv(output_path, index=False)
        
        print(f"\nSaved {len(df)} cities to {output_path.absolute()}")
        
        # Print summary statistics
        print("\n=== SUMMARY STATISTICS ===")
        print(f"Total cities: {len(df)}")
        print(f"Total entries: {df['entries'].sum():,}")
        print(f"Top 10 cities by entries:")
        print(df[['state', 'city', 'entries']].head(10).to_string(index=False))
        
        print(f"\nStates by total entries:")
        state_totals = df.groupby('state')['entries'].sum().sort_values(ascending=False)
        print(state_totals.head(10).to_string())
        
        return output_path

def main():
    scraper = HappyCowHierarchyScraper()
    
    print("HappyCow Hierarchy Scraper")
    print("=" * 40)
    
    # Scrape all data
    city_data = scraper.scrape_all_hierarchy()
    
    if city_data:
        # Save to CSV
        output_file = scraper.save_to_csv(city_data)
        print(f"\n✅ Success! Data saved to: {output_file}")
        
        # Show prioritization strategy
        df = pd.DataFrame(city_data).sort_values('entries', ascending=False)
        print(f"\n🎯 SCRAPING PRIORITY ORDER (Top 20):")
        print("=" * 50)
        for i, row in df.head(20).iterrows():
            print(f"{row.name + 1:2d}. {row['city']}, {row['state']} ({row['entries']} entries)")
    else:
        print("❌ No data collected!")

if __name__ == "__main__":
    main() 