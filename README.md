# Сервис автообъявлений

Система сбора автомобильных объявлений (carsensor.net), админ-панель с фильтрами и Telegram-бот для поиска.

## Что работает

- **Backend (FastAPI)** — REST API: JWT-логин, список авто с фильтрами и пагинацией, парсинг поискового запроса через LLM (DeepSeek), курс JPY→RUB, опции для фильтров. Внутренний ключ `X-Internal-API-Key` для доступа бота без JWT.
- **Frontend (Next.js)** — SPA: страница входа, главная с таблицей авто, фильтры (марка, год, цена, кузов, КПП, свободный поиск с подсказкой LLM), сортировка, пагинация, отображение цены в ¥ и ₽.
- **Worker** — периодически скрапит объявления, сохраняет/обновляет в БД по `source_id`. Интервал задаётся переменной окружения.
- **Telegram-бот** — работает только через API бэкенда: пользователь пишет запрос («красная BMW до 2 млн»), бот парсит его на бэкенде, получает список авто и курс, отвечает списком с ценами в ¥ и ₽.

## Запуск

```bash
cp .env.example .env
# Заполните переменные в .env (см. ниже)
docker compose up --build
```

После запуска:

| Сервис    | URL                      |
|-----------|--------------------------|
| Frontend  | http://localhost:3000    |
| API       | http://localhost:8000     |
| API docs  | http://localhost:8000/docs |

**Логин админки:** из `.env` — `ADMIN_EMAIL` и `ADMIN_PASSWORD` (по умолчанию `admin@example.com` / `admin123`).

## Переменные окружения

| Переменная | Где | Описание |
|------------|-----|----------|
| `DATABASE_URL` | backend, worker | PostgreSQL (async URL, например `postgresql+asyncpg://postgres:postgres@db:5432/cars`) |
| `JWT_SECRET` | backend | Секрет для JWT |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | backend | Учётные данные админа при сидинге |
| `INTERNAL_API_KEY` | backend, bot | Внутренний ключ: один и тот же для бэкенда и бота |
| `DEEPSEEK_API_KEY` | backend | Ключ DeepSeek для парсинга поисковых запросов (админка + бот через API) |
| `SCRAPER_INTERVAL_SEC` | worker | Интервал между прогонами скрапера (секунды), по умолчанию 60 |
| `NEXT_PUBLIC_API_URL` | frontend | URL API для браузера (при сборке), например `http://localhost:8000` |
| `TELEGRAM_BOT_TOKEN` | bot | Токен бота Telegram |
| `BACKEND_URL` | bot | URL бэкенда, например `http://backend:8000` |

Для работы бота обязательно задать `TELEGRAM_BOT_TOKEN`, `BACKEND_URL` и `INTERNAL_API_KEY` (тот же, что в бэкенде).
