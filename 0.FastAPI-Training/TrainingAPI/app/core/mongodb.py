"""MongoDB client setup (async)."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient

from .config import get_config


def get_mongo_client() -> AsyncIOMotorClient:
    cfg = get_config()
    return AsyncIOMotorClient(cfg.mongo_url)
