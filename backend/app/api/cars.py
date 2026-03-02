import logging
import re
import time
import httpx
from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.database import get_db
from app.models.car import Car
from app.models.user import User
from app.schemas.car import CarOut
from app.api.deps import get_current_user, get_current_user_or_internal
from app.services.search_parser import parse_search_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["cars"])

CBR_JSON_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
_rates_cache: dict[str, tuple[float, float]] = {}
RATES_CACHE_TTL_SEC = 3600


@router.get("/rates")
async def get_rates(_: User | None = Depends(get_current_user_or_internal)):
    now = time.time()
    if "jpy_rub" in _rates_cache:
        rate, cached_at = _rates_cache["jpy_rub"]
        if now - cached_at < RATES_CACHE_TTL_SEC:
            return {"jpy_rub": rate}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(CBR_JSON_URL)
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError):
        _rates_cache["jpy_rub"] = (0.6, now)
        return {"jpy_rub": 0.6}
    val = data.get("Valute", {}).get("JPY")
    if not val:
        _rates_cache["jpy_rub"] = (0.6, now)
        return {"jpy_rub": 0.6}
    nominal = float(val.get("Nominal", 1))
    value = float(val.get("Value", 0))
    jpy_rub = value / nominal
    _rates_cache["jpy_rub"] = (jpy_rub, now)
    return {"jpy_rub": round(jpy_rub, 6)}


def _parse_year_from_q(q: str | None) -> tuple[str | None, int | None, int | None]:
    if not q or not q.strip():
        return (q, None, None)
    text = q.strip()
    year_min_extra: int | None = None
    year_max_extra: int | None = None
    m = re.search(r"до\s+(\d{2,4})\s*(?:год(?:а|у)?)?", text, re.IGNORECASE)
    if m:
        y = int(m.group(1))
        year_max_extra = 2000 + y if y < 100 else y
        text = (text[: m.start()] + " " + text[m.end() :]).strip()
    m = re.search(r"(?:от|с)\s+(\d{2,4})\s*(?:год(?:а|у)?)?", text, re.IGNORECASE)
    if m:
        y = int(m.group(1))
        year_min_extra = 2000 + y if y < 100 else y
        text = (text[: m.start()] + " " + text[m.end() :]).strip()
    m = re.search(r"после\s+(\d{2,4})", text, re.IGNORECASE)
    if m:
        y = int(m.group(1))
        year_min_extra = 2000 + y if y < 100 else y
        text = (text[: m.start()] + " " + text[m.end() :]).strip()
    cleaned = re.sub(r"\s+", " ", text).strip() or None
    return (cleaned, year_min_extra, year_max_extra)


def _merge_parsed_into_params(
    parsed: dict,
    brand: str | None,
    model: str | None,
    color: str | None,
    year_min: int | None,
    year_max: int | None,
    body_type: str | None,
    transmission: str | None,
    mileage_max_km: int | None,
    drive_type: str | None,
    engine_type: str | None,
) -> tuple[str | None, str | None, str | None, int | None, int | None, str | None, str | None, int | None, str | None, str | None]:
    def s(v: str | None) -> str | None:
        return (v or "").strip() or None

    brand_ = s(brand) or s(parsed.get("brand"))
    model_ = s(model) or s(parsed.get("model"))
    color_ = s(color) or s(parsed.get("color"))
    ymin = year_min if year_min is not None else parsed.get("year_min")
    ymax = year_max if year_max is not None else parsed.get("year_max")
    bt = s(body_type) or s(parsed.get("body_type"))
    tr = s(transmission) or s(parsed.get("transmission"))
    mile = mileage_max_km if mileage_max_km is not None else parsed.get("mileage_max_km")
    dr = s(drive_type) or s(parsed.get("drive_type"))
    en = s(engine_type) or s(parsed.get("engine_type"))
    return brand_, model_, color_, ymin, ymax, bt, tr, mile, dr, en


