from __future__ import annotations

from typing import Any

from hexbytes import HexBytes
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3._utils.events import get_event_data

from ..core.config import get_config
from ..core.blockchain_web3 import web3_with_failover
from ..models.blockchain_event import BlockchainEvent
from ..models.large_transaction import LargeTransaction


class BlockchainService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _normalize_log_for_decode(log: dict[str, Any]) -> dict[str, Any]:
        """Ensure topics/data types suit web3's get_event_data."""
        out = dict(log)
        topics = out.get("topics")
        if topics is not None:
            out["topics"] = tuple(
                HexBytes(t) if isinstance(t, str) else t for t in topics
            )
        data = out.get("data")
        if isinstance(data, str) and data.startswith("0x"):
            out["data"] = HexBytes(data)
        return out

    @staticmethod
    def decode_event(log: dict, abi: list) -> dict:
        """Decode a raw eth_getLogs entry using contract ABI; returns event name and named args."""
        w3 = Web3()
        normalized = BlockchainService._normalize_log_for_decode(log)
        event_abis = [item for item in abi if item.get("type") == "event"]
        last_error: Exception | None = None
        for event_abi in event_abis:
            try:
                decoded = get_event_data(w3.codec, event_abi, normalized)
                return {
                    "event": decoded["event"],
                    "args": dict(decoded["args"]),
                }
            except Exception as exc:
                last_error = exc
                continue
        msg = "Log does not match any event in the provided ABI"
        if last_error is not None:
            msg = f"{msg}: {last_error}"
        raise ValueError(msg)

    def _coerce_event_data_for_json(self, raw: Any) -> dict | None:
        """JSON column expects a mapping; raw log data is often a hex string."""
        if raw is None:
            return None
        if isinstance(raw, dict):
            return raw
        return {"raw_data": raw if isinstance(raw, str) else str(raw)}

    async def fetch_events(
        self,
        contract_address: str,
        from_block: int = 0,
        to_block: int | None = None,
    ) -> list[dict]:
        cfg = get_config()
        max_span = max(1, cfg.blockchain_max_index_block_span)
        chunk_size = max(100, cfg.blockchain_get_logs_chunk_size)
        checksum = Web3.to_checksum_address(contract_address)

        def _fetch_chunked(w3: Web3) -> list:
            latest = int(w3.eth.block_number)
            resolved_end = int(to_block) if to_block is not None else latest
            resolved_end = min(resolved_end, latest)
            start = int(from_block)

            if start > resolved_end:
                raise ValueError(
                    f"from_block ({start}) is above the resolved to_block ({resolved_end}) "
                    f"or chain head ({latest}). Check the network or pass a valid to_block."
                )

            span = resolved_end - start + 1
            if span > max_span:
                raise ValueError(
                    f"Block range is {span} blocks; maximum allowed is {max_span} per request "
                    f"(set BLOCKCHAIN_MAX_INDEX_BLOCK_SPAN or pass a smaller interval via to_block). "
                    f"Example: from_block={start}&to_block={start + max_span - 1}"
                )

            all_logs: list = []
            cur = start
            while cur <= resolved_end:
                chunk_end = min(cur + chunk_size - 1, resolved_end)
                part = w3.eth.get_logs(
                    {
                        "address": checksum,
                        "fromBlock": cur,
                        "toBlock": chunk_end,
                    }
                )
                all_logs.extend(part)
                cur = chunk_end + 1
            return all_logs

        logs = web3_with_failover(_fetch_chunked, timeout=60)
        out: list[dict] = []
        for log in logs:
            txh = log["transactionHash"]
            tx_hash = txh.hex() if hasattr(txh, "hex") else str(txh)
            bn = log["blockNumber"]
            block_number = int(bn)
            raw_data = log.get("data")
            if raw_data is None:
                data_str = None
            elif hasattr(raw_data, "hex"):
                data_str = raw_data.hex()
            else:
                data_str = str(raw_data)
            out.append({
                "block_number": block_number,
                "tx_hash": tx_hash,
                "data": data_str,
            })
        return out

    async def store_events(self, chain: str, events: list[dict]) -> int:
        stored = 0
        for event in events:
            existing = await self.db.execute(
                select(BlockchainEvent).where(
                    BlockchainEvent.tx_hash == event["tx_hash"],
                    BlockchainEvent.block_number == event["block_number"],
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue
            db_event = BlockchainEvent(
                chain=chain,
                contract_address=Web3.to_checksum_address(event["contract_address"]),
                event_name=event.get("event_name", "Unknown"),
                block_number=event["block_number"],
                tx_hash=event["tx_hash"],
                data=self._coerce_event_data_for_json(event.get("data")),
            )
            self.db.add(db_event)
            stored += 1
        await self.db.flush()
        return stored

    async def get_indexed_events_page(
        self, page: int, page_size: int
    ) -> tuple[list[BlockchainEvent], int]:
        offset = (page - 1) * page_size
        count_stmt = select(func.count()).select_from(BlockchainEvent)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(BlockchainEvent)
            .order_by(BlockchainEvent.block_number.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_events_by_contract(
        self,
        contract_address: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[BlockchainEvent], int]:
        addr = contract_address.strip().lower()
        offset = (page - 1) * page_size
        condition = func.lower(BlockchainEvent.contract_address) == addr

        count_stmt = (
            select(func.count()).select_from(BlockchainEvent).where(condition)
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(BlockchainEvent)
            .where(condition)
            .order_by(BlockchainEvent.block_number.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_indexed_events(self, limit: int = 50) -> list[BlockchainEvent]:
        """Backwards-compatible helper; prefer get_indexed_events_page."""
        stmt = (
            select(BlockchainEvent)
            .order_by(BlockchainEvent.block_number.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_large_transactions_page(
        self,
        min_value_eth: float,
        page: int,
        page_size: int,
    ) -> tuple[list[LargeTransaction], int]:
        offset = (page - 1) * page_size
        condition = LargeTransaction.value_eth >= min_value_eth
        count_stmt = (
            select(func.count()).select_from(LargeTransaction).where(condition)
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(LargeTransaction)
            .where(condition)
            .order_by(LargeTransaction.block_number.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total
