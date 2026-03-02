import json
import logging
import httpx
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

SEARCH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_cars",
            "description": "Параметры поиска авто в японской БД. Строковые поля — только по-японски (как в объявлениях). Цена — в рублях (макс.), пробег — в км.",
            "parameters": {
                "type": "object",
                "properties": {
                    "brand": {"type": "string", "description": "Марка по-японски (例: ＢＭＷ, トヨタ, フィアット)"},
                    "model": {"type": "string", "description": "Модель по-японски (例: 3シリーズ, プリウス, 500)"},
                    "color": {"type": "string", "description": "Цвет по-японски (例: レッド, ホワイト, ブラック)"},
                    "year_min": {"type": "integer", "description": "Минимальный год выпуска"},
                    "year_max": {"type": "integer", "description": "Максимальный год выпуска"},
                    "price_max_rub": {"type": "integer", "description": "Максимальная цена в рублях"},
                    "transmission": {"type": "string", "description": "Коробка по-японски (例: フロアMT, インパネCVT, 5AT, 8AT)"},
                    "mileage_max_km": {"type": "integer", "description": "Максимальный пробег в км"},
                    "body_type": {"type": "string", "description": "Тип кузова по-японски (例: セダン, ハッチバック, ミニバン, SUV)"},
                    "drive_type": {"type": "string", "description": "Привод по-японски (例: 2WD, 4WD, FF)"},
                    "engine_type": {"type": "string", "description": "Двигатель по-японски (例: ガソリン, ディーゼル, ハイブリッド)"},
                },
            },
        },
    }
]

SYSTEM_PROMPT_BASE = (
    "Твоя задача — перевести запрос пользователя в параметры поиска по японской базе авто. "
    "Латиницу и русский переводи на японский: марка (Suzuki→スズキ, BMW→ＢＭＷ), цвет, тип кузова, коробка, привод, двигатель — как в объявлениях. "
    "price_max_rub — в рублях, mileage_max_km — в км. Не упомянуто — не включай в JSON. "
)

CONTEXT_OPTIONS_PROMPT = (
    "Ниже списки значений из базы — чтобы поиск нашёл машины, подставляй в ответ именно эти строки "
    "(например, если пользователь написал Suzuki, укажи brand из списка марок: スズキ). Год — из диапазона year_min..year_max."
)

_client: AsyncOpenAI | None = None


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"


def _get_client() -> AsyncOpenAI | None:
    global _client
    if _client is None and settings.deepseek_api_key:
        _client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=DEEPSEEK_BASE_URL,
            http_client=httpx.AsyncClient(timeout=60.0),
        )
        logger.info("[search_parser] LLM client: DeepSeek %s model=%s", DEEPSEEK_BASE_URL, DEEPSEEK_MODEL)
    return _client


def _build_options_context(options: dict | None) -> str:
    if not options:
        return ""
    parts = [CONTEXT_OPTIONS_PROMPT]
    if options.get("brands"):
        parts.append(f"Марки (brand): {', '.join(options['brands'][:80])}")
    if options.get("body_types"):
        parts.append(f"Типы кузова (body_type): {', '.join(options['body_types'][:30])}")
    if options.get("transmissions"):
        parts.append(f"Коробки (transmission): {', '.join(options['transmissions'][:30])}")
    if options.get("colors"):
        parts.append(f"Цвета (color): {', '.join(options['colors'][:40])}")
    if options.get("drive_types"):
        parts.append(f"Привод (drive_type): {', '.join(options['drive_types'][:20])}")
    if options.get("engine_types"):
        parts.append(f"Двигатель (engine_type): {', '.join(options['engine_types'][:20])}")
    ymin, ymax = options.get("year_min"), options.get("year_max")
    if ymin is not None and ymax is not None:
        parts.append(f"Год выпуска: от {ymin} до {ymax}.")
    pmin, pmax = options.get("price_min"), options.get("price_max")
    if pmin is not None and pmax is not None:
        parts.append(f"Цена в иенах: от {pmin} до {pmax} (в ответе price_max_rub — в рублях).")
    return "\n".join(parts)


async def parse_search_query(user_text: str, options: dict | None = None) -> dict | None:
    client = _get_client()
    if not client:
        logger.warning("[search_parser] DEEPSEEK_API_KEY not set, cannot parse query %r", (user_text or "")[:80])
        return None
    text = (user_text or "").strip()
    if not text:
        return None
    context = _build_options_context(options)
    system_content = SYSTEM_PROMPT_BASE + ("\n\n" + context if context else "")
    logger.info("[search_parser] Calling DeepSeek %s for q=%r", DEEPSEEK_MODEL, text[:60])
    try:
        resp = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": text},
            ],
            tools=SEARCH_TOOLS,
            tool_choice="required",
        )
        choice = resp.choices[0]
        if choice.message.tool_calls:
            tc = choice.message.tool_calls[0]
            if tc.function.name == "search_cars":
                out = json.loads(tc.function.arguments or "{}")
                logger.info("[search_parser] LLM result for %r: %s", text[:50], out)
                return out
        logger.warning("[search_parser] No tool_calls in LLM response")
    except Exception as e:
        logger.exception("[search_parser] LLM call failed for %r: %s", text[:50], e)
    return None
