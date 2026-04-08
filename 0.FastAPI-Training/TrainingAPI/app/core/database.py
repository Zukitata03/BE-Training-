"""Async SQLAlchemy engine and session management.

Engine is created lazily (not at import time) so tests can override
the database URL before the engine is first accessed.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_config

_engine = None
_session_factory = None


def get_engine():
    """Return (and lazily create) the async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_config().database_url,
            future=True,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory():
    """Return (and lazily create) the async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session.

    Usage:
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    from ..models import Base  # noqa: PLC0415

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    engine = get_engine()
    await engine.dispose()
