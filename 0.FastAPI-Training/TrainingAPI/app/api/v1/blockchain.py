from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3.exceptions import Web3RPCError

from ...core.database import get_db
from ...core.security import get_current_active_user, require_role
from ...dependencies.pagination import PaginationParams
from ...models.user import User
from ...schemas.blockchain import BlockchainEventOut, LargeTransactionOut
from ...schemas.common import PaginatedResponse
from ...services.blockchain_service import BlockchainService

router = APIRouter()


@router.get("/events", response_model=PaginatedResponse[BlockchainEventOut])
async def get_events(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BlockchainService(db)
    events, total = await service.get_indexed_events_page(
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return PaginatedResponse(
        data=[BlockchainEventOut.model_validate(e) for e in events],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/events/contract/{contract_address}",
    response_model=PaginatedResponse[BlockchainEventOut],
)
async def get_events_by_contract(
    contract_address: str,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BlockchainService(db)
    events, total = await service.get_events_by_contract(
        contract_address=contract_address,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return PaginatedResponse(
        data=[BlockchainEventOut.model_validate(e) for e in events],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/index", status_code=status.HTTP_202_ACCEPTED)
async def trigger_index(
    contract_address: str,
    from_block: int = 0,
    to_block: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Index logs for a contract. Use a **narrow** block range: public RPCs reject huge `eth_getLogs` queries."""
    service = BlockchainService(db)
    try:
        raw_events = await service.fetch_events(contract_address, from_block, to_block)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Web3RPCError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"Blockchain RPC error (try a smaller block range or different RPC): {exc}",
        ) from exc
    checksum = Web3.to_checksum_address(contract_address)
    for event in raw_events:
        event["contract_address"] = checksum
        event["event_name"] = "Unknown"
    stored = await service.store_events(chain="evm", events=raw_events)
    return {"indexed": stored, "total_fetched": len(raw_events)}


@router.get(
    "/large-transactions",
    response_model=PaginatedResponse[LargeTransactionOut],
)
async def list_large_transactions(
    min_value: float = Query(
        10.0,
        ge=0,
        description=(
            "Minimum value in ETH. Rows appear only after the Celery task "
            "`monitor_large_transactions` has run (Beat or POST /blockchain/monitor as admin)."
        ),
    ),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BlockchainService(db)
    rows, total = await service.list_large_transactions_page(
        min_value_eth=min_value,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return PaginatedResponse(
        data=[LargeTransactionOut.model_validate(r) for r in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/monitor", status_code=status.HTTP_202_ACCEPTED)
async def trigger_monitor(
    min_value_eth: float = Query(10.0, ge=0),
    _admin: User = Depends(require_role("admin")),
):
    # Import here so API startup does not load Celery sync DB engine (needs psycopg2 for Postgres).
    from app.tasks.blockchain_tasks import monitor_large_transactions

    monitor_large_transactions.delay(min_value_eth=min_value_eth)
    return {
        "message": "Large-transaction monitor queued",
        "min_value_eth": min_value_eth,
    }
