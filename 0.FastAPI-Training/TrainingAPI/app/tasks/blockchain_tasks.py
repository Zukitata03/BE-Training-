import logging
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from web3 import Web3

from ..core.blockchain_web3 import web3_with_failover
from ..core.config import get_config
from ..models.blockchain_event import BlockchainEvent
from ..models.large_transaction import LargeTransaction
from .celery_app import celery_app

config = get_config()


def _sync_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
    return url


SYNC_DATABASE_URL = _sync_database_url(config.database_url)
engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

logger = logging.getLogger(__name__)
LARGE_TX_THRESHOLD = 10**18  # example threshold (in smallest unit, e.g. wei)


def _coerce_event_data_json(raw: Any) -> dict | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    return {"raw_data": raw if isinstance(raw, str) else str(raw)}


def _store_events_sync(session: Session, chain: str, events: list[dict]) -> int:
    stored = 0
    for event in events:
        existing = session.execute(
            select(BlockchainEvent).where(
                BlockchainEvent.tx_hash == event["tx_hash"],
                BlockchainEvent.block_number == event["block_number"],
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        session.add(
            BlockchainEvent(
                chain=chain,
                contract_address=event["contract_address"],
                event_name=event.get("event_name", "Unknown"),
                block_number=event["block_number"],
                tx_hash=event["tx_hash"],
                data=_coerce_event_data_json(event.get("data")),
            )
        )
        stored += 1
    session.commit()
    return stored


def _format_log_row(log) -> dict:
    raw = dict(log)
    addr = raw["address"]
    if isinstance(addr, str):
        contract_address = Web3.to_checksum_address(addr)
    elif isinstance(addr, (bytes, bytearray)):
        contract_address = Web3.to_checksum_address(addr)
    else:
        contract_address = Web3.to_checksum_address(
            addr.hex() if hasattr(addr, "hex") else addr
        )
    txh = raw["transactionHash"]
    tx_hash = txh.hex() if hasattr(txh, "hex") else str(txh)
    bn = raw["blockNumber"]
    block_number = int(bn)
    data = raw.get("data")
    data_out: str | dict | None
    if data is None:
        data_out = None
    elif hasattr(data, "hex"):
        data_out = data.hex()
    else:
        data_out = str(data)
    return {
        "contract_address": contract_address,
        "event_name": "Unknown",
        "block_number": block_number,
        "tx_hash": tx_hash,
        "data": data_out,
    }


@celery_app.task(bind=True, max_retries=5, default_retry_delay=30)
def poll_events(self):
    session: Session = SessionLocal()
    try:

        def _poll(w3: Web3) -> list:
            return w3.eth.get_logs({"fromBlock": "latest", "toBlock": "latest"})

        logs = web3_with_failover(_poll)
        formatted = [_format_log_row(dict(log)) for log in logs]
        if formatted:
            _store_events_sync(session, "evm", formatted)
    except Exception as exc:
        raise self.retry(exc=exc) from exc
    finally:
        session.close()


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
        raise self.retry(exc=exc) from exc
    finally:
        session.close()


def _tx_hash_str(tx) -> str:
    h = tx["hash"]
    return h.hex() if hasattr(h, "hex") else str(h)


def _addr_str(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if hasattr(val, "hex"):
        return val.hex()
    return str(val)


@celery_app.task(bind=True, max_retries=5, default_retry_delay=45)
def monitor_large_transactions(self, min_value_eth: float = 10.0) -> int:
    """Scan the latest 100 blocks for high-value native transfers and persist them."""
    session: Session = SessionLocal()
    try:
        min_wei = Web3.to_wei(min_value_eth, "ether")

        def _run(w3: Web3) -> int:
            latest = w3.eth.block_number
            start = max(0, latest - 99)
            inserted = 0
            for bn in range(start, latest + 1):
                block = w3.eth.get_block(bn, full_transactions=True)
                for tx in block.transactions:
                    if tx["value"] < min_wei:
                        continue
                    tx_hash = _tx_hash_str(tx)
                    exists = session.execute(
                        select(LargeTransaction).where(
                            LargeTransaction.tx_hash == tx_hash
                        )
                    ).scalar_one_or_none()
                    if exists is not None:
                        continue
                    value_eth = float(Web3.from_wei(tx["value"], "ether"))
                    session.add(
                        LargeTransaction(
                            tx_hash=tx_hash,
                            from_address=_addr_str(tx["from"]) or "",
                            to_address=_addr_str(tx.get("to")),
                            value_eth=value_eth,
                            block_number=int(block["number"]),
                        )
                    )
                    inserted += 1
            session.commit()
            return inserted

        return web3_with_failover(_run)
    except Exception as exc:
        session.rollback()
        raise self.retry(exc=exc) from exc
    finally:
        session.close()
