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

    # Blockchain (use blockchain_rpc_urls comma-separated to rotate / failover when rate-limited)
    blockchain_rpc_url: str = "https://eth.llamarpc.com"
    blockchain_rpc_urls: str = ""
    blockchain_chain_id: int = 1
    # Cap /blockchain/index range — public RPCs reject huge eth_getLogs spans
    blockchain_max_index_block_span: int = 10_000
    blockchain_get_logs_chunk_size: int = 2_000


def get_config() -> Settings:
    return Settings()
