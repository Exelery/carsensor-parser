from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.car import Car
from app.services.scraper import CarItem


async def upsert_cars(db: AsyncSession, items: list[CarItem]) -> None:
    for item in items:
        sid = item.source_id()
        result = await db.execute(select(Car).where(Car.source_id == sid))
        existing = result.scalar_one_or_none()
        now = datetime.utcnow()
        if existing:
            existing.brand = item.brand
            existing.model = item.model
            existing.year = item.year
            existing.price = item.price
            existing.color = item.color
            existing.link = item.link
            existing.total_price = item.total_price
            existing.transmission = item.transmission
            existing.title = item.title
            existing.mileage_km = item.mileage_km
            existing.mileage_display = item.mileage_display
            existing.body_type = item.body_type
            existing.drive_type = item.drive_type
            existing.steering = item.steering
            existing.displacement = item.displacement
            existing.seating_capacity = item.seating_capacity
            existing.engine_type = item.engine_type
            existing.door_count = item.door_count
            existing.updated_at = now
        else:
            db.add(
                Car(
                    source_id=sid,
                    brand=item.brand,
                    model=item.model,
                    year=item.year,
                    price=item.price,
                    color=item.color,
                    link=item.link,
                    total_price=item.total_price,
                    transmission=item.transmission,
                    title=item.title,
                    mileage_km=item.mileage_km,
                    mileage_display=item.mileage_display,
                    body_type=item.body_type,
                    drive_type=item.drive_type,
                    steering=item.steering,
                    displacement=item.displacement,
                    seating_capacity=item.seating_capacity,
                    engine_type=item.engine_type,
                    door_count=item.door_count,
                )
            )
    await db.commit()
