from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3

from ..core.config import get_config
from ..models.blockchain_event import BlockchainEvent


class BlockchainService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.w3 = Web3(Web3.HTTPProvider(get_config().blockchain_rpc_url))

    async def fetch_events(
        self,
        contract_address: str,
        from_block: int = 0,
        to_block: int | None = None,
    ) -> list[dict]:
        if to_block is None:
            to_block = self.w3.eth.block_number

        logs = self.w3.eth.get_logs({
            "address": Web3.to_checksum_address(contract_address),
            "fromBlock": from_block,
            "toBlock": to_block,
        })
        return [
            {
                "block_number": log["blockNumber"],
                "tx_hash": log["transactionHash"].hex(),
                "data": log.get("data", ""),
            }
            for log in logs
        ]

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
                contract_address=event["contract_address"],
                event_name=event.get("event_name", "Unknown"),
                block_number=event["block_number"],
                tx_hash=event["tx_hash"],
                data=event.get("data"),
            )
            self.db.add(db_event)
            stored += 1
        await self.db.flush()
        return stored

    async def get_indexed_events(self, limit: int = 50) -> list[BlockchainEvent]:
        stmt = (
            select(BlockchainEvent)
            .order_by(BlockchainEvent.block_number.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
