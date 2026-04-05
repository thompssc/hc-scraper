#!/usr/bin/env python3
"""
Fully autonomous HappyCow scraper — no LLM needed.

Pulls cities from city_queue, scrapes them, upserts to Supabase.
Automatically detects WAF blocks and adjusts cooldown timing.
Runs until all cities are done or max runtime is reached.

Usage:
    export SUPABASE_KEY="your-key"
    python auto_scraper.py                    # Run until done
    python auto_scraper.py --max-hours 24     # Stop after 24 hours
    python auto_scraper.py --batch-size 10    # 10 cities per batch
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

from supabase import create_client

from playwright_scraper import PlaywrightScraper, upsert_venues

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# --- Configuration ---
MIN_COOLDOWN = 300       # 5 min minimum between batches
MAX_COOLDOWN = 1800      # 30 min maximum
COOLDOWN_STEP = 120      # Increase by 2 min on WAF
COOLDOWN_DECAY = 60      # Decrease by 1 min on success
DELAY_BETWEEN_CITIES = 30  # Seconds between cities within a batch


def get_supabase():
    sb_url = "https://vzlzyckayprsnpajrxmr.supabase.co"
    sb_key = os.environ.get("SUPABASE_KEY")
    if not sb_key:
        logger.error("SUPABASE_KEY not set")
        sys.exit(1)
    return create_client(sb_url, sb_key)


def get_stats(sb):
    """Get current queue stats."""
    completed = sb.table("city_queue").select("id", count="exact").eq("trigger_status", "completed").execute()
    pending = sb.table("city_queue").select("id", count="exact").eq("trigger_status", "pending").execute()
    restaurants = sb.table("restaurants").select("venue_id", count="exact").execute()
    return {
        "completed": completed.count,
        "pending": pending.count,
        "restaurants": restaurants.count,
    }


def scrape_batch(scraper, sb, batch_size: int) -> dict:
    """Scrape one batch of cities. Returns summary dict."""
    cities = (
        sb.table("city_queue")
        .select("id,city,state,entries,url")
        .eq("trigger_status", "pending")
        .order("entries", desc=True)
        .limit(batch_size)
        .execute()
    )

    if not cities.data:
        return {"success": True, "cities_done": 0, "venues_added": 0, "waf_blocked": False, "finished": True}

    cities_done = 0
    venues_added = 0
    waf_blocked = False

    for i, city in enumerate(cities.data):
        city_id = city["id"]
        city_name = city["city"]
        state = city["state"]

        logger.info(f"  [{i+1}/{len(cities.data)}] {city_name}, {state} ({city['entries']} expected)")
        sb.table("city_queue").update({"trigger_status": "running"}).eq("id", city_id).execute()

        start = time.time()
        try:
            venues = scraper.scrape_city(city["url"])
            duration = int(time.time() - start)

            if not venues:
                logger.warning(f"  0 venues — WAF block likely")
                sb.table("city_queue").update({
                    "trigger_status": "pending",
                    "error_message": "0 venues, WAF suspected",
                }).eq("id", city_id).execute()
                waf_blocked = True
                break

            count = upsert_venues(venues)
            logger.info(f"  {count} venues in {duration}s")

            sb.table("city_queue").update({
                "trigger_status": "completed",
                "restaurants_scraped": count,
            }).eq("id", city_id).execute()

            cities_done += 1
            venues_added += count

        except RuntimeError as e:
            if "WAF_BLOCKED" in str(e):
                logger.warning(f"  WAF BLOCKED — stopping batch")
                sb.table("city_queue").update({
                    "trigger_status": "pending",
                    "error_message": str(e)[:500],
                }).eq("id", city_id).execute()
                waf_blocked = True
                break
            raise

        except Exception as e:
            logger.error(f"  Error: {e}")
            sb.table("city_queue").update({
                "trigger_status": "error",
                "error_message": str(e)[:500],
            }).eq("id", city_id).execute()
            # Continue to next city on non-WAF errors
            continue

        # Delay between cities
        if i < len(cities.data) - 1:
            time.sleep(DELAY_BETWEEN_CITIES)

    return {
        "success": True,
        "cities_done": cities_done,
        "venues_added": venues_added,
        "waf_blocked": waf_blocked,
        "finished": False,
    }


def run(batch_size: int = 10, max_hours: float = 0):
    """Main loop: scrape batches with adaptive cooldown."""
    sb = get_supabase()
    cooldown = MIN_COOLDOWN
    start_time = time.time()
    total_cities = 0
    total_venues = 0
    batch_num = 0
    consecutive_waf = 0

    stats = get_stats(sb)
    logger.info(f"Starting auto_scraper: {stats['completed']} cities done, "
                f"{stats['pending']} pending, {stats['restaurants']} restaurants")

    with PlaywrightScraper(headless=True, max_pages=50) as scraper:
        while True:
            # Check max runtime
            elapsed_hours = (time.time() - start_time) / 3600
            if max_hours > 0 and elapsed_hours >= max_hours:
                logger.info(f"Max runtime of {max_hours}h reached. Stopping.")
                break

            batch_num += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"BATCH {batch_num} | cooldown={cooldown}s | "
                        f"total: {total_cities} cities, {total_venues} venues | "
                        f"elapsed: {elapsed_hours:.1f}h")
            logger.info(f"{'='*60}")

            result = scrape_batch(scraper, sb, batch_size)

            if result.get("finished"):
                logger.info("All cities done!")
                break

            total_cities += result["cities_done"]
            total_venues += result["venues_added"]

            if result["waf_blocked"]:
                consecutive_waf += 1
                # Increase cooldown
                cooldown = min(cooldown + COOLDOWN_STEP * consecutive_waf, MAX_COOLDOWN)
                logger.info(f"WAF blocked (streak={consecutive_waf}). "
                            f"Increasing cooldown to {cooldown}s")
            else:
                consecutive_waf = 0
                # Decrease cooldown on full success
                cooldown = max(cooldown - COOLDOWN_DECAY, MIN_COOLDOWN)
                logger.info(f"Batch OK ({result['cities_done']} cities, "
                            f"{result['venues_added']} venues). "
                            f"Cooldown now {cooldown}s")

            # Log progress periodically
            if batch_num % 10 == 0:
                stats = get_stats(sb)
                logger.info(f"\n*** PROGRESS: {stats['completed']} cities, "
                            f"{stats['restaurants']} restaurants, "
                            f"{stats['pending']} pending ***\n")

            logger.info(f"Sleeping {cooldown}s before next batch...")
            time.sleep(cooldown)

    # Final stats
    stats = get_stats(sb)
    logger.info(f"\n{'='*60}")
    logger.info(f"DONE: {stats['completed']} cities, {stats['restaurants']} restaurants")
    logger.info(f"This session: +{total_cities} cities, +{total_venues} venues in {batch_num} batches")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous HappyCow scraper")
    parser.add_argument("--batch-size", type=int, default=10, help="Cities per batch (default: 10)")
    parser.add_argument("--max-hours", type=float, default=0, help="Max runtime in hours (0=unlimited)")
    args = parser.parse_args()

    run(batch_size=args.batch_size, max_hours=args.max_hours)
