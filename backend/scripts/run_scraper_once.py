import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.services.scraper import fetch_cars
from app.services.sync_cars import upsert_cars


async def main():
    print("Fetching from carsensor.net...")
    items = fetch_cars()
    print(f"Parsed {len(items)} items")
    if not items:
        return
    async with AsyncSessionLocal() as db:
        await upsert_cars(db, items)
    print(f"Upserted {len(items)} cars")


if __name__ == "__main__":
    asyncio.run(main())
