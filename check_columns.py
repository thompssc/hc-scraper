#!/usr/bin/env python3

import pandas as pd

# Load the CSV
df = pd.read_csv('city_listings.csv')

print("=== CSV COLUMNS ===")
print(df.columns.tolist())

print("\n=== FIRST FEW ROWS ===")
print(df.head())

print(f"\nTotal rows: {len(df)}") 