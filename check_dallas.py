#!/usr/bin/env python3

import pandas as pd

# Load the CSV
df = pd.read_csv('city_listings.csv')

# Find Dallas entries
dallas_rows = df[df['city'].str.contains('Dallas', case=False, na=False)]

print("=== DALLAS ENTRIES IN CSV ===")
if len(dallas_rows) > 0:
    for idx, row in dallas_rows.iterrows():
        print(f"City: {row['city']}")
        print(f"State: {row['state']}")
        print(f"Entries: {row['entries']}")
        print(f"Path: {row['city_path']}")
        print(f"URL: {row['url']}")
        print("-" * 50)
else:
    print("No Dallas entries found")

print(f"\nTotal cities in CSV: {len(df)}") 