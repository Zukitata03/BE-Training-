"""Application configuration using pydantic-settings v2."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./test.db"
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db_name: str = "training_db"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "CHANGE_ME_IN_PROD"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Blockchain
    blockchain_rpc_url: str = "https://bsc-dataseed.binance.org"
    blockchain_chain_id: int = 56


def get_config() -> Settings:
    return Settings()
