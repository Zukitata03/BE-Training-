import logging
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import get_config
from ..models.blockchain_event import BlockchainEvent
from ..services.blockchain_service import BlockchainService
from .celery_app import celery_app

config = get_config()

SYNC_DATABASE_URL = config.database_url.replace("postgresql+asyncpg://", "postgresql://")
engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def poll_events(self):
    session: Session = SessionLocal()
    try:
        service = BlockchainService(session)
        events = service.w3.eth.get_logs({
            "fromBlock": "latest",
            "toBlock": "latest",
        })
        formatted = []
        for log in events:
            formatted.append({
                "contract_address": log["address"],
                "event_name": "Unknown",
                "block_number": log["blockNumber"],
                "tx_hash": log["transactionHash"].hex(),
                "data": log.get("data", ""),
            })
        if formatted:
            import asyncio
            asyncio.run(service.store_events(chain="evm", events=formatted))
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        session.close()


logger = logging.getLogger(__name__)
LARGE_TX_THRESHOLD = 10**18  # example threshold (in smallest unit, e.g. wei)


def _extract_amount(data: Any) -> float | None:
    if data is None:
        return None
    if isinstance(data, dict):
        value = data.get("amount") or data.get("value")
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if isinstance(data, str):
        try:
            if data.startswith("0x"):
                return float(int(data, 16))
            return float(data)
        except (ValueError, TypeError):
            return None
    return None


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def notify_large_transactions(self, limit: int = 100) -> int:
    """Scan recent blockchain events and log a notification for large transactions."""
    session: Session = SessionLocal()
    try:
        stmt = (
            select(BlockchainEvent)
            .order_by(BlockchainEvent.block_number.desc())
            .limit(limit)
        )
        result = session.execute(stmt)
        events = list(result.scalars().all())

        notified = 0
        for event in events:
            amount = _extract_amount(event.data)
            if amount is not None and amount >= LARGE_TX_THRESHOLD:
                logger.info(
                    "Large transaction detected: chain=%s tx_hash=%s amount=%s",
                    event.chain,
                    event.tx_hash,
                    amount,
                )
                notified += 1
        return notified
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        session.close()
