#!/usr/bin/env python3
"""
HappyCow Playwright Scraper

Replaces the broken AJAX scraper. Uses a headless browser to bypass
Incapsula WAF and extract venue data from JS-rendered city pages.

Usage:
    # Scrape a single city and print JSON to stdout
    python playwright_scraper.py --url "https://www.happycow.net/north_america/usa/texas/dallas/"

    # Scrape next city from Supabase queue and upsert results
    python playwright_scraper.py --from-queue

    # Scrape a city and upsert to Supabase
    python playwright_scraper.py --url "https://www.happycow.net/north_america/usa/texas/dallas/" --upsert
"""

import argparse
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Page, BrowserContext

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# JS executed in the browser to extract venue data from the rendered DOM
EXTRACTION_JS = """
() => {
    const venues = document.querySelectorAll('.venue-list-item');
    if (!venues || venues.length === 0) return { venues: [], pagination: null };

    const results = [];
    venues.forEach(venue => {
        // Name
        const nameEl = venue.querySelector('[data-analytics="listing-card-title"]');

        // Detail URL from the listing card link
        const linkEl = venue.querySelector('a[data-analytics="listing-card"]');
        const detailUrl = linkEl ? linkEl.getAttribute('href') : null;

        // Address from the directions link
        const addrEl = venue.querySelector('a[data-analytics="listing-directions"]');
        const address = addrEl ? addrEl.textContent.trim() : null;

        // Coordinates from Google Maps link
        let lat = null, lng = null;
        const mapsEl = venue.querySelector('a[href*="google.com/maps"]');
        if (mapsEl) {
            const href = mapsEl.getAttribute('href') || '';
            const m = href.match(/[?&]q=(-?[\\d.]+),(-?[\\d.]+)/) || href.match(/@(-?[\\d.]+),(-?[\\d.]+)/);
            if (m) { lat = parseFloat(m[1]); lng = parseFloat(m[2]); }
        }

        // Rating and review count from first <li> in the stats list
        let rating = null, reviewCount = null;
        const firstLi = venue.querySelector('ul li');
        if (firstLi) {
            const divs = firstLi.querySelectorAll('div');
            for (const d of divs) {
                const t = d.textContent.trim();
                // Rating is like "5.0" or "4.5"
                if (!rating && /^\\d+\\.\\d$/.test(t)) {
                    rating = parseFloat(t);
                }
                // Review count is like "(25)"
                const rcm = t.match(/^\\((\\d+)\\)$/);
                if (rcm) reviewCount = parseInt(rcm[1]);
            }
        }

        // Phone from tel: link
        const phoneEl = venue.querySelector('a[href^="tel:"]');
        const phone = phoneEl ? phoneEl.textContent.trim() : null;

        // Price range: count SVGs inside span.price-range (each SVG = one $)
        let priceRange = null;
        const priceSpan = venue.querySelector('span.price-range');
        if (priceSpan) {
            const svgCount = priceSpan.querySelectorAll('svg').length;
            if (svgCount > 0) priceRange = '$'.repeat(svgCount);
        }

        // Cuisine tags from the line-clamp-2 text-sm div
        const cuisineTags = [];
        const cuisineDiv = venue.querySelector('div.line-clamp-2.text-sm, div[class*="line-clamp-2"][class*="text-sm"]');
        if (cuisineDiv) {
            cuisineDiv.textContent.split(',').forEach(t => {
                t = t.trim();
                if (t) cuisineTags.push(t);
            });
        }

        // Description from the paragraph after cuisine
        let description = null;
        const descEl = venue.querySelector('p.text-gray-800.text-base.font-normal.mt-2.line-clamp-3');
        if (descEl) description = descEl.textContent.trim();

        // Category label (e.g. "Vegan Restaurant")
        const catEl = venue.querySelector('.category-label span');
        const category = catEl ? catEl.textContent.trim().replace(/\\s+/g, ' ') : null;

        // Open/closed status
        const hoursEl = venue.querySelector('.venue-hours-text');
        const hoursStatus = hoursEl ? hoursEl.textContent.trim() : null;

        // Image
        const imgEl = venue.querySelector('img.card-listing-image');

        results.push({
            venue_id: venue.getAttribute('data-id') || null,
            name: nameEl ? nameEl.textContent.trim() : null,
            type: venue.getAttribute('data-type') || null,
            rating: rating,
            review_count: reviewCount,
            address: address,
            latitude: lat,
            longitude: lng,
            phone: phone,
            website: null,
            cuisine_tags: cuisineTags,
            price_range: priceRange,
            features: [],
            category: category,
            description: description,
            hours_status: hoursStatus,
            detail_url: detailUrl,
            image_url: imgEl ? (imgEl.getAttribute('src') || imgEl.getAttribute('data-src')) : null,
            is_partner: venue.getAttribute('data-partner') === '1',
        });
    });

    // Pagination info
    const pagLinks = document.querySelectorAll('.pagination-link');
    let maxPage = 1;
    pagLinks.forEach(el => {
        const p = parseInt(el.getAttribute('data-page'));
        if (p && p > maxPage) maxPage = p;
    });
    const activePage = document.querySelector('.pagination-link.active, .pagination-link[aria-current]');
    const currentPage = activePage ? parseInt(activePage.getAttribute('data-page') || '1') : 1;

    return {
        venues: results,
        pagination: { currentPage, maxPage, hasMore: currentPage < maxPage }
    };
}
"""


