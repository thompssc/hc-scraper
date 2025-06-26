#!/usr/bin/env python3
"""
Enhance city_listings.csv with trigger status columns for n8n automation
"""

import pandas as pd
import argparse
from datetime import datetime

def enhance_city_listings(input_file: str = 'city_listings.csv', output_file: str = 'enhanced_city_listings.csv'):
    """
    Add trigger status columns to city_listings.csv for n8n automation
    """
    try:
        # Read the original CSV
        df = pd.read_csv(input_file)
        print(f"Loaded {len(df)} cities from {input_file}")
        
        # Add new columns for n8n automation
        df['trigger_status'] = 'ready'  # ready, pending, running, completed, error, skip
        df['last_scraped'] = None  # Will be filled when scraping completes
        df['scrape_priority'] = 'medium'  # high, medium, low
        df['restaurants_found'] = None  # Will be filled after scraping
        df['last_error'] = None  # Error message if scraping fails
        df['retry_count'] = 0  # Number of retry attempts
        df['created_at'] = datetime.now().isoformat()
        
        # Set priority based on entry count
        def set_priority(entries):
            if entries >= 500:
                return 'high'
            elif entries >= 100:
                return 'medium'
            else:
                return 'low'
        
        df['scrape_priority'] = df['entries'].apply(set_priority)
        
        # Save enhanced CSV
        df.to_csv(output_file, index=False)
        print(f"Enhanced CSV saved to {output_file}")
        
        # Print summary
        print("\nPriority Distribution:")
        print(df['scrape_priority'].value_counts())
        
        print("\nTop 10 cities by entries:")
        print(df.nlargest(10, 'entries')[['city', 'state', 'entries', 'scrape_priority']])
        
        return df
        
    except Exception as e:
        print(f"Error enhancing city listings: {e}")
        return None

def trigger_cities(csv_file: str, city_names: list, status: str = 'pending'):
    """
    Set trigger status for specific cities
    """
    try:
        df = pd.read_csv(csv_file)
        
        updated_count = 0
        for city_name in city_names:
            mask = df['city'].str.contains(city_name, case=False, na=False)
            if mask.any():
                df.loc[mask, 'trigger_status'] = status
                df.loc[mask, 'retry_count'] = 0  # Reset retry count
                updated_count += mask.sum()
                print(f"Set {city_name} to {status}")
            else:
                print(f"City '{city_name}' not found")
        
        if updated_count > 0:
            df.to_csv(csv_file, index=False)
            print(f"Updated {updated_count} cities in {csv_file}")
        
        return updated_count
        
    except Exception as e:
        print(f"Error triggering cities: {e}")
        return 0

def reset_status(csv_file: str, from_status: str, to_status: str = 'ready'):
    """
    Reset cities from one status to another
    """
    try:
        df = pd.read_csv(csv_file)
        
        mask = df['trigger_status'] == from_status
        count = mask.sum()
        
        if count > 0:
            df.loc[mask, 'trigger_status'] = to_status
            df.loc[mask, 'last_error'] = None  # Clear error messages
            df.to_csv(csv_file, index=False)
            print(f"Reset {count} cities from '{from_status}' to '{to_status}'")
        else:
            print(f"No cities found with status '{from_status}'")
        
        return count
        
    except Exception as e:
        print(f"Error resetting status: {e}")
        return 0

def show_status(csv_file: str):
    """
    Show current status of all cities
    """
    try:
        df = pd.read_csv(csv_file)
        
        print("Status Distribution:")
        print(df['trigger_status'].value_counts())
        
        print("\nPriority Distribution:")
        print(df['scrape_priority'].value_counts())
        
        print("\nRecent Activity (last 10):")
        recent_mask = df['last_scraped'].notna()
        if recent_mask.any():
            recent = df[recent_mask].sort_values(by='last_scraped', ascending=False).head(10)
            print(recent[['city', 'state', 'trigger_status', 'restaurants_found', 'last_scraped']])
        else:
            print("No recent activity")
        
        print("\nErrors:")
        errors = df[df['last_error'].notna()]
        if not errors.empty:
            print(errors[['city', 'state', 'last_error', 'retry_count']])
        else:
            print("No errors")
        
    except Exception as e:
        print(f"Error showing status: {e}")

def main():
    parser = argparse.ArgumentParser(description='Manage city listings for n8n automation')
    parser.add_argument('--action', choices=['enhance', 'trigger', 'reset', 'status'], 
                       default='enhance', help='Action to perform')
    parser.add_argument('--input', default='city_listings.csv', help='Input CSV file')
    parser.add_argument('--output', default='enhanced_city_listings.csv', help='Output CSV file')
    parser.add_argument('--cities', nargs='+', help='City names to trigger')
    parser.add_argument('--from-status', help='Status to reset from')
    parser.add_argument('--to-status', default='ready', help='Status to reset to')
    parser.add_argument('--trigger-status', default='pending', help='Status to set for triggered cities')
    
    args = parser.parse_args()
    
    if args.action == 'enhance':
        enhance_city_listings(args.input, args.output)
    
    elif args.action == 'trigger':
        if not args.cities:
            print("Please provide city names with --cities")
            return
        trigger_cities(args.output, args.cities, args.trigger_status)
    
    elif args.action == 'reset':
        if not args.from_status:
            print("Please provide --from-status")
            return
        reset_status(args.output, args.from_status, args.to_status)
    
    elif args.action == 'status':
        show_status(args.output)

if __name__ == "__main__":
    main() 