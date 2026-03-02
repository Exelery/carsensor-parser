import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

from app.config import settings
from app.backend_client import parse_query, search_cars, get_rates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not (settings.telegram_bot_token and settings.telegram_bot_token.strip()):
    logger.warning("TELEGRAM_BOT_TOKEN не задан — бот не запущен. Заполните .env для работы бота.")
    sys.exit(0)

if not (settings.backend_url and settings.backend_url.strip()) or not (settings.internal_api_key and settings.internal_api_key.strip()):
    logger.warning(
        "BACKEND_URL и INTERNAL_API_KEY обязательны (бот работает только через API бэкенда). "
        "Заполните .env и убедитесь, что INTERNAL_API_KEY совпадает с ключом бэкенда."
    )
    sys.exit(0)

bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()


def format_cars(cars: list[dict], jpy_rub: float = 0.6) -> str:
    if not cars:
        return "По вашему запросу ничего не найдено."
    lines = []
    for c in cars:
        price_yen = c.get("total_price") or c.get("price") or 0
        price_rub = int(price_yen * jpy_rub) if jpy_rub > 0 else price_yen
        price_ja = f"{price_yen:,} ¥" if price_yen else "—"
        lines.append(
            f"• {c['brand']} {c['model']} ({c['year']}), {c['color']} — {price_ja} ({price_rub:,} ₽)\n  {c['link']}"
        )
    return "\n".join(lines)


@dp.message(Command("start"))
async def cmd_start(msg: Message):
    await msg.answer(
        "Напишите запрос в свободной форме, например:\n"
        "«Найди красную BMW до 2 млн» или «Toyota до 2022 года»"
    )


@dp.message(F.text)
async def on_text(msg: Message):
    text = (msg.text or "").strip()
    if not text:
        return
    params = await parse_query(text)
    if params is None:
        params = {}
    price_max_rub = params.get("price_max_rub")
    price_max_yen = None
    if price_max_rub is not None and price_max_rub > 0:
        jpy_rub = await get_rates()
        if jpy_rub > 0:
            price_max_yen = int(price_max_rub / jpy_rub)
    cars = await search_cars(
        brand=params.get("brand"),
        model=params.get("model"),
        color=params.get("color"),
        year_min=params.get("year_min"),
        year_max=params.get("year_max"),
        transmission=params.get("transmission"),
        mileage_max_km=params.get("mileage_max_km"),
        body_type=params.get("body_type"),
        drive_type=params.get("drive_type"),
        engine_type=params.get("engine_type"),
        limit=10,
        price_max=price_max_yen,
    )
    jpy_rub = await get_rates()
    reply = format_cars(cars, jpy_rub)
    await msg.answer(reply[:4000] or "Ничего не найдено.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