def _cars_filter_query(
    brand: str | None = None,
    model: str | None = None,
    color: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    body_type: str | None = None,
    transmission: str | None = None,
    mileage_max_km: int | None = None,
    drive_type: str | None = None,
    engine_type: str | None = None,
    search: str | None = None,
):
    q = select(Car)
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.where(
            or_(
                Car.brand.ilike(term),
                Car.model.ilike(term),
                Car.color.ilike(term),
                Car.title.ilike(term),
            )
        )
    if brand and brand.strip():
        q = q.where(Car.brand.ilike(f"%{brand.strip()}%"))
    if model and model.strip():
        q = q.where(Car.model.ilike(f"%{model.strip()}%"))
    if color and color.strip():
        q = q.where(Car.color.ilike(f"%{color.strip()}%"))
    if year_min is not None:
        q = q.where(Car.year >= year_min)
    if year_max is not None:
        q = q.where(Car.year <= year_max)
    if price_min is not None:
        q = q.where(func.coalesce(Car.total_price, Car.price) >= price_min)
    if price_max is not None:
        q = q.where(func.coalesce(Car.total_price, Car.price) <= price_max)
    if body_type and body_type.strip():
        q = q.where(Car.body_type.ilike(f"%{body_type.strip()}%"))
    if transmission and transmission.strip():
        q = q.where(Car.transmission.ilike(f"%{transmission.strip()}%"))
    if mileage_max_km is not None:
        q = q.where((Car.mileage_km.is_(None)) | (Car.mileage_km <= mileage_max_km))
    if drive_type and drive_type.strip():
        q = q.where(Car.drive_type.ilike(f"%{drive_type.strip()}%"))
    if engine_type and engine_type.strip():
        q = q.where(Car.engine_type.ilike(f"%{engine_type.strip()}%"))
    return q


async def _get_filter_options(db: AsyncSession) -> dict:
    br = await db.execute(select(Car.brand).distinct().where(Car.brand.isnot(None)).order_by(Car.brand))
    bt = await db.execute(select(Car.body_type).distinct().where(Car.body_type.isnot(None)).order_by(Car.body_type))
    tr = await db.execute(select(Car.transmission).distinct().where(Car.transmission.isnot(None)).order_by(Car.transmission))
    cl = await db.execute(select(Car.color).distinct().where(Car.color.isnot(None)).order_by(Car.color))
    dr = await db.execute(select(Car.drive_type).distinct().where(Car.drive_type.isnot(None)).order_by(Car.drive_type))
    en = await db.execute(select(Car.engine_type).distinct().where(Car.engine_type.isnot(None)).order_by(Car.engine_type))
    bounds = await db.execute(
        select(
            func.min(Car.year).label("year_min"),
            func.max(Car.year).label("year_max"),
            func.min(func.coalesce(Car.total_price, Car.price)).label("price_min"),
            func.max(func.coalesce(Car.total_price, Car.price)).label("price_max"),
        )
    )
    b = bounds.one()
    return {
        "brands": [row[0] for row in br.all() if row[0]],
        "body_types": [row[0] for row in bt.all() if row[0]],
        "transmissions": [row[0] for row in tr.all() if row[0]],
        "colors": [row[0] for row in cl.all() if row[0]],
        "drive_types": [row[0] for row in dr.all() if row[0]],
        "engine_types": [row[0] for row in en.all() if row[0]],
        "year_min": b.year_min or 1990,
        "year_max": b.year_max or 2030,
        "price_min": b.price_min or 0,
        "price_max": b.price_max or 0,
    }