def url_to_city_path(url: str) -> str:
    """Extract the city path from a HappyCow URL.

    e.g. https://www.happycow.net/north_america/usa/texas/dallas/
         -> north_america/usa/texas/dallas
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    return path


def random_delay(min_sec: float = 3.0, max_sec: float = 8.0):
    """Sleep for a random duration to mimic human browsing."""
    delay = random.uniform(min_sec, max_sec)
    logger.debug(f"Sleeping {delay:.1f}s")
    time.sleep(delay)


class PlaywrightScraper:
    def __init__(self, headless: bool = True, max_pages: int = 20):
        self.headless = headless
        self.max_pages = max_pages
        self.pw = None
        self.browser = None
        self.context: Optional[BrowserContext] = None

    def __enter__(self):
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(headless=self.headless)
        ua = random.choice(USER_AGENTS)
        self.context = self.browser.new_context(
            user_agent=ua,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
        )
        return self

    def __exit__(self, *exc):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.pw:
            self.pw.stop()

    def _check_waf_block(self, page: Page) -> bool:
        """Check if the page is a WAF block page (Imperva/Incapsula)."""
        try:
            content = page.content()
            if "Access denied" in content and "Error 15" in content:
                logger.warning("Imperva WAF block detected (Error 15) - IP is rate-limited")
                return True
            if "incapsula" in content.lower() and "blocked" in content.lower():
                logger.warning("Incapsula WAF block detected")
                return True
        except Exception:
            pass
        return False

    def _wait_for_venues(self, page: Page, timeout_ms: int = 30000):
        """Wait until venue list items are present in the DOM."""
        try:
            page.wait_for_selector(".venue-list-item", timeout=timeout_ms)
        except Exception:
            # Venues might not exist (empty city or last page)
            logger.debug("No .venue-list-item found within timeout")

    def scrape_city(self, url: str) -> List[Dict]:
        """Scrape all pages of a HappyCow city listing."""
        city_path = url_to_city_path(url)
        logger.info(f"Scraping city: {city_path} ({url})")

        page = self.context.new_page()
        all_venues: List[Dict] = []
        current_page = 1

        try:
            # Load the initial city page
            logger.info(f"Loading page 1: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            random_delay(2, 5)

            if self._check_waf_block(page):
                raise RuntimeError("WAF_BLOCKED: IP is rate-limited by Imperva")

            self._wait_for_venues(page)

            while current_page <= self.max_pages:
                # Extract venue data from the current page
                result = page.evaluate(EXTRACTION_JS)
                venues = result.get("venues", [])
                pagination = result.get("pagination", {})

                if not venues:
                    logger.info(f"No venues found on page {current_page}, stopping")
                    break

                # Tag each venue with city metadata
                for v in venues:
                    v["city_path"] = city_path
                    v["scraped_at"] = datetime.now(timezone.utc).isoformat()
                    v["page_number"] = current_page

                all_venues.extend(venues)
                logger.info(
                    f"Page {current_page}: {len(venues)} venues "
                    f"(total: {len(all_venues)})"
                )

                # Check pagination
                has_more = pagination.get("hasMore", False)
                if not has_more:
                    logger.info("No more pages")
                    break

                # Navigate to next page via URL on the same page/tab
                # (opening a new page triggers anti-bot detection)
                current_page += 1
                random_delay(3, 8)
                base = url.rstrip("/") + "/"
                page_url = base + f"?page={current_page}"
                logger.info(f"Navigating to page {current_page}: {page_url}")
                page.goto(page_url, wait_until="domcontentloaded", timeout=60000)
                random_delay(2, 4)
                self._wait_for_venues(page)

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
        finally:
            page.close()

        logger.info(f"Scraping complete: {len(all_venues)} venues from {city_path}")
        return all_venues


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def get_supabase_client():
    """Create a Supabase client from env vars or Bitwarden."""
    try:
        from supabase import create_client
    except ImportError:
        logger.error("supabase-py not installed. Run: pip install supabase")
        sys.exit(1)

    sb_url = os.environ.get("SUPABASE_URL", "https://vzlzyckayprsnpajrxmr.supabase.co")
    sb_key = os.environ.get("SUPABASE_KEY")

    if not sb_key:
        logger.error(
            "SUPABASE_KEY not set. Export it or fetch from Bitwarden:\n"
            "  export BW_SESSION=$(bw unlock \"$BW_PASSWORD\" --raw)\n"
            "  export SUPABASE_KEY=$(bw get password 'Supabase VeganVoyage API Key')"
        )
        sys.exit(1)

    return create_client(sb_url, sb_key)


def upsert_venues(venues: List[Dict]) -> int:
    """Upsert scraped venues to the Supabase restaurants table.

    Returns number of rows upserted.
    """
    if not venues:
        return 0

    supabase = get_supabase_client()
    city_path = venues[0].get("city_path", "")

    # Derive city_name, state_name from city_path
    parts = city_path.strip("/").split("/")
    city_name = parts[-1].replace("_", " ").title() if parts else ""
    state_name = parts[-2].replace("_", " ").title() if len(parts) >= 2 else ""

    rows = []
    for v in venues:
        if not v.get("venue_id"):
            continue

        # Normalize type to match DB constraint
        vtype = (v.get("type") or "veg-options").lower()
        if vtype not in ("vegan", "vegetarian", "veg-options", "veg-friendly"):
            vtype = "veg-options"

        rows.append(
            {
                "venue_id": str(v["venue_id"]),
                "name": v.get("name") or "Unknown",
                "type": vtype,
                "rating": v.get("rating"),
                "review_count": v.get("review_count") or 0,
                "address": v.get("address"),
                "latitude": round(v["latitude"], 6) if v.get("latitude") is not None else None,
                "longitude": round(v["longitude"], 6) if v.get("longitude") is not None else None,
                "phone": v.get("phone"),
                "website": v.get("website"),
                "cuisine_tags": v.get("cuisine_tags") or [],
                "price_range": v.get("price_range"),
                "features": v.get("features") or [],
                "city_path": city_path,
                "city_name": city_name,
                "state_name": state_name,
                "scraped_at": v.get("scraped_at"),
                "page_number": v.get("page_number"),
            }
        )

    if not rows:
        return 0

    # Deduplicate by venue_id (keep last seen)
    seen = {}
    for r in rows:
        seen[r["venue_id"]] = r
    rows = list(seen.values())

    # Upsert in batches of 100
    batch_size = 100
    upserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        supabase.table("restaurants").upsert(batch, on_conflict="venue_id").execute()
        upserted += len(batch)
        logger.info(f"Upserted batch {i // batch_size + 1}: {len(batch)} rows")

    return upserted


def scrape_from_queue() -> Optional[Dict]:
    """Fetch the next city from Supabase city_queue, scrape it, and upsert results."""
    supabase = get_supabase_client()

    # Get next pending city
    result = supabase.rpc("get_next_city_to_scrape").execute()
    if not result.data:
        logger.info("No pending cities in queue")
        return None

    city = result.data[0] if isinstance(result.data, list) else result.data
    city_id = city["id"]
    city_url = city["url"]
    city_path = city["full_path"]

    logger.info(f"Queue: scraping {city['city']}, {city['state']} ({city_path})")

    # Mark as running
    supabase.rpc(
        "update_city_status", {"city_id": city_id, "new_status": "running"}
    ).execute()

    start_time = time.time()

    try:
        with PlaywrightScraper(headless=True) as scraper:
            venues = scraper.scrape_city(city_url)

        count = upsert_venues(venues)
        duration = int(time.time() - start_time)

        # Mark completed
        supabase.rpc(
            "update_city_status", {"city_id": city_id, "new_status": "completed"}
        ).execute()

        # Log activity
        supabase.rpc(
            "log_scraping_activity",
            {
                "city_path_param": city_path,
                "city_name_param": city.get("city", ""),
                "state_name_param": city.get("state", ""),
                "status_param": "completed",
                "restaurants_found_param": count,
                "pages_scraped_param": max((v.get("page_number", 1) for v in venues), default=1) if venues else 0,
                "duration_seconds_param": duration,
            },
        ).execute()

        return {
            "success": True,
            "city": city["city"],
            "state": city["state"],
            "restaurants_found": count,
            "duration_seconds": duration,
        }

    except Exception as e:
        duration = int(time.time() - start_time)
        error_msg = str(e)
        logger.error(f"Failed to scrape {city_path}: {error_msg}")

        supabase.rpc(
            "update_city_status",
            {"city_id": city_id, "new_status": "error", "error_msg": error_msg},
        ).execute()

        supabase.rpc(
            "log_scraping_activity",
            {
                "city_path_param": city_path,
                "city_name_param": city.get("city", ""),
                "state_name_param": city.get("state", ""),
                "status_param": "error",
                "error_message_param": error_msg,
                "duration_seconds_param": duration,
            },
        ).execute()

        return {"success": False, "city": city["city"], "error": error_msg}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="HappyCow Playwright Scraper")
    parser.add_argument("--url", help="HappyCow city URL to scrape")
    parser.add_argument(
        "--from-queue",
        action="store_true",
        help="Scrape next city from Supabase city_queue",
    )
    parser.add_argument(
        "--upsert",
        action="store_true",
        help="Upsert results to Supabase restaurants table",
    )
    parser.add_argument(
        "--max-pages", type=int, default=20, help="Max pages per city (default: 20)"
    )
    parser.add_argument(
        "--headed", action="store_true", help="Run browser in headed mode (debug)"
    )
    parser.add_argument(
        "--output-json", help="Write results to a JSON file"
    )

    args = parser.parse_args()

    if args.from_queue:
        result = scrape_from_queue()
        if result:
            print(json.dumps(result, default=str))
        return 0

    if not args.url:
        parser.error("Either --url or --from-queue is required")

    with PlaywrightScraper(headless=not args.headed, max_pages=args.max_pages) as scraper:
        venues = scraper.scrape_city(args.url)

    if args.upsert:
        count = upsert_venues(venues)
        logger.info(f"Upserted {count} restaurants to Supabase")

    output = {
        "success": True,
        "city_path": url_to_city_path(args.url),
        "total_venues": len(venues),
        "venues": venues,
    }

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(output, f, indent=2, default=str)
        logger.info(f"Saved to {args.output_json}")

    print(json.dumps(output, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
