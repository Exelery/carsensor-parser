import asyncio
import os
import sys

print("Worker starting...", flush=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.scraper import fetch_cars_pages
from app.services.sync_cars import upsert_cars

INTERVAL_SEC = int(os.getenv("SCRAPER_INTERVAL_SEC", "60"))


async def run_once():
    print("Fetching cars...", flush=True)
    total = 0
    for page_items in fetch_cars_pages(fetch_details=True, delay_between_details=1.0):
        if not page_items:
            continue
        async with AsyncSessionLocal() as db:
            await upsert_cars(db, page_items)
        total += len(page_items)
        print(f"Upserted page batch: {len(page_items)} cars (total this run: {total})", flush=True)
    print(f"Run complete: {total} cars upserted", flush=True)


async def main():
    while True:
        try:
            await run_once()
        except Exception as e:
            print(f"Scraper error: {e}", flush=True)
            import traceback
            traceback.print_exc()
        print(f"Sleeping {INTERVAL_SEC}s until next run...", flush=True)
        await asyncio.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    asyncio.run(main())