@router.get("/cars/filter-options")
async def cars_filter_options(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    opts = await _get_filter_options(db)
    return {k: opts[k] for k in ("brands", "body_types", "transmissions", "year_min", "year_max", "price_min", "price_max")}


@router.post("/cars/parse-query")
async def cars_parse_query(
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    _: User | None = Depends(get_current_user_or_internal),
):
    q = (body.get("q") or "").strip()
    if not q:
        return {}
    logger.info("[parse-query] q=%r", q)
    options = await _get_filter_options(db)
    result = await parse_search_query(q, options=options)
    logger.info("[parse-query] parsed=%s", result)
    return result or {}


@router.get("/cars/count")
async def cars_count(
    db: AsyncSession = Depends(get_db),
    _: User | None = Depends(get_current_user_or_internal),
    brand: str | None = Query(None),
    model: str | None = Query(None),
    color: str | None = Query(None),
    year_min: int | None = Query(None, ge=1990, le=2030),
    year_max: int | None = Query(None, ge=1990, le=2030),
    price_min: int | None = Query(None, ge=0),
    price_max: int | None = Query(None, ge=0),
    body_type: str | None = Query(None),
    transmission: str | None = Query(None),
    mileage_max_km: int | None = Query(None, ge=0),
    drive_type: str | None = Query(None),
    engine_type: str | None = Query(None),
    q: str | None = Query(None),
):
    cleaned_q, year_min_from_q, year_max_from_q = _parse_year_from_q(q)
    year_min_used = year_min if year_min is not None else year_min_from_q
    year_max_used = year_max if year_max is not None else year_max_from_q
    search_used = cleaned_q
    brand_used, model_used = brand, model
    color_used, body_used, tr_used = color, body_type, transmission
    mile_used, dr_used, en_used = mileage_max_km, drive_type, engine_type

    logger.info("[cars/count] q=%r cleaned_q=%r year_from_q=(%s,%s)", q, cleaned_q, year_min_from_q, year_max_from_q)

    if cleaned_q and cleaned_q.strip():
        options = await _get_filter_options(db)
        parsed = await parse_search_query(cleaned_q, options=options)
        logger.info("[cars/count] LLM parsed=%s", parsed)
        if parsed:
            brand_used, model_used, color_used, year_min_used, year_max_used, body_used, tr_used, mile_used, dr_used, en_used = _merge_parsed_into_params(
                parsed, brand, model, color, year_min_used, year_max_used, body_type, transmission, mileage_max_km, drive_type, engine_type
            )
            search_used = None
            logger.info("[cars/count] after merge brand_used=%r search_used=%s", brand_used, search_used)

    query = _cars_filter_query(
        brand_used, model_used, color_used, year_min_used, year_max_used,
        price_min, price_max, body_used, tr_used,
        mile_used, dr_used, en_used, search=search_used,
    )
    subq = query.subquery()
    result = await db.execute(select(func.count()).select_from(subq))
    total = result.scalar() or 0
    logger.info("[cars/count] total=%s", total)
    return {"total": total}


SORT_COLUMNS = {"id", "brand", "model", "year", "price", "total_price", "updated_at", "mileage_km", "body_type"}


@router.get("/cars", response_model=list[CarOut])
async def list_cars(
    db: AsyncSession = Depends(get_db),
    _: User | None = Depends(get_current_user_or_internal),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    sort_by: str = Query("updated_at"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    brand: str | None = Query(None),
    model: str | None = Query(None),
    color: str | None = Query(None),
    year_min: int | None = Query(None, ge=1990, le=2030),
    year_max: int | None = Query(None, ge=1990, le=2030),
    price_min: int | None = Query(None, ge=0),
    price_max: int | None = Query(None, ge=0),
    body_type: str | None = Query(None),
    transmission: str | None = Query(None),
    mileage_max_km: int | None = Query(None, ge=0),
    drive_type: str | None = Query(None),
    engine_type: str | None = Query(None),
    q: str | None = Query(None),
):
    cleaned_q, year_min_from_q, year_max_from_q = _parse_year_from_q(q)
    year_min_used = year_min if year_min is not None else year_min_from_q
    year_max_used = year_max if year_max is not None else year_max_from_q
    search_used = cleaned_q
    brand_used, model_used = brand, model
    color_used, body_used, tr_used = color, body_type, transmission
    mile_used, dr_used, en_used = mileage_max_km, drive_type, engine_type

    logger.info("[cars] q=%r cleaned_q=%r year_from_q=(%s,%s)", q, cleaned_q, year_min_from_q, year_max_from_q)

    if cleaned_q and cleaned_q.strip():
        options = await _get_filter_options(db)
        parsed = await parse_search_query(cleaned_q, options=options)
        logger.info("[cars] LLM parsed=%s", parsed)
        if parsed:
            brand_used, model_used, color_used, year_min_used, year_max_used, body_used, tr_used, mile_used, dr_used, en_used = _merge_parsed_into_params(
                parsed, brand, model, color, year_min_used, year_max_used, body_type, transmission, mileage_max_km, drive_type, engine_type
            )
            search_used = None
            logger.info("[cars] after merge brand_used=%r search_used=%s", brand_used, search_used)
        else:
            logger.warning("[cars] LLM returned nothing, falling back to text search search_used=%r", search_used)

    col = sort_by if sort_by in SORT_COLUMNS else "updated_at"
    order_by = getattr(Car, col).desc() if order == "desc" else getattr(Car, col).asc()
    query = _cars_filter_query(
        brand_used, model_used, color_used, year_min_used, year_max_used,
        price_min, price_max, body_used, tr_used,
        mile_used, dr_used, en_used, search=search_used,
    )
    query = query.order_by(order_by).offset(skip).limit(limit)
    result = await db.execute(query)
    cars = result.scalars().all()
    logger.info("[cars] returned %s cars", len(cars))
    return [CarOut.model_validate(c) for c in cars]
