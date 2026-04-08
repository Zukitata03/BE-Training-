from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models.user import User
from ...services.blockchain_service import BlockchainService

router = APIRouter()


@router.get("/events")
async def get_events(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BlockchainService(db)
    events = await service.get_indexed_events(limit=limit)
    return [
        {
            "id": e.id,
            "chain": e.chain,
            "contract_address": e.contract_address,
            "event_name": e.event_name,
            "block_number": e.block_number,
            "tx_hash": e.tx_hash,
            "data": e.data,
        }
        for e in events
    ]


@router.post("/index", status_code=status.HTTP_202_ACCEPTED)
async def trigger_index(
    contract_address: str,
    from_block: int = 0,
    to_block: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BlockchainService(db)
    raw_events = await service.fetch_events(contract_address, from_block, to_block)
    for event in raw_events:
        event["contract_address"] = contract_address
        event["event_name"] = "Unknown"
    stored = await service.store_events(chain="evm", events=raw_events)
    return {"indexed": stored, "total_fetched": len(raw_events)}
