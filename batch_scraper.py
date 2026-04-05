#!/usr/bin/env python3
"""Batch runner: scrape N cities from the Supabase queue sequentially."""

import argparse
import json
import sys
import time

from playwright_scraper import (
    PlaywrightScraper,
    get_supabase_client,
    upsert_venues,
    url_to_city_path,
    logger,
)


def batch_scrape(count: int = 5):
    supabase = get_supabase_client()
    results = []

    for i in range(count):
        # Get next pending city
        result = supabase.rpc("get_next_city_to_scrape").execute()
        if not result.data:
            logger.info("No more pending cities in queue")
            break

        city = result.data[0] if isinstance(result.data, list) else result.data
        city_id = city["id"]
        city_url = city["url"]
        city_name = city.get("city", "?")
        state_name = city.get("state", "?")

        logger.info(f"[{i+1}/{count}] Scraping {city_name}, {state_name}")

        # Mark as running
        supabase.rpc(
            "update_city_status", {"city_id": city_id, "new_status": "running"}
        ).execute()

        start_time = time.time()

        try:
            with PlaywrightScraper(headless=True) as scraper:
                venues = scraper.scrape_city(city_url)

            upserted = upsert_venues(venues)
            duration = int(time.time() - start_time)

            supabase.rpc(
                "update_city_status", {"city_id": city_id, "new_status": "completed"}
            ).execute()

            city_path = city.get("full_path", url_to_city_path(city_url))
            supabase.rpc(
                "log_scraping_activity",
                {
                    "city_path_param": city_path,
                    "city_name_param": city_name,
                    "state_name_param": state_name,
                    "status_param": "completed",
                    "restaurants_found_param": upserted,
                    "pages_scraped_param": max(
                        (v.get("page_number", 1) for v in venues), default=0
                    )
                    if venues
                    else 0,
                    "duration_seconds_param": duration,
                },
            ).execute()

            r = {
                "city": city_name,
                "state": state_name,
                "venues": upserted,
                "duration": duration,
                "status": "completed",
            }
            results.append(r)
            logger.info(
                f"[{i+1}/{count}] Done: {city_name} - {upserted} venues in {duration}s"
            )

        except Exception as e:
            duration = int(time.time() - start_time)
            error_msg = str(e)[:500]
            logger.error(f"[{i+1}/{count}] Failed: {city_name} - {error_msg}")

            # If WAF blocked, reset city to pending (not an error) and stop batch
            if "WAF_BLOCKED" in error_msg:
                supabase.rpc(
                    "update_city_status",
                    {"city_id": city_id, "new_status": "pending"},
                ).execute()
                results.append(
                    {
                        "city": city_name,
                        "state": state_name,
                        "status": "waf_blocked",
                        "duration": duration,
                    }
                )
                logger.warning("WAF block detected — stopping batch to avoid further blocking")
                break
            else:
                supabase.rpc(
                    "update_city_status",
                    {"city_id": city_id, "new_status": "error", "error_msg": error_msg},
                ).execute()

            results.append(
                {
                    "city": city_name,
                    "state": state_name,
                    "status": "error",
                    "error": error_msg,
                    "duration": duration,
                }
            )

        # Brief pause between cities to avoid detection
        if i < count - 1:
            time.sleep(5)

    # Summary
    completed = [r for r in results if r["status"] == "completed"]
    failed = [r for r in results if r["status"] == "error"]
    total_venues = sum(r.get("venues", 0) for r in completed)

    summary = {
        "total_cities": len(results),
        "completed": len(completed),
        "failed": len(failed),
        "total_venues_upserted": total_venues,
        "results": results,
    }

    print(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch scrape cities from queue")
    parser.add_argument(
        "-n", "--count", type=int, default=5, help="Number of cities to scrape"
    )
    args = parser.parse_args()
    batch_scrape(args.count)
