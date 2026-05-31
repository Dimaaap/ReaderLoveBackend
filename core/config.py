from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = "postgresql+asyncpg://postgres:987456321@localhost/rork"
    db_echo: bool = False


settings = Settings()
