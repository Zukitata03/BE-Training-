from __future__ import annotations

from collections import Counter
from typing import Any

from .celery_app import celery_app
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import get_config
from ..models.book import Book

config = get_config()


def _get_sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://")
    if database_url.startswith("sqlite+aiosqlite://"):
        return database_url.replace("sqlite+aiosqlite://", "sqlite://")
    return database_url


SYNC_DATABASE_URL = _get_sync_database_url(config.database_url)
engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def analyze_user_activity(self, user_id: int) -> dict[str, Any]:
    session: Session = SessionLocal()
    try:
        books = list(session.execute(select(Book).where(Book.owner_id == user_id)).scalars().all())

        total_books = len(books)
        title_lengths = [len(b.title) for b in books]
        avg_title_length = (sum(title_lengths) / total_books) if total_books > 0 else 0.0

        authors = [b.author for b in books]
        most_common_author: str | None = None
        if authors:
            counts = Counter(authors)
            max_count = max(counts.values())
            most_common_author = sorted([a for a, c in counts.items() if c == max_count])[0]

        return {
            "user_id": user_id,
            "total_books": total_books,
            "avg_title_length": avg_title_length,
            "most_common_author": most_common_author,
        }
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        session.close()

