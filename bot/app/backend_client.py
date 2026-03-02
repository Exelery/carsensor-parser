import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def parse_query(q: str) -> dict | None:
    """Единая механика с админкой: парсинг запроса через LLM на бэкенде."""
    if not settings.backend_url or not settings.internal_api_key:
        return None
    url = f"{settings.backend_url.rstrip('/')}/api/cars/parse-query"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                url,
                json={"q": q},
                headers={"X-Internal-API-Key": settings.internal_api_key},
            )
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, dict) and data else None
    except Exception as e:
        logger.warning("Backend parse_query failed: %s", e)
        return None


async def search_cars(
    brand: str | None = None,
    model: str | None = None,
    color: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    price_max: int | None = None,
    transmission: str | None = None,
    mileage_max_km: int | None = None,
    body_type: str | None = None,
    drive_type: str | None = None,
    engine_type: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Поиск авто через API бэкенда (единая логика с админкой). Цена в иенах."""
    if not settings.backend_url or not settings.internal_api_key:
        return []
    params: dict[str, Any] = {"limit": limit, "sort_by": "price", "order": "asc"}
    if brand:
        params["brand"] = brand
    if model:
        params["model"] = model
    if color:
        params["color"] = color
    if year_min is not None:
        params["year_min"] = year_min
    if year_max is not None:
        params["year_max"] = year_max
    if price_max is not None:
        params["price_max"] = price_max
    if transmission:
        params["transmission"] = transmission
    if mileage_max_km is not None:
        params["mileage_max_km"] = mileage_max_km
    if body_type:
        params["body_type"] = body_type
    if drive_type:
        params["drive_type"] = drive_type
    if engine_type:
        params["engine_type"] = engine_type
    url = f"{settings.backend_url.rstrip('/')}/api/cars"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                url,
                params=params,
                headers={"X-Internal-API-Key": settings.internal_api_key},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.warning("Backend search_cars failed: %s", e)
        return []


async def get_rates() -> float:
    """Курс JPY→RUB через API бэкенда. При ошибке — 0.6."""
    if not settings.backend_url or not settings.internal_api_key:
        return 0.6
    url = f"{settings.backend_url.rstrip('/')}/api/rates"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                url,
                headers={"X-Internal-API-Key": settings.internal_api_key},
            )
            r.raise_for_status()
            data = r.json()
            return float(data.get("jpy_rub", 0.6))
    except Exception as e:
        logger.warning("Backend get_rates failed: %s", e)
        return 0.6
