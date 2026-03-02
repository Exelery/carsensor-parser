from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    backend_url: str = ""
    internal_api_key: str = ""

    class Config:
        env_file = ".env"
        env_prefix = ""


settings = Settings()
