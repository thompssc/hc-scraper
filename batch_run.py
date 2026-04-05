#!/usr/bin/env python3
"""
Batch scraper that pulls cities directly from the city_queue table
and scrapes them sequentially with delays to avoid WAF blocks.
"""

import json
import os
import sys
import time
import logging

from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Import scraper components from playwright_scraper
from playwright_scraper import PlaywrightScraper, upsert_venues, url_to_city_path


def get_supabase():
    sb_url = "https://vzlzyckayprsnpajrxmr.supabase.co"
    sb_key = os.environ.get("SUPABASE_KEY")
    if not sb_key:
        logger.error("SUPABASE_KEY not set")
        sys.exit(1)
    return create_client(sb_url, sb_key)


def batch_scrape(limit: int = 10, delay_between: float = 15.0):
    sb = get_supabase()

    # Get pending cities ordered by entry count (biggest first)
    cities = (
        sb.table("city_queue")
        .select("id,city,state,entries,url,trigger_status")
        .eq("trigger_status", "pending")
        .order("entries", desc=True)
        .limit(limit)
        .execute()
    )

    if not cities.data:
        logger.info("No pending cities in queue")
        return []

    logger.info(f"Found {len(cities.data)} cities to scrape")
    results = []

    with PlaywrightScraper(headless=True, max_pages=50) as scraper:
        for i, city in enumerate(cities.data):
            city_id = city["id"]
            city_name = city["city"]
            state = city["state"]
            url = city["url"]

            logger.info(f"\n[{i+1}/{len(cities.data)}] Scraping {city_name}, {state} ({city['entries']} expected entries)")

            # Mark as running
            sb.table("city_queue").update({"trigger_status": "running"}).eq("id", city_id).execute()

            start = time.time()
            try:
                venues = scraper.scrape_city(url)
                duration = int(time.time() - start)

                if not venues:
                    logger.warning(f"  0 venues found for {city_name} - possible WAF block")
                    # Check if WAF blocked (scraper raises RuntimeError with WAF_BLOCKED)
                    sb.table("city_queue").update({
                        "trigger_status": "pending",
                        "error_message": "0 venues returned, possible WAF"
                    }).eq("id", city_id).execute()
                    results.append({"city": city_name, "state": state, "success": False, "reason": "0 venues"})
                    # If we get 0 venues, WAF may be kicking in - stop the batch
                    logger.warning("Stopping batch early - possible WAF detection")
                    break

                count = upsert_venues(venues)
                logger.info(f"  {count} venues upserted in {duration}s")

                sb.table("city_queue").update({
                    "trigger_status": "completed",
                    "restaurants_scraped": count,
                }).eq("id", city_id).execute()

                results.append({
                    "city": city_name,
                    "state": state,
                    "success": True,
                    "venues": count,
                    "duration": duration,
                })

            except RuntimeError as e:
                if "WAF_BLOCKED" in str(e):
                    logger.error(f"  WAF BLOCKED on {city_name} - stopping batch")
                    sb.table("city_queue").update({
                        "trigger_status": "pending",
                        "error_message": str(e)
                    }).eq("id", city_id).execute()
                    results.append({"city": city_name, "state": state, "success": False, "reason": "WAF"})
                    break
                raise
            except Exception as e:
                duration = int(time.time() - start)
                logger.error(f"  Error: {e}")
                sb.table("city_queue").update({
                    "trigger_status": "error",
                    "error_message": str(e)[:500]
                }).eq("id", city_id).execute()
                results.append({"city": city_name, "state": state, "success": False, "reason": str(e)[:200]})

            # Delay between cities to avoid WAF
            if i < len(cities.data) - 1:
                logger.info(f"  Waiting {delay_between}s before next city...")
                time.sleep(delay_between)

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Number of cities to scrape")
    parser.add_argument("--delay", type=float, default=15.0, help="Seconds between cities")
    args = parser.parse_args()

    results = batch_scrape(limit=args.limit, delay_between=args.delay)
    print(json.dumps(results, indent=2, default=str))
