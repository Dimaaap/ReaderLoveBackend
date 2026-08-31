from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
AVATAR_DIR = "media/avatars"


class Settings(BaseSettings):
    templates_dir: Path = TEMPLATES_DIR
    avatar_dir: Path = AVATAR_DIR

    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(alias="JWT_ALGORITHM")

    access_token_expire_minutes: int = Field(alias="ACCESS_EXPIRED_MINUTES")
    refresh_token_expire_days: int = Field(alias="REFRESH_EXPIRED_DAYS")

    allowed_types: set[str] = {"image/png", "image/jpeg", "image/webp"}
    avatar_max_size: int = 5 * 1024 * 1024

    mail_username: str = Field(alias="MAIL_USERNAME")
    mail_password: str = Field(alias="MAIL_PASSWORD")
    mail_from: str = Field(alias="MAIL_FROM")
    mail_port: int = Field(alias="MAIL_PORT")
    mail_server: str = Field(alias="MAIL_SERVER")
    mail_starttls: bool = Field(alias="MAIL_STARTTLS")
    mail_ssl_tls: bool = Field(alias="MAIL_SSL_BF")
    use_credentials: bool = Field(alias="USE_CREDENTIALS")
    validate_certs: bool = Field(alias="VALIDATE_CERTS")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
